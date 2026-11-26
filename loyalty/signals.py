from django.db.models.signals import post_save
from django.dispatch import receiver
from orders.models import Order
from payments.models import Payment


@receiver(post_save, sender=Order)
@receiver(post_save, sender=Payment)
def financial_state_changed(sender, instance, raw=False, **kwargs):
    if raw:
        return
    from .models import LoyaltyOrder
    from .services import synchronize
    order = instance if sender is Order else instance.order
    if LoyaltyOrder.objects.filter(order_id=order.pk).exists() and Payment.objects.filter(order_id=order.pk).exists():
        synchronize(order)
