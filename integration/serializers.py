from rest_framework import serializers
from .models import ExternalIntegration, IntegrationLog


class ExternalIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalIntegration
        fields = ['id', 'name', 'integration_type', 'status', 'api_endpoint',
                  'api_key', 'config', 'last_sync', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_sync']


class IntegrationLogSerializer(serializers.ModelSerializer):
    integration_name = serializers.CharField(source='integration.name', read_only=True)
    
    class Meta:
        model = IntegrationLog
        fields = ['id', 'integration', 'integration_name', 'level', 'message',
                  'request_data', 'response_data', 'status_code', 'timestamp']
        read_only_fields = ['id', 'timestamp']
