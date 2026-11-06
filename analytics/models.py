from django.db import models
from django.conf import settings

class AnalyticsEvent(models.Model):
    EVENT_TYPES = [
        ('order_created', 'Order Created'),
        ('order_completed', 'Order Completed'),
        ('order_cancelled', 'Order Cancelled'),
        ('user_login', 'User Login'),
        ('user_logout', 'User Logout'),
        ('page_view', 'Page View'),
        ('api_call', 'API Call'),
    ]
    
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.event_type} at {self.timestamp}"

class SystemMetric(models.Model):
    name = models.CharField(max_length=100, unique=True)
    value = models.DecimalField(max_digits=15, decimal_places=2)
    unit = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"{self.name}: {self.value} {self.unit}"

class PerformanceReport(models.Model):
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    total_orders = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    average_delivery_time = models.DurationField(null=True, blank=True)
    active_users = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.period} report: {self.start_date} to {self.end_date}"
