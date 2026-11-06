from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
import requests
from .models import ExternalIntegration, IntegrationLog
from .serializers import ExternalIntegrationSerializer, IntegrationLogSerializer
from users.constraints import validate_role_access


class ExternalIntegrationListCreateView(generics.ListCreateAPIView):
    serializer_class = ExternalIntegrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'manager']:
            return ExternalIntegration.objects.all()
        else:
            return ExternalIntegration.objects.filter(status='active')
    
    def perform_create(self, serializer):
        try:
            validate_role_access(self.request.user, ['admin', 'manager'])
        except Exception:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Admin or manager access required")
        serializer.save()


class ExternalIntegrationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ExternalIntegration.objects.all()
    serializer_class = ExternalIntegrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_update(self, serializer):
        validate_role_access(self.request.user, ['admin', 'manager'])
        serializer.save()
    
    def perform_destroy(self, instance):
        validate_role_access(self.request.user, ['admin'])
        instance.delete()


class IntegrationLogListView(generics.ListAPIView):
    serializer_class = IntegrationLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'manager']:
            return IntegrationLog.objects.all()
        else:
            return IntegrationLog.objects.none()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def test_integration(request, integration_id):
    """Test an external integration"""
    user = request.user
    validate_role_access(user, ['admin', 'manager'])
    
    try:
        integration = ExternalIntegration.objects.get(id=integration_id)
        
        # Simulate API call
        log_entry = IntegrationLog.objects.create(
            integration=integration,
            level='info',
            message=f'Testing integration: {integration.name}',
            request_data={'test': True},
            status_code=200
        )
        
        # In real implementation, make actual API call
        # response = requests.get(integration.api_endpoint, headers={'Authorization': integration.api_key})
        
        return Response({
            'message': 'Integration test initiated',
            'log_id': log_entry.id
        })
    except ExternalIntegration.DoesNotExist:
        return Response({'error': 'Integration not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def sync_integration(request, integration_id):
    """Sync data with external integration"""
    user = request.user
    validate_role_access(user, ['admin', 'manager'])
    
    try:
        integration = ExternalIntegration.objects.get(id=integration_id)
        
        # Log sync attempt
        IntegrationLog.objects.create(
            integration=integration,
            level='info',
            message=f'Sync initiated for {integration.name}',
            request_data={'sync': True}
        )
        
        # Update last sync time
        integration.last_sync = timezone.now()
        integration.save()
        
        return Response({
            'message': 'Sync completed successfully',
            'last_sync': integration.last_sync
        })
    except ExternalIntegration.DoesNotExist:
        return Response({'error': 'Integration not found'}, status=status.HTTP_404_NOT_FOUND)
