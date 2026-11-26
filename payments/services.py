from uuid import uuid4
from django.conf import settings

from .models import Payment


def create_order_payment(order, method):
    payment = Payment.objects.create(
        order=order,
        method=method,
        provider=('legacy' if settings.PAYMENTS_ALLOW_LEGACY_SIMULATION else 'freedompay') if method == 'online' else 'cash',
        is_test=settings.FREEDOMPAY_TEST_MODE if method == 'online' else False,
        amount=order.total_amount,
        status='pending',
        transaction_id='',
        paid_at=None,
    )
    if not order.total_amount:
        payment.provider = 'bonuses'
        payment.is_test = False
        payment.save(update_fields=['provider', 'is_test'])
        payment.mark_paid()
        order.status = 'confirmed'
        order.save(update_fields=['status'])
    return payment


def create_simulated_transaction_id():
    return f'SIM-{uuid4().hex[:12].upper()}'


def detect_card_brand(card_number):
    if card_number.startswith('4'):
        return 'visa'
    prefix_two = int(card_number[:2])
    prefix_four = int(card_number[:4])
    if 51 <= prefix_two <= 55 or 2221 <= prefix_four <= 2720:
        return 'mastercard'
    return 'other'
