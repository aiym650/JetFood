from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import ExternalIntegration, IntegrationLog

User = get_user_model()


class IntegrationTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123',
            role='admin'
        )
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@example.com',
            password='pass123',
            role='customer'
        )
        self.client = APIClient()

    def test_create_integration_admin_only(self):
        """Test that only admins can create integrations"""
        self.client.force_authenticate(user=self.customer)
        response = self.client.post('/api/integration/', {
            'name': 'Payment Gateway',
            'integration_type': 'payment_gateway',
            'api_endpoint': 'https://api.payment.com',
            'status': 'active'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/integration/', {
            'name': 'Payment Gateway',
            'integration_type': 'payment_gateway',
            'api_endpoint': 'https://api.payment.com',
            'status': 'active'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_integration_sync(self):
        """Test integration sync endpoint"""
        integration = ExternalIntegration.objects.create(
            name='Test Integration',
            integration_type='analytics_service',
            api_endpoint='https://api.test.com',
            status='active'
        )
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/integration/{integration.id}/sync/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_integration_test(self):
        """Test integration test endpoint"""
        integration = ExternalIntegration.objects.create(
            name='Test Integration',
            integration_type='payment_gateway',
            api_endpoint='https://api.test.com',
            status='active'
        )
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/integration/{integration.id}/test/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
