from django.db import models
from django.db.models import Q
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('analyst', 'Analyst'),
        ('delivery', 'Delivery Person'),
        ('customer', 'Customer'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Phone number must be valid')],
        blank=True
    )
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        constraints = [
            # UNIQUE: one account per e-mail (empty e-mail is allowed many times)
            models.UniqueConstraint(
                fields=['email'], condition=~Q(email=''), name='user_email_unique_if_set',
            ),
            # CHECK: role must be one of the five known roles
            models.CheckConstraint(
                condition=Q(role__in=['admin', 'manager', 'analyst', 'delivery', 'customer']),
                name='user_role_valid',
            ),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.role})"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('order_created', 'Order Created'),
        ('order_updated', 'Order Updated'),
        ('order_status', 'Order Status Changed'),
        ('order_delivered', 'Order Delivered'),
        ('role_changed', 'Role Changed'),
        ('system', 'System Notification'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    link = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"


class DeliveryAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='delivery_addresses')
    label = models.CharField(max_length=50, default='Home')
    recipient_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address_line = models.CharField(max_length=500)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)
    instructions = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', 'id']
        constraints = [
            # UNIQUE (partial): a user can have only ONE default address
            models.UniqueConstraint(
                fields=['user'], condition=Q(is_default=True),
                name='deliveryaddress_one_default_per_user',
            ),
        ]

    def __str__(self):
        return f'{self.label}: {self.address_line}, {self.city}'
