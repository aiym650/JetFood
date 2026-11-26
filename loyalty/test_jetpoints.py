from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from . import tests as fixtures
from .amounts import to_minor
from .models import LedgerEntry, LoyaltyOrder, LoyaltyPolicy, SecondOrderReward, Wallet
from .services import apply_refund, level_summary, synchronize
from orders.models import Order
from users.models import User


class JetPointsTests(TestCase):
    setUp = fixtures.CashbackTests.setUp
    checkout = fixtures.CashbackTests.checkout
    completed = fixtures.CashbackTests.completed

    def test_first_paid_delivered_order_awards_five_percent_and_unlocks_offer(self):
        order = self.completed()
        record = LoyaltyOrder.objects.get(order=order)
        self.assertEqual(record.percentage_reward, 20000)
        data = self.client.get('/api/loyalty/').data
        self.assertEqual(data['total_earned_minor'], 20000)
        self.assertEqual(data['available'], '5200.00')
        self.assertEqual(data['level']['code'], 'bronze')
        self.assertEqual(data['level']['completed_orders'], 1)
        self.assertEqual(data['second_order']['status'], 'eligible')
        self.assertEqual(data['second_order']['reward_minor'], 100000)
        self.assertGreater(data['second_order']['seconds_remaining'], 0)

    def test_second_success_within_seven_days_earns_exactly_one_thousand(self):
        first = self.completed('first')
        first_at = timezone.now()-timedelta(days=6)
        LoyaltyOrder.objects.filter(order=first).update(completed_at=first_at)
        SecondOrderReward.objects.filter(user=self.user).update(deadline=first_at+timedelta(days=7))
        second = self.completed('second')
        reward = SecondOrderReward.objects.get(user=self.user)
        self.assertEqual(reward.awarded, 100000)
        self.assertEqual(reward.status, 'awarded')
        self.assertEqual(reward.second_order_id, second.pk)
        self.assertEqual(LedgerEntry.objects.filter(category='second_order').count(), 1)

    def test_second_success_after_seven_days_gets_no_retention_reward(self):
        first = self.completed('first')
        first_at = timezone.now()-timedelta(days=8)
        LoyaltyOrder.objects.filter(order=first).update(completed_at=first_at)
        SecondOrderReward.objects.filter(user=self.user).update(deadline=first_at+timedelta(days=7))
        self.completed('second')
        self.assertEqual(SecondOrderReward.objects.get(user=self.user).status, 'expired')
        self.assertFalse(LedgerEntry.objects.filter(category='second_order').exists())

    def test_second_order_exactly_at_the_deadline_is_inclusive(self):
        from unittest.mock import patch
        self.completed('first')
        deadline = SecondOrderReward.objects.get(user=self.user).deadline
        with patch('django.utils.timezone.now', return_value=deadline):
            self.completed('second-at-deadline')
        self.assertEqual(SecondOrderReward.objects.get(user=self.user).awarded, 100000)

    def test_migrated_first_success_still_shows_second_order_eligibility(self):
        first = self.completed('historical-first')
        SecondOrderReward.objects.filter(user=self.user).delete()  # Simulate pre-program history with no eligibility row.
        LoyaltyOrder.objects.filter(order=first).update(program_version=0, completed_at=timezone.now()-timedelta(days=2))
        data = self.client.get('/api/loyalty/').data
        self.assertEqual(data['second_order']['status'], 'eligible')
        self.assertEqual(data['second_order']['first_order_id'], first.pk)

    def test_second_order_offer_keeps_its_promised_amount_and_deadline(self):
        self.completed('first')
        before = SecondOrderReward.objects.get(user=self.user)
        LoyaltyPolicy.objects.filter(pk=1).update(second_order_bonus=200000, second_order_days=14)
        self.completed('second')
        after = SecondOrderReward.objects.get(user=self.user)
        self.assertEqual(after.awarded, before.amount)
        self.assertEqual(after.deadline, before.deadline)

    def test_failed_order_does_not_become_first_success(self):
        failed = self.checkout('failed')
        order = Order.objects.get(pk=failed.data['id'])
        order.status = 'cancelled'
        order.save()
        payment = order.payment
        payment.status = 'failed'
        payment.save()
        self.completed('first-success')
        data = self.client.get('/api/loyalty/').data
        self.assertEqual(data['level']['completed_orders'], 1)
        self.assertEqual(data['second_order']['status'], 'eligible')
        self.assertEqual(data['total_earned_minor'], 20000)

    def test_replayed_success_events_never_duplicate_cashback_or_second_bonus(self):
        first = self.completed('first')
        second = self.completed('second')
        for _ in range(3):
            synchronize(first)
            synchronize(second)
        self.assertEqual(LedgerEntry.objects.filter(category='cashback', kind='earn').count(), 2)
        self.assertEqual(LedgerEntry.objects.filter(category='second_order').count(), 1)
        self.assertEqual(self.client.get('/api/loyalty/').data['total_earned_minor'], 140000)

    def test_second_order_refund_reverses_both_rewards_once(self):
        self.completed('first')
        second = self.completed('second')
        apply_refund(second, Decimal('4000'), full=True)
        apply_refund(second, Decimal('4000'), full=True)
        self.assertEqual(SecondOrderReward.objects.get(user=self.user).status, 'reversed')
        self.assertEqual(LedgerEntry.objects.filter(category='second_order_reversal').count(), 1)
        self.assertEqual(self.client.get('/api/loyalty/').data['total_earned_minor'], 20000)
        self.assertEqual(level_summary(self.user.pk)['completed_orders'], 1)

    def test_partial_refund_adjusts_cashback_and_disqualifies_retention_order(self):
        self.completed('first')
        second = self.completed('second')
        apply_refund(second, Decimal('2000'))
        self.assertEqual(LoyaltyOrder.objects.get(order=second).percentage_reward, 10000)
        self.assertEqual(SecondOrderReward.objects.get(user=self.user).awarded, 0)
        self.assertEqual(level_summary(self.user.pk)['completed_orders'], 1)

    def test_cancellation_reverses_reward_and_it_cannot_be_claimed_again(self):
        first = self.completed('first')
        self.completed('second')
        first.status = 'cancelled'
        first.save()
        self.completed('third')
        self.assertEqual(SecondOrderReward.objects.get(user=self.user).awarded, 0)
        self.assertEqual(LedgerEntry.objects.filter(category='second_order').count(), 1)

    def test_tenth_order_qualifies_for_silver_rate(self):
        orders = [self.completed(f'order-{n}') for n in range(10)]
        self.assertEqual(level_summary(self.user.pk)['code'], 'silver')
        self.assertEqual(level_summary(self.user.pk)['orders_remaining'], 10)
        self.assertEqual(LoyaltyOrder.objects.get(order=orders[-1]).percentage_reward, 28000)

    def test_batched_completions_keep_ninth_bronze_and_tenth_silver(self):
        from payments.models import Payment
        for n in range(8):
            self.completed(f'before-threshold-{n}')
        ninth = self.checkout('ninth')
        tenth = self.checkout('tenth')
        ids = [ninth.data['id'], tenth.data['id']]
        Order.objects.filter(pk__in=ids).update(status='delivered')
        Payment.objects.filter(order_id__in=ids).update(status='paid', paid_at=timezone.now())
        synchronize(Order.objects.get(pk=ids[-1]))
        self.assertEqual(LoyaltyOrder.objects.get(order_id=ids[0]).cashback_bps, 500)
        self.assertEqual(LoyaltyOrder.objects.get(order_id=ids[1]).cashback_bps, 700)

    def test_twentieth_order_qualifies_for_gold_and_beats_promotional_rate(self):
        self.dish.cashback_promotional = True
        self.dish.save()
        orders = [self.completed(f'gold-{n}') for n in range(20)]
        data = level_summary(self.user.pk)
        self.assertEqual(data['code'], 'gold')
        self.assertEqual(data['cashback_percent'], '10.00')
        self.assertEqual(data['progress_percent'], 100)
        self.assertIsNone(data['next_level'])
        self.assertEqual(LoyaltyOrder.objects.get(order=orders[-1]).percentage_reward, 40000)

    def test_refund_recalculates_level_without_repricing_other_earned_orders(self):
        orders = [self.completed(f'silver-{n}') for n in range(10)]
        apply_refund(orders[0], Decimal('4000'), full=True)
        self.assertEqual(level_summary(self.user.pk)['code'], 'bronze')
        self.assertEqual(level_summary(self.user.pk)['completed_orders'], 9)
        self.assertEqual(LoyaltyOrder.objects.get(order=orders[-1]).cashback_bps, 700)

    def test_calendar_month_boundary_uses_kazakhstan_time(self):
        order = self.completed()
        start = timezone.now().astimezone(ZoneInfo('Asia/Qyzylorda')).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        LoyaltyOrder.objects.filter(order=order).update(completed_at=start-timedelta(microseconds=1))
        self.assertEqual(level_summary(self.user.pk)['completed_orders'], 0)
        LoyaltyOrder.objects.filter(order=order).update(completed_at=start)
        self.assertEqual(level_summary(self.user.pk)['completed_orders'], 1)

    def test_month_reset_removes_previous_month_orders_from_level(self):
        for n in range(10):
            self.completed(f'month-{n}')
        start = timezone.now().astimezone(ZoneInfo('Asia/Qyzylorda')).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        LoyaltyOrder.objects.filter(order__customer=self.user).update(completed_at=start-timedelta(days=1))
        data = level_summary(self.user.pk)
        self.assertEqual(data['code'], 'bronze')
        self.assertEqual(data['cashback_percent'], '5.00')
        self.assertEqual(data['completed_orders'], 0)

    def test_ledger_is_authority_even_if_cached_wallet_balance_is_tampered(self):
        Wallet.objects.filter(pk=self.wallet.pk).update(available=999999999)
        self.assertEqual(self.client.get('/api/loyalty/').data['balance_minor'], 500000)
        response = self.checkout(cashback_amount='1200.01')
        self.assertEqual(response.status_code, 400)

    def test_financial_order_history_cannot_be_deleted(self):
        order = self.completed('permanent-history')
        admin = User.objects.create_user(username='history-admin', role='admin')
        self.client.force_authenticate(admin)
        response = self.client.delete(f'/api/orders/{order.pk}/')
        self.assertEqual(response.status_code, 409)
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())
        self.assertTrue(LedgerEntry.objects.filter(order=order).exists())

    def test_customer_cannot_modify_balance_or_access_another_account(self):
        response = self.client.patch('/api/loyalty/', {'balance_minor': 9999999}, format='json')
        self.assertEqual(response.status_code, 405)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/loyalty/').data['balance_minor'], 0)
        self.assertEqual(self.client.get(f'/api/loyalty/{self.wallet.pk}/').status_code, 404)
        self.other.role = 'manager'
        self.other.save()
        self.assertEqual(self.client.get('/api/loyalty/').status_code, 403)

    def test_staff_cannot_redeem_or_generate_new_customer_rewards(self):
        self.user.role = 'manager'
        self.user.save()
        self.assertEqual(self.checkout(cashback_amount='100').status_code, 403)
        self.completed('staff-order')
        pending = self.checkout('staff-pre-program-order')
        order = Order.objects.get(pk=pending.data['id'])
        LoyaltyOrder.objects.filter(order=order).update(program_version=2)
        order.status = 'delivered'
        order.save()
        order.payment.mark_paid()
        self.assertFalse(LedgerEntry.objects.filter(kind='earn').exists())
        self.assertFalse(SecondOrderReward.objects.filter(user=self.user).exists())

    def test_reserve_spend_and_refund_are_reported_separately(self):
        response = self.checkout(cashback_amount='1000')
        order = Order.objects.get(pk=response.data['id'])
        data = self.client.get('/api/loyalty/').data
        self.assertEqual(data['reserved_minor'], 100000)
        self.assertEqual(data['total_redeemed_minor'], 0)
        order.status = 'delivered'
        order.save()
        order.payment.mark_paid()
        self.assertEqual(self.client.get('/api/loyalty/').data['total_redeemed_minor'], 100000)
        apply_refund(order, Decimal('3000'), full=True)
        data = self.client.get('/api/loyalty/').data
        self.assertEqual(data['total_redeemed_minor'], 0)
        self.assertEqual(data['balance_minor'], 500000)

    def test_money_boundary_rejects_floats_and_unsupported_precision(self):
        from rest_framework.exceptions import ValidationError
        for invalid in [1.2, '1.001', 'NaN', True]:
            with self.assertRaises(ValidationError):
                to_minor(invalid)
        self.assertEqual(to_minor(Decimal('123.45')), 12345)

    def test_history_pagination_is_stable_and_user_scoped(self):
        for n in range(60):
            LedgerEntry.objects.create(wallet=self.wallet, kind='adjustment', reason='Synthetic audit fixture', event_key=f'history-{n}')
        first = self.client.get('/api/loyalty/').data
        self.assertEqual(len(first['entries']), 50)
        self.assertTrue(first['has_more'])
        second = self.client.get('/api/loyalty/', {'before': first['next_before']}).data
        self.assertTrue(second['entries'])
        self.assertFalse({e['id'] for e in first['entries']} & {e['id'] for e in second['entries']})


class ConcurrentSecondRewardTests(TransactionTestCase):
    setUp = fixtures.CashbackTests.setUp
    checkout = fixtures.CashbackTests.checkout
    completed = fixtures.CashbackTests.completed

    def test_parallel_completion_events_issue_second_bonus_once(self):
        from payments.models import PaymentAttempt
        from payments.hosted import apply_status
        self.completed('first')
        response = self.checkout('second', payment_method='online')
        second = Order.objects.get(pk=response.data['id'])
        second.status = 'delivered'
        second.save()
        attempt = PaymentAttempt.objects.create(payment=second.payment, reference='second-reward-race', provider_id='1234', status='pending')
        facts = dict(pg_status='ok', pg_order_id=attempt.reference, pg_payment_id='1234', pg_amount='4000.00', pg_currency='KZT', pg_testing_mode='1', pg_payment_status='success', pg_captured='1')
        barrier = Barrier(2)
        def run(_):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                return apply_status(attempt.pk, facts, 'test').status
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(run, range(2))), ['paid', 'paid'])
        self.assertEqual(LedgerEntry.objects.filter(category='second_order').count(), 1)
        self.assertEqual(SecondOrderReward.objects.get(user=self.user).awarded, 100000)
