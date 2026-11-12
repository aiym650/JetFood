from django.db import models
from django.db.models import Q
from django.utils import timezone


class Payment(models.Model):
    METHOD_CHOICES = [
        ('online', 'Online simulation'),
        ('cash', 'Cash on delivery'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refund_requested', 'Refund requested'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='payment',
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=32, blank=True)
    refund_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # CHECK: amount cannot be negative
            models.CheckConstraint(condition=Q(amount__gte=0), name='payment_amount_not_negative'),
            # CHECK: method and status only from the allowed lists
            models.CheckConstraint(condition=Q(method__in=['online', 'cash']), name='payment_method_valid'),
            models.CheckConstraint(
                condition=Q(status__in=['pending', 'paid', 'refund_requested', 'refunded', 'cancelled']),
                name='payment_status_valid',
            ),
            # CHECK: a paid payment must have the payment time
            models.CheckConstraint(
                condition=~Q(status='paid') | Q(paid_at__isnull=False),
                name='payment_paid_has_paid_at',
            ),
            # UNIQUE: a transaction id is never repeated (empty id is allowed many times)
            models.UniqueConstraint(
                fields=['transaction_id'], condition=~Q(transaction_id=''),
                name='payment_transaction_id_unique_if_set',
            ),
        ]

    def mark_paid(self):
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.save(update_fields=['status', 'paid_at', 'updated_at'])

    def __str__(self):
        return f'Payment {self.pk} for {self.order.order_number}: {self.status}'
