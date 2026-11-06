from rest_framework import serializers
from .models import AnalyticsEvent, SystemMetric, PerformanceReport


class AnalyticsEventSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = AnalyticsEvent
        fields = ['id', 'event_type', 'user', 'username', 'timestamp', 
                  'metadata', 'ip_address']
        read_only_fields = ['id', 'timestamp', 'ip_address']


class SystemMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemMetric
        fields = ['id', 'name', 'value', 'unit', 'description', 'recorded_at']
        read_only_fields = ['id', 'recorded_at']


class PerformanceReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceReport
        fields = ['id', 'period', 'start_date', 'end_date', 'total_orders',
                  'total_revenue', 'average_delivery_time', 'active_users', 'created_at']
        read_only_fields = ['id', 'created_at']
