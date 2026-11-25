"""Migration helpers: preserve exact balances, history and legacy reward snapshots."""
from decimal import Decimal


AMOUNTS = {
    'wallet': ('available', 'reserved', 'debt'),
    'ledgerentry': ('available_delta', 'reserved_delta', 'debt_delta'),
    'loyaltyorder': ('reserved', 'delivery_cash', 'refunded_cash', 'returned_bonus', 'percentage_reward', 'milestone_reward', 'minimum', 'milestone'),
}


def minor(value):
    exact = Decimal(str(value)) * 100
    if exact != int(exact):
        raise ValueError('A legacy amount has unsupported precision; no rounding is permitted during migration.')
    return int(exact)


def convert_amounts(apps, schema_editor):
    alias = schema_editor.connection.alias
    for model_name, names in AMOUNTS.items():
        model = apps.get_model('loyalty', model_name)
        for row in model.objects.using(alias).all().iterator():
            updates = {name: minor(getattr(row, name)) for name in names}
            if model_name == 'loyaltyorder':
                updates['lines'] = [{'goods': minor(line['goods']), 'bonus': minor(line['bonus']),
                    'rate_bps': minor(line.get('rate', '0'))} for line in row.lines]
            model.objects.using(alias).filter(pk=row.pk).update(**updates)


def preserve_history(apps, schema_editor):
    alias = schema_editor.connection.alias
    Wallet = apps.get_model('loyalty', 'Wallet')
    Ledger = apps.get_model('loyalty', 'LedgerEntry')
    Snapshot = apps.get_model('loyalty', 'LoyaltyOrder')
    Policy = apps.get_model('loyalty', 'LoyaltyPolicy')
    Order = apps.get_model('orders', 'Order')
    Payment = apps.get_model('payments', 'Payment')
    from django.db.models import Sum
    policy, _ = Policy.objects.using(alias).get_or_create(pk=1)
    if policy.base_percent == 3:
        policy.base_percent = 5
        policy.save(using=alias, update_fields=['base_percent'])
    for wallet in Wallet.objects.using(alias).all().iterator():
        totals = Ledger.objects.using(alias).filter(wallet=wallet).aggregate(a=Sum('available_delta'), r=Sum('reserved_delta'), d=Sum('debt_delta'))
        deltas = {'available_delta': wallet.available-(totals['a'] or 0),
            'reserved_delta': wallet.reserved-(totals['r'] or 0), 'debt_delta': wallet.debt-(totals['d'] or 0)}
        if any(deltas.values()):
            Ledger.objects.using(alias).create(wallet=wallet, kind='adjustment', category='opening',
                reason='JetPoints migration: preserve pre-ledger balance', event_key=f'jetpoints-opening:{wallet.pk}', **deltas)
    payments = {p.order_id: p for p in Payment.objects.using(alias).all()}
    for order in Order.objects.using(alias).all().iterator():
        payment = payments.get(order.pk)
        completed = order.status == 'delivered' and payment and payment.paid_at
        completed_at = max(order.actual_delivery_time or order.updated_at, payment.paid_at) if completed else None
        record = Snapshot.objects.using(alias).filter(order_id=order.pk).first()
        if record:
            if completed_at:
                Snapshot.objects.using(alias).filter(pk=record.pk).update(completed_at=completed_at)
            continue
        total = minor(payment.amount if payment else order.total_amount)
        delivery = min(total, max(0, minor(order.delivery_fee)-minor(order.delivery_discount)))
        refunded = minor(payment.refunded_amount) if payment else 0
        Snapshot.objects.using(alias).create(order_id=order.pk, program_version=0 if completed else 2,
            completed_at=completed_at, state='spent' if payment and payment.paid_at else 'released' if order.status == 'cancelled' else 'reserved',
            delivery_cash=delivery, refunded_cash=refunded,
            lines=[{'goods': total-delivery, 'bonus': 0, 'rate_bps': 0, 'promotional_bps': 0}])
