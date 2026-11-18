from uuid import uuid4

from .models import Payment


def create_order_payment(order, method):
    return Payment.objects.create(
        order=order,
        method=method,
        amount=order.total_amount,
        status='pending',
        transaction_id='',
        paid_at=None,
    )


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
