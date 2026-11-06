from uuid import uuid4

from django.utils import timezone

from .models import Payment


def create_order_payment(order, method):
    fields = {
        'order': order,
        'method': method,
        'amount': order.total_amount,
        'status': 'pending',
        'transaction_id': '',
        'paid_at': None,
    }
    if method == 'online':
        fields.update({
            'status': 'paid',
            'transaction_id': f'SIM-{uuid4().hex[:12].upper()}',
            'paid_at': timezone.now(),
        })
    return Payment.objects.create(**fields)
