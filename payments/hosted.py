"""Persist intent before networking. Unknown results always reconcile, never charge again."""
import hashlib
import json
import time
from collections.abc import Mapping
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4
from xml.etree import ElementTree as ET

from django.conf import settings
from django.db import transaction, OperationalError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, authentication_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from loyalty.services import apply_refund, lock_wallet, synchronize
from . import freedompay
from .models import Payment, PaymentAttempt, PaymentEvent, PaymentRefund
from .serializers import PaymentSerializer


def _amount(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0 or result.as_tuple().exponent < -2:
            raise InvalidOperation
        return result
    except (InvalidOperation, ValueError):
        raise ValidationError('Invalid monetary amount.')


def apply_status(attempt_id, facts, source):
    for retry in range(5):
        try:
            customer_id = PaymentAttempt.objects.values_list('payment__order__customer_id', flat=True).get(pk=attempt_id)
            return _apply_status(attempt_id, facts, source, customer_id)
        except OperationalError as exc:
            if 'locked' not in str(exc).lower() or retry == 4:
                raise
            time.sleep(.05 * 2 ** retry)


@transaction.atomic
def _apply_status(attempt_id, facts, source, customer_id):
    lock_wallet(customer_id)
    attempt = PaymentAttempt.objects.select_for_update().select_related('payment__order').get(pk=attempt_id)
    payment = Payment.objects.select_for_update().get(pk=attempt.payment_id)
    if facts.get('pg_status') != 'ok':
        raise freedompay.ProviderUnavailable('Provider has not confirmed the payment status.')
    if str(facts.get('pg_payment_id', '')) != attempt.provider_id and attempt.provider_id:
        raise ValidationError('Provider payment reference mismatch.')
    if facts.get('pg_order_id') and facts['pg_order_id'] != attempt.reference:
        raise ValidationError('Order reference mismatch.')
    if _amount(facts.get('pg_amount')) != payment.amount or facts.get('pg_currency') != 'KZT':
        raise ValidationError('Payment amount or currency mismatch.')
    if str(facts.get('pg_testing_mode', '')) != ('1' if payment.is_test else '0'):
        raise ValidationError('Payment mode mismatch.')
    allowed = ['pg_payment_id', 'pg_order_id', 'pg_amount', 'pg_currency', 'pg_payment_status', 'pg_captured', 'pg_refund_amount', 'pg_revoked_amount', 'pg_testing_mode']
    safe = {key: str(facts[key]) for key in allowed if key in facts}
    key = hashlib.sha256(json.dumps([attempt.pk, safe], sort_keys=True).encode()).hexdigest()
    _, created = PaymentEvent.objects.get_or_create(event_key=key, defaults={'attempt': attempt, 'source': source, 'facts': safe})
    if not created:
        return payment
    if not attempt.provider_id:
        attempt.provider_id = str(facts['pg_payment_id'])
    state = facts.get('pg_payment_status')
    if state == 'success' and str(facts.get('pg_captured')) == '1':
        refunded = abs(Decimal(str(facts.get('pg_refund_amount', '0'))))
        if not refunded.is_finite() or refunded > payment.amount:
            raise ValidationError('Invalid provider refund amount.')
        if not payment.paid_at:
            payment.paid_at = timezone.now()
            payment.transaction_id = attempt.provider_id
        attempt.status = 'paid'
        if refunded >= payment.refunded_amount:
            payment.refunded_amount = refunded
        payment.status = ('refunded' if payment.refunded_amount == payment.amount and payment.amount > 0 else 'partially_refunded') if payment.refunded_amount else 'paid'
        if payment.order.status == 'pending':
            payment.order.status = 'confirmed'
            payment.order.save(update_fields=['status', 'updated_at'])
    elif state == 'error' and not payment.paid_at:
        # The provider has confirmed a final non-payment, so releasing is safe.
        # A local deadline alone never releases an unknown/in-progress payment.
        attempt.status = payment.status = 'expired' if timezone.now() >= attempt.created_at + timedelta(seconds=3600) else 'failed'
    elif state == 'success' and str(facts.get('pg_captured')) == '0' and abs(Decimal(str(facts.get('pg_revoked_amount', '0')))) == payment.amount and not payment.paid_at:
        attempt.status = payment.status = 'cancelled'
    elif state in ['new', 'waiting', 'process'] and not payment.paid_at and attempt.status not in ['failed', 'cancelled', 'expired']:
        attempt.status = payment.status = 'pending'
    attempt.save()
    payment.save()
    synchronize(payment.order)
    if payment.refunded_amount:
        apply_refund(payment.order, payment.refunded_amount, full=payment.status == 'refunded')
        for refund in PaymentRefund.objects.filter(payment=payment, status='unknown'):
            if payment.refunded_amount >= refund.previous_total + refund.amount:
                refund.status = 'confirmed'
                refund.save(update_fields=['status'])
    return payment


def reconcile(attempt):
    facts = freedompay.fetch(attempt)
    return apply_status(attempt.pk, facts, 'status')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def configuration(request):
    return Response({'provider': 'freedompay', 'configured': freedompay.configured(), 'test_mode': settings.FREEDOMPAY_TEST_MODE})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def checkout(request, order_id):
    payment = get_object_or_404(Payment.objects.select_related('order'), order_id=order_id, order__customer=request.user)
    if payment.method != 'online':
        raise ValidationError('This is a cash payment.')
    if request.method == 'GET':
        return Response({'payment': PaymentSerializer(payment).data, 'test_mode': payment.is_test})
    if payment.paid_at or payment.status in ['cancelled', 'expired', 'refunded']:
        return Response({'payment': PaymentSerializer(payment).data, 'redirect_url': '', 'test_mode': payment.is_test})
    if not freedompay.configured():
        raise freedompay.ProviderUnavailable('Online payment is not configured. Use FAQ or contact support.')
    with transaction.atomic():
        lock_wallet(request.user.pk)
        payment.refresh_from_db()
        if payment.paid_at:
            return Response({'payment': PaymentSerializer(payment).data, 'redirect_url': '', 'test_mode': payment.is_test})
        attempt = payment.attempts.filter(status__in=['unknown', 'pending', 'paid']).first()
        new = attempt is None
        if new:
            if payment.status == 'failed':
                # A failed checkout released its reserve. Re-reserve the original amount before retry.
                from loyalty.models import LoyaltyOrder
                from loyalty.services import journal
                record = LoyaltyOrder.objects.filter(order=payment.order).first()
                if record and record.state == 'released':
                    wallet = lock_wallet(request.user.pk)
                    if record.reserved > wallet.available:
                        raise ValidationError({'cashback_amount': 'Insufficient bonus balance for retry.'})
                    if record.reserved:
                        journal(wallet, 'reserve', 'Payment retry reservation', payment.order, credit=-record.reserved, reserve=record.reserved)
                    record.state = 'reserved'
                    record.save(update_fields=['state'])
            attempt = PaymentAttempt.objects.create(payment=payment, reference='JF-' + uuid4().hex)
            payment.status = 'pending'
            payment.save(update_fields=['status'])
    if new:
        result = freedompay.start(attempt)
        with transaction.atomic():
            locked = PaymentAttempt.objects.select_for_update().get(pk=attempt.pk)
            locked.provider_id = str(result['pg_payment_id'])
            locked.redirect_url = result['pg_redirect_url']
            if locked.status == 'unknown':
                locked.status = 'pending'
            locked.save()
            attempt = locked
    else:
        payment = reconcile(attempt)
        attempt.refresh_from_db()
    payment.refresh_from_db()
    return Response({'payment': PaymentSerializer(payment).data,
        'redirect_url': attempt.redirect_url if not payment.paid_at and attempt.status == 'pending' else '',
        'test_mode': payment.is_test})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify(request, order_id):
    payment = get_object_or_404(Payment, order_id=order_id, order__customer=request.user)
    attempt = payment.attempts.order_by('-id').first()
    if attempt:
        payment = reconcile(attempt)
    return Response({'payment': PaymentSerializer(payment).data, 'test_mode': payment.is_test})


@api_view(['POST'])
@authentication_classes([])
@throttle_classes([])
@permission_classes([AllowAny])
def result_notify(request):
    if not isinstance(request.data, Mapping) or len(request.data) > 100:
        raise ValidationError('Invalid callback payload.')
    if hasattr(request.data, 'lists') and any(len(values) != 1 for _, values in request.data.lists()):
        raise ValidationError('Duplicate callback fields.')
    facts = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)
    if any(isinstance(value, (dict, list)) for value in facts.values()):
        raise ValidationError('Callback fields must be scalar values.')
    if not freedompay.valid_signature('result.php', facts):
        return Response({'detail': 'Invalid signature.'}, status=403)
    attempt = get_object_or_404(PaymentAttempt, reference=facts.get('pg_order_id'))
    # Re-query the provider: result notifications do not always include currency/capture/refund fields.
    reconcile(attempt)
    values = {'pg_status': 'ok', 'pg_description': 'Accepted', 'pg_salt': uuid4().hex}
    values['pg_sig'] = freedompay.signature('result.php', values)
    root = ET.Element('response')
    for key, value in values.items():
        ET.SubElement(root, key).text = value
    return HttpResponse(ET.tostring(root, encoding='utf-8', xml_declaration=True), content_type='application/xml')


