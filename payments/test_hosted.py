from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from loyalty.tests import CashbackTests
from loyalty.models import LedgerEntry, Wallet
from .models import Payment, PaymentAttempt, PaymentEvent
from .freedompay import signature, ProviderUnavailable
from .hosted import apply_status


@override_settings(FREEDOMPAY_SECRET_KEY='unit-test-secret', FREEDOMPAY_MERCHANT_ID='12345', PAYMENTS_PUBLIC_URL='https://jetfood.example', FREEDOMPAY_TEST_MODE=True)
class HostedPaymentTests(TestCase):
    setUp = CashbackTests.setUp
    checkout = CashbackTests.checkout
    def pending(self):
        response = self.checkout(payment_method='online', cashback_amount='1000')
        self.assertEqual(response.status_code, 201, response.data)
        payment = Payment.objects.get(order_id=response.data['id'])
        attempt = PaymentAttempt.objects.create(payment=payment, reference='test-reference', provider_id='987', status='pending')
        return payment, attempt

    def facts(self, **extra):
        return dict(pg_status='ok', pg_order_id='test-reference', pg_payment_id='987', pg_amount='3000.00', pg_currency='KZT', pg_testing_mode='1', pg_payment_status='success', pg_captured='1', **extra)

    def test_official_signature_vector(self):
        params = dict(pg_amount='100', pg_currency='KZT', pg_description='Order #1001', pg_merchant_id='12345', pg_order_id='order_1001', pg_salt='a1b2c3d4')
        self.assertEqual(signature('init_payment.php', params, 'test_secret_key'), 'b9ad75871668ca040f80f5f6b530e6ed')

    def test_card_simulator_is_disabled_by_default(self):
        payment, _ = self.pending()
        self.assertEqual(self.client.post(f'/api/payments/{payment.order_id}/pay/', {}).status_code, 410)

    def test_duplicate_and_out_of_order_status_cannot_unpay(self):
        payment, attempt = self.pending()
        facts = self.facts()
        apply_status(attempt.pk, facts, 'test')
        apply_status(attempt.pk, facts, 'test')
        facts['pg_payment_status'] = 'waiting'
        apply_status(attempt.pk, facts, 'test')
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'paid')
        self.assertEqual(LedgerEntry.objects.filter(kind='spend').count(), 1)

    def test_webhook_rejects_invalid_signature(self):
        _, attempt = self.pending()
        response = APIClient().post('/api/payments/result.php', {'pg_order_id': attempt.reference, 'pg_sig': 'invalid'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(PaymentEvent.objects.count(), 0)

    @patch('payments.freedompay.fetch')
    def test_signed_webhook_reconciles_and_is_idempotent(self, fetch):
        payment, attempt = self.pending()
        fetch.return_value = self.facts()
        params = dict(pg_order_id=attempt.reference, pg_payment_id='987', pg_result='1', pg_salt='salt')
        params['pg_sig'] = signature('result.php', params)
        for _ in range(2):
            response = APIClient().post('/api/payments/result.php', params)
            self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'paid')
        self.assertEqual(PaymentEvent.objects.count(), 1)

    def test_amount_currency_mode_and_reference_are_verified(self):
        _, attempt = self.pending()
        for key, value in [('pg_amount', '1'), ('pg_currency', 'USD'), ('pg_testing_mode', '0'), ('pg_payment_id', 'another'), ('pg_order_id', 'other')]:
            facts = self.facts()
            facts[key] = value
            from rest_framework.exceptions import ValidationError
            with self.assertRaises(ValidationError):
                apply_status(attempt.pk, facts, 'test')
        self.assertEqual(PaymentEvent.objects.count(), 0)

    @patch('payments.freedompay.fetch', side_effect=ProviderUnavailable())
    @patch('payments.freedompay.start')
    def test_unknown_result_does_not_create_another_charge(self, start, fetch):
        payment, _ = self.pending()
        response = self.client.post(f'/api/payments/{payment.order_id}/checkout/', {})
        self.assertEqual(response.status_code, 503)
        start.assert_not_called()
        self.assertEqual(PaymentAttempt.objects.count(), 1)
        self.assertEqual(Wallet.objects.get(user=self.user).reserved, 100000)

    def test_foreign_payment_status_and_checkout_are_inaccessible(self):
        payment, _ = self.pending()
        self.client.force_authenticate(self.other)
        for path in ['checkout', 'verify']:
            self.assertEqual(self.client.post(f'/api/payments/{payment.order_id}/{path}/', {}).status_code, 404)

    def test_partial_and_full_refund_are_monotonic(self):
        payment, attempt = self.pending()
        facts = self.facts()
        apply_status(attempt.pk, facts, 'test')
        for refunded, expected in [('1500', 'partially_refunded'), ('0', 'partially_refunded'), ('3000', 'refunded')]:
            facts['pg_refund_amount'] = '-' + refunded
            apply_status(attempt.pk, facts, 'test')
            payment.refresh_from_db()
            self.assertEqual(payment.status, expected)
        self.assertEqual(Wallet.objects.get(user=self.user).available, 500000)

    def test_only_verified_final_failure_can_expire_and_release_bonuses(self):
        from django.utils import timezone
        from datetime import timedelta
        payment, attempt = self.pending()
        PaymentAttempt.objects.filter(pk=attempt.pk).update(created_at=timezone.now()-timedelta(hours=2))
        facts = self.facts()
        facts['pg_payment_status'] = 'waiting'
        apply_status(attempt.pk, facts, 'test')
        self.assertEqual(Wallet.objects.get(user=self.user).reserved, 100000)
        facts['pg_payment_status'] = 'error'
        apply_status(attempt.pk, facts, 'test')
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'expired')
        self.assertEqual(Wallet.objects.get(user=self.user).reserved, 0)

    @patch('payments.freedompay.urlopen')
    def test_unsigned_provider_response_never_confirms_payment(self, urlopen):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'<response><pg_status>ok</pg_status><pg_payment_status>success</pg_payment_status></response>'
        urlopen.return_value = response
        payment, _ = self.pending()
        verified = self.client.post(f'/api/payments/{payment.order_id}/verify/', {})
        self.assertEqual(verified.status_code, 503)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'pending')

    @patch('payments.freedompay.fetch')
    def test_test_payment_keeps_its_label_after_live_configuration_switch(self, fetch):
        payment, _ = self.pending()
        fetch.return_value = self.facts()
        with override_settings(FREEDOMPAY_TEST_MODE=False):
            verified = self.client.post(f'/api/payments/{payment.order_id}/verify/', {})
        self.assertEqual(verified.status_code, 200)
        self.assertTrue(verified.data['test_mode'])
        self.assertTrue(verified.data['payment']['is_test'])


from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import close_old_connections
from django.test import TransactionTestCase


@override_settings(FREEDOMPAY_TEST_MODE=True)
class ConcurrentWebhookTests(TransactionTestCase):
    setUp = CashbackTests.setUp
    checkout = CashbackTests.checkout

    def test_parallel_verified_events_consume_reserved_bonuses_once(self):
        response = self.checkout(payment_method='online', cashback_amount='1000')
        payment = Payment.objects.get(order_id=response.data['id'])
        attempt = PaymentAttempt.objects.create(payment=payment, reference='parallel-reference', provider_id='987', status='pending')
        facts = dict(pg_status='ok', pg_order_id=attempt.reference, pg_payment_id='987', pg_amount='3000.00', pg_currency='KZT', pg_testing_mode='1', pg_payment_status='success', pg_captured='1')
        barrier = Barrier(2)
        def run(_):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                return apply_status(attempt.pk, facts, 'parallel-test').status
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(run, range(2))), ['paid', 'paid'])
        self.assertEqual(LedgerEntry.objects.filter(kind='spend').count(), 1)
        self.assertEqual(PaymentEvent.objects.count(), 1)
