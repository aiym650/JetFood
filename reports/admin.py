from django.contrib import admin
from .models import Report, ReportSchedule


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'report_type', 'status', 'format', 'generated_by', 'created_at']
    list_filter = ['report_type', 'status', 'format', 'created_at']
    search_fields = ['title', 'generated_by__username']
    ordering = ['-created_at']


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ['report_type', 'frequency', 'is_active', 'next_run', 'created_at']
    list_filter = ['report_type', 'frequency', 'is_active']
    filter_horizontal = ['recipients']
    ordering = ['report_type']
