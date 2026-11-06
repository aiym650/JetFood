from django.contrib import admin
from .models import ExternalIntegration, IntegrationLog


@admin.register(ExternalIntegration)
class ExternalIntegrationAdmin(admin.ModelAdmin):
    list_display = ['name', 'integration_type', 'status', 'last_sync', 'created_at']
    list_filter = ['integration_type', 'status', 'created_at']
    search_fields = ['name']


@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    list_display = ['integration', 'level', 'message', 'timestamp', 'status_code']
    list_filter = ['level', 'timestamp', 'integration']
    search_fields = ['message', 'integration__name']
    ordering = ['-timestamp']
