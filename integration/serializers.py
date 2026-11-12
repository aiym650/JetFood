from rest_framework import serializers
from .models import ExternalIntegration, IntegrationLog


class ExternalIntegrationSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    api_key_present = serializers.SerializerMethodField()

    class Meta:
        model = ExternalIntegration
        fields = ['id', 'name', 'integration_type', 'status', 'api_endpoint',
                  'api_key', 'api_key_present', 'config', 'last_sync',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_sync']

    def get_api_key_present(self, integration):
        return bool(integration.api_key)


class IntegrationLogSerializer(serializers.ModelSerializer):
    integration_name = serializers.CharField(source='integration.name', read_only=True)
    
    class Meta:
        model = IntegrationLog
        fields = ['id', 'integration', 'integration_name', 'level', 'message',
                  'request_data', 'response_data', 'status_code', 'timestamp']
        read_only_fields = ['id', 'timestamp']
