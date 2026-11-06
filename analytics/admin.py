from django.contrib import admin
from .models import AnalyticsEvent, SystemMetric, PerformanceReport


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'user', 'timestamp', 'ip_address']
    list_filter = ['event_type', 'timestamp']
    search_fields = ['user__username', 'event_type']
    ordering = ['-timestamp']


@admin.register(SystemMetric)
class SystemMetricAdmin(admin.ModelAdmin):
    list_display = ['name', 'value', 'unit', 'recorded_at']
    ordering = ['-recorded_at']


@admin.register(PerformanceReport)
class PerformanceReportAdmin(admin.ModelAdmin):
    list_display = ['period', 'start_date', 'end_date', 'total_orders', 'total_revenue']
    list_filter = ['period', 'start_date']
    ordering = ['-start_date']
