"""
System Constraints Module
Defines business rules and validation constraints for the food delivery system
"""

from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta


class BusinessConstraints:
    """Business logic constraints for the food delivery system"""
    
    # Order constraints
    MIN_ORDER_AMOUNT = 10.00
    MAX_ORDER_AMOUNT = 10000.00
    MAX_ITEMS_PER_ORDER = 50
    
    # Delivery constraints
    MAX_DELIVERY_TIME_HOURS = 4
    MIN_DELIVERY_TIME_MINUTES = 30
    
    # User constraints
    MIN_PASSWORD_LENGTH = 8
    MAX_PENDING_ORDERS_PER_USER = 5
    
    # System constraints
    MAX_ORDERS_PER_HOUR = 100
    MAX_CONCURRENT_USERS = 500


def validate_order_amount(amount):
    """Validate order amount against business constraints"""
    if amount < BusinessConstraints.MIN_ORDER_AMOUNT:
        raise ValidationError(
            f"Order amount must be at least ${BusinessConstraints.MIN_ORDER_AMOUNT}"
        )
    if amount > BusinessConstraints.MAX_ORDER_AMOUNT:
        raise ValidationError(
            f"Order amount cannot exceed ${BusinessConstraints.MAX_ORDER_AMOUNT}"
        )


def validate_delivery_time(estimated_time):
    """Validate estimated delivery time"""
    now = timezone.now()
    min_time = now + timedelta(minutes=BusinessConstraints.MIN_DELIVERY_TIME_MINUTES)
    max_time = now + timedelta(hours=BusinessConstraints.MAX_DELIVERY_TIME_HOURS)
    
    if estimated_time < min_time:
        raise ValidationError(
            f"Delivery time must be at least {BusinessConstraints.MIN_DELIVERY_TIME_MINUTES} minutes from now"
        )
    if estimated_time > max_time:
        raise ValidationError(
            f"Delivery time cannot exceed {BusinessConstraints.MAX_DELIVERY_TIME_HOURS} hours from now"
        )


def validate_user_pending_orders(user):
    """Check if user has too many pending orders"""
    from orders.models import Order
    pending_count = Order.objects.filter(
        customer=user,
        status__in=['pending', 'confirmed', 'preparing', 'ready_for_pickup', 'delivering']
    ).count()
    
    if pending_count >= BusinessConstraints.MAX_PENDING_ORDERS_PER_USER:
        raise ValidationError(
            f"You have reached the maximum of {BusinessConstraints.MAX_PENDING_ORDERS_PER_USER} pending orders"
        )


def validate_role_access(user, required_roles):
    """Validate if user has required role"""
    if user.role not in required_roles:
        raise ValidationError(
            f"Access denied. Required roles: {', '.join(required_roles)}"
        )
