from django.db import models
from django.db.models import Q
from django.utils import timezone


class Payment(models.Model):
    METHOD_CHOICES = [
        ('online', 'Hosted online payment'),
        ('cash', 'Cash on delivery'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('paid', 'Paid'),
        ('refund_requested', 'Refund requested'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('partially_refunded', 'Partially refunded'),
    ]

    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='payment',
    )
    provider = models.CharField(max_length=24, default='legacy', editable=False)
    is_test = models.BooleanField(default=True, editable=False)
    refunded_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=32, blank=True)
    card_brand = models.CharField(max_length=20, null=True, blank=True)
    card_last4 = models.CharField(max_length=4, null=True, blank=True)
    failure_reason = models.TextField(null=True, blank=True)
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
                condition=Q(status__in=['pending', 'failed', 'paid', 'refund_requested', 'refunded', 'cancelled', 'expired', 'partially_refunded']),
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
        from loyalty.services import synchronize
        synchronize(self.order)

    def __str__(self):
        return f'Payment {self.pk} for {self.order.order_number}: {self.status}'


class PaymentAttempt(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='attempts')
    reference = models.CharField(max_length=50, unique=True)
    provider_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=24, default='unknown')
    redirect_url = models.URLField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['payment'], condition=Q(status__in=['unknown', 'pending', 'paid']), name='one_active_payment_attempt')]


class PaymentEvent(models.Model):
    attempt = models.ForeignKey(PaymentAttempt, on_delete=models.PROTECT, related_name='events')
    event_key = models.CharField(max_length=100, unique=True)
    source = models.CharField(max_length=20)
    facts = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class PaymentRefund(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='refunds')
    key = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    previous_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default='unknown')
    reason = models.CharField(max_length=1000)
    provider_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['payment', 'key'], name='payment_refund_key')]
