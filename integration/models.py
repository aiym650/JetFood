from django.db import models
from django.conf import settings

class ExternalIntegration(models.Model):
    INTEGRATION_TYPES = [
        ('payment_gateway', 'Payment Gateway'),
        ('mapping_service', 'Mapping Service'),
        ('notification_service', 'Notification Service'),
        ('analytics_service', 'Analytics Service'),
        ('inventory_system', 'Inventory System'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('error', 'Error'),
    ]
    
    name = models.CharField(max_length=100)
    integration_type = models.CharField(max_length=50, choices=INTEGRATION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    api_endpoint = models.URLField()
    api_key = models.CharField(max_length=255, blank=True)
    config = models.JSONField(default=dict, blank=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.integration_type})"

class IntegrationLog(models.Model):
    LOG_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('debug', 'Debug'),
    ]
    
    integration = models.ForeignKey(ExternalIntegration, on_delete=models.CASCADE, related_name='logs')
    level = models.CharField(max_length=20, choices=LOG_LEVELS)
    message = models.TextField()
    request_data = models.JSONField(default=dict, blank=True)
    response_data = models.JSONField(default=dict, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['integration']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.integration.name} - {self.level}: {self.message[:50]}"
