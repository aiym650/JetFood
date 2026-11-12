from django.db import models
from django.db.models import Q
from django.conf import settings


class MenuItem(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(max_length=500, blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    is_active = models.BooleanField(default=True)
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='menu_items',
    )

    class Meta:
        ordering = ['id']
        constraints = [
            # CHECK: price must be positive
            models.CheckConstraint(condition=Q(price__gt=0), name='menuitem_price_positive'),
            # CHECK: rating is from 0 to 5
            models.CheckConstraint(
                condition=Q(rating__gte=0) & Q(rating__lte=5), name='menuitem_rating_0_5',
            ),
            # UNIQUE: no two dishes with the same name in one restaurant
            models.UniqueConstraint(
                fields=['restaurant', 'name'], name='menuitem_unique_name_per_restaurant',
            ),
        ]

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('delivering', 'Delivering'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    delivery_person = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deliveries'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_address = models.TextField()
    delivery_notes = models.TextField(blank=True)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    actual_delivery_time = models.DateTimeField(null=True, blank=True)
    delivery_confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['customer']),
        ]
        constraints = [
            # CHECK: total cannot be negative
            models.CheckConstraint(condition=Q(total_amount__gte=0), name='order_total_not_negative'),
            # CHECK: status and priority only from the allowed lists
            models.CheckConstraint(
                condition=Q(status__in=['pending', 'confirmed', 'preparing', 'delivering', 'delivered', 'cancelled']),
                name='order_status_valid',
            ),
            models.CheckConstraint(
                condition=Q(priority__in=['low', 'normal', 'high', 'urgent']),
                name='order_priority_valid',
            ),
        ]
    
    def __str__(self):
        return f"Order {self.order_number} - {self.status}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
    )
    item_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    price_per_item = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            # CHECK: quantity must be at least 1, money fields cannot be negative
            models.CheckConstraint(condition=Q(quantity__gt=0), name='orderitem_quantity_positive'),
            models.CheckConstraint(condition=Q(price_per_item__gte=0), name='orderitem_price_not_negative'),
            models.CheckConstraint(condition=Q(subtotal__gte=0), name='orderitem_subtotal_not_negative'),
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
        related_name='delivery_route',
    )
    origin_address = models.CharField(max_length=500)
    notes = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_delivery_routes',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Route for {self.order.order_number}'