def hosted_refund(request, payment):
    if not request.headers.get('Idempotency-Key', '').strip():
        raise ValidationError('Idempotency-Key is required for refunds.')
    key = request.headers['Idempotency-Key'].strip()
    if len(key) > 100:
        raise ValidationError('Idempotency-Key is too long.')
    attempt = payment.attempts.filter(status='paid').first()
    if not attempt:
        raise ValidationError('No verified provider payment exists.')
    # Always reconcile before planning another refund, including after lost responses.
    payment = reconcile(attempt)
    with transaction.atomic():
        lock_wallet(payment.order.customer_id)
        payment.refresh_from_db()
        previous = payment.refunds.filter(key=key).first()
        if previous:
            return Response({'status': previous.status, 'payment': PaymentSerializer(payment).data})
        if payment.refunds.filter(status='unknown').exists():
            raise freedompay.ProviderUnavailable('Previous refund result is unknown; reconcile before another refund.')
        amount = _amount(request.data.get('amount', payment.amount-payment.refunded_amount))
        if not amount or amount > payment.amount-payment.refunded_amount:
            raise ValidationError('Refund exceeds remaining payment.')
        refund = PaymentRefund.objects.create(payment=payment, key=key, amount=amount, previous_total=payment.refunded_amount, reason=request.data['reason'])
    result = freedompay.call('revoke', {'pg_payment_id': attempt.provider_id, 'pg_refund_amount': str(amount)})
    refund.provider_id = result.get('pg_revoke_payment_id', '')
    if result.get('pg_status') != 'ok':
        refund.status = 'failed'
    refund.save()
    payment = reconcile(attempt)
    refund.refresh_from_db()
    return Response({'status': refund.status, 'payment': PaymentSerializer(payment).data})
