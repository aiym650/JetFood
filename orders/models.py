from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.validators import MinValueValidator
from backend.image_references import validate_image_reference


class PromoCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    kind = models.CharField(max_length=20, choices=[('percent', 'Percent'), ('fixed', 'KZT'), ('delivery', 'Free delivery')])
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    maximum_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    per_user_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0, editable=False)
    restaurant = models.ForeignKey('restaurants.Restaurant', on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(value__gte=0, minimum_amount__gte=0), name='promo_amounts_nonnegative'),
            models.CheckConstraint(condition=~Q(kind='percent') | Q(value__lte=100), name='promo_percent_at_most_100'),
            models.CheckConstraint(condition=Q(maximum_discount__isnull=True) | Q(maximum_discount__gte=0), name='promo_cap_nonnegative'),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        self.code = self.code.strip().upper()
        if self.kind == 'percent' and not 0 <= self.value <= 100:
            raise ValidationError({'value': 'Use a percentage between 0 and 100.'})
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            raise ValidationError({'ends_at': 'End must be after start.'})

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.full_clean()
        if self.pk:
            # Redemptions update this counter atomically; ordinary admin saves cannot reset it.
            kwargs['update_fields'] = [f.name for f in self._meta.concrete_fields if f.name not in ['id', 'used_count']]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class PromoRedemption(models.Model):
    promo = models.ForeignKey(PromoCode, on_delete=models.PROTECT, related_name='redemptions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    order = models.OneToOneField('Order', on_delete=models.PROTECT, related_name='redemption')
    created_at = models.DateTimeField(auto_now_add=True)


class MenuItem(models.Model):
    menu_category = models.ForeignKey('restaurants.MenuCategory', on_delete=models.PROTECT, null=True, blank=True, related_name='items')
    demo_key = models.CharField(max_length=80, unique=True, null=True, blank=True, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.CharField(max_length=500, blank=True, validators=[validate_image_reference])
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    is_active = models.BooleanField(default=True)
    restaurant = models.ForeignKey(
        "restaurants.Restaurant",
        on_delete=models.CASCADE,
        related_name="menu_items",
    )

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gt=0),
                name="menuitem_price_positive",
            ),
            models.CheckConstraint(
                condition=Q(rating__gte=0) & Q(rating__lte=5),
                name="menuitem_rating_0_5",
            ),
            models.UniqueConstraint(
                fields=["restaurant", "name"],
                name="menuitem_unique_name_per_restaurant",
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.menu_category_id and not self.category.strip():
            raise ValidationError({'menu_category': 'Choose a menu category.'})
        if self.menu_category_id and self.menu_category.restaurant_id != self.restaurant_id:
            raise ValidationError({'menu_category': 'Category must belong to the same restaurant.'})

    def save(self, *args, **kwargs):
        if not self.menu_category_id and self.restaurant_id and self.category:
            from restaurants.models import MenuCategory
            self.menu_category, _ = MenuCategory.objects.get_or_create(restaurant_id=self.restaurant_id, name=self.category)
        self.clean()
        if self.menu_category_id:
            self.category = self.menu_category.name
        super().save(*args, **kwargs)


class Order(models.Model):
    promo_code = models.CharField(max_length=50, blank=True)
    items_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    idempotency_key = models.CharField(max_length=100, null=True, blank=True)
    request_fingerprint = models.CharField(max_length=64, blank=True)
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("preparing", "Preparing"),
        ("ready_for_pickup", "Ready for pickup"),
        ("delivering", "Delivering"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    order_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    delivery_person = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliveries",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="normal",
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_address = models.TextField()
    delivery_notes = models.TextField(blank=True)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    actual_delivery_time = models.DateTimeField(null=True, blank=True)
    delivery_confirmed_at = models.DateTimeField(null=True, blank=True)
    delivery_started_at = models.DateTimeField(null=True, blank=True)
    estimated_arrival_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["customer"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=['customer', 'idempotency_key'], name='order_customer_idempotency'),
            models.CheckConstraint(
                condition=Q(total_amount__gte=0),
                name="order_total_not_negative",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "pending",
                        "confirmed",
                        "preparing",
                        "ready_for_pickup",
                        "delivering",
                        "delivered",
                        "cancelled",
                    ]
                ),
                name="order_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(priority__in=["low", "normal", "high", "urgent"]),
                name="order_priority_valid",
            ),
        ]

    def __str__(self):
        return f"Order {self.order_number} - {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    item_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    price_per_item = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="orderitem_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(price_per_item__gte=0),
                name="orderitem_price_not_negative",
            ),
            models.CheckConstraint(
                condition=Q(subtotal__gte=0),
                name="orderitem_subtotal_not_negative",
            ),
        ]

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.price_per_item
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name} x {self.quantity}"


class DeliveryRoute(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="delivery_route",
    )
    origin_address = models.CharField(max_length=500)
    origin_latitude = models.FloatField(null=True, blank=True)
    origin_longitude = models.FloatField(null=True, blank=True)
    destination_latitude = models.FloatField(null=True, blank=True)
    destination_longitude = models.FloatField(null=True, blank=True)
    route_distance_meters = models.PositiveIntegerField(null=True, blank=True)
    estimated_duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_delivery_routes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Route for {self.order.order_number}"
