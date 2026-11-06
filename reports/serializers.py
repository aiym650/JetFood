from rest_framework import serializers
from .models import Report, ReportSchedule


class ReportSerializer(serializers.ModelSerializer):
    generated_by_name = serializers.CharField(source='generated_by.username', read_only=True)
    
    class Meta:
        model = Report
        fields = ['id', 'report_type', 'title', 'description', 'status',
                  'format', 'file_path', 'generated_by', 'generated_by_name',
                  'parameters', 'created_at', 'completed_at']
        read_only_fields = ['id', 'created_at', 'completed_at', 'file_path']


class ReportScheduleSerializer(serializers.ModelSerializer):
    recipient_names = serializers.SerializerMethodField()
    
    class Meta:
        model = ReportSchedule
        fields = ['id', 'report_type', 'frequency', 'parameters', 'recipients',
                  'recipient_names', 'is_active', 'last_run', 'next_run', 'created_at']
        read_only_fields = ['id', 'last_run', 'next_run', 'created_at']
    
    def get_recipient_names(self, obj):
        return [user.username for user in obj.recipients.all()]
