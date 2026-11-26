from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class LoyaltyPolicy(models.Model):
    """One editable programme, read afresh for each quote. No retroactive rate changes."""
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    base_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5, validators=[MinValueValidator(0), MaxValueValidator(100)])
    silver_orders = models.PositiveSmallIntegerField(default=10, validators=[MinValueValidator(1)])
    silver_percent = models.DecimalField(max_digits=5, decimal_places=2, default=7, validators=[MinValueValidator(0), MaxValueValidator(100)])
    gold_orders = models.PositiveSmallIntegerField(default=20, validators=[MinValueValidator(1)])
    gold_percent = models.DecimalField(max_digits=5, decimal_places=2, default=10, validators=[MinValueValidator(0), MaxValueValidator(100)])
    second_order_bonus = models.PositiveBigIntegerField(default=100000, help_text='Minor JetPoints; 100000 = 1000 JetPoints.')
    second_order_days = models.PositiveSmallIntegerField(default=7, validators=[MinValueValidator(1)])
    jetpoints_started_at = models.DateTimeField(default=timezone.now, editable=False)
    promotional_percent = models.DecimalField(max_digits=5, decimal_places=2, default=7, validators=[MinValueValidator(0), MaxValueValidator(100)])
    spend_percent = models.DecimalField(max_digits=5, decimal_places=2, default=30, validators=[MinValueValidator(0), MaxValueValidator(100)])
    milestone_every = models.PositiveSmallIntegerField(default=5, validators=[MinValueValidator(1)])
    milestone_minimum = models.DecimalField(max_digits=12, decimal_places=2, default=3000, validators=[MinValueValidator(0)])
    milestone_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=500, validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.gold_orders <= self.silver_orders:
            raise ValidationError('Gold must require more completed orders than Silver.')
        if not self.base_percent <= self.silver_percent <= self.gold_percent:
            raise ValidationError('Level rates must increase from Bronze to Gold.')

    @classmethod
    def current(cls):
        return cls.objects.get_or_create(pk=1)[0]


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='wallet')
    available = models.BigIntegerField(default=0, help_text='Cached ledger projection in minor JetPoints (100 = 1 JP).')
    reserved = models.BigIntegerField(default=0)
    debt = models.BigIntegerField(default=0)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(available__gte=0, reserved__gte=0, debt__gte=0), name='wallet_nonnegative')]


class LoyaltyOrder(models.Model):
    """Only new checkouts participate; historical orders are never silently rewarded."""
    order = models.OneToOneField('orders.Order', on_delete=models.PROTECT, related_name='loyalty')
    program_version = models.PositiveSmallIntegerField(default=2, editable=False)
    completed_at = models.DateTimeField(null=True, blank=True, editable=False, db_index=True)
    cashback_bps = models.PositiveSmallIntegerField(null=True, blank=True, editable=False)
    reserved = models.BigIntegerField(default=0)
    state = models.CharField(max_length=12, default='reserved', choices=[('reserved', 'Reserved'), ('spent', 'Spent'), ('released', 'Released')])
    # Immutable line allocations: discounted goods, bonus share, rate and cumulative cash refunds.
    lines = models.JSONField(default=list)
    delivery_cash = models.BigIntegerField(default=0)
    refunded_cash = models.BigIntegerField(default=0)
    returned_bonus = models.BigIntegerField(default=0)
    percentage_reward = models.BigIntegerField(default=0)
    milestone_reward = models.BigIntegerField(default=0)
    minimum = models.BigIntegerField(default=300000)
    every = models.PositiveSmallIntegerField(default=5)
    milestone = models.BigIntegerField(default=50000)


class LedgerEntry(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='entries')
    order = models.ForeignKey('orders.Order', null=True, blank=True, on_delete=models.PROTECT)
    category = models.CharField(max_length=24, default="legacy", editable=False)
    kind = models.CharField(max_length=20, choices=[(x, x) for x in ['earn', 'reserve', 'spend', 'release', 'refund', 'adjustment']])
    available_delta = models.BigIntegerField(default=0)
    reserved_delta = models.BigIntegerField(default=0)
    debt_delta = models.BigIntegerField(default=0)
    reason = models.CharField(max_length=250)
    event_key = models.CharField(max_length=150, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']


class SecondOrderReward(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='second_order_reward')
    first_order = models.ForeignKey('orders.Order', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    second_order = models.ForeignKey('orders.Order', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    deadline = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    amount = models.PositiveBigIntegerField(default=100000)
    awarded = models.PositiveBigIntegerField(default=0)
    status = models.CharField(max_length=20, default='waiting', choices=[(x, x) for x in ['waiting', 'eligible', 'awarded', 'expired', 'reversed', 'not_eligible']])
