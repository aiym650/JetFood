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

    def test_api_key_is_accepted_but_never_returned_by_serializer(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/integration/', {
            'name': 'Protected Payment Gateway',
            'integration_type': 'payment_gateway',
            'api_endpoint': 'https://api.payment.test',
            'api_key': 'test-secret-key',
            'status': 'active',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('api_key', response.data)
        self.assertTrue(response.data['api_key_present'])

        integration_id = response.data['id']
        detail = self.client.get(f'/api/integration/{integration_id}/')
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertNotIn('api_key', detail.data)
        self.assertTrue(ExternalIntegration.objects.get(pk=integration_id).api_key)

    def test_updating_other_fields_without_api_key_preserves_existing_secret(self):
        integration = ExternalIntegration.objects.create(
            name='Protected mapping',
            integration_type='mapping_service',
            api_endpoint='https://maps.example.test',
            api_key='keep-existing-secret',
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.put(
            f'/api/integration/{integration.id}/',
            {
                'name': 'Updated mapping',
                'integration_type': 'mapping_service',
                'api_endpoint': 'https://updated-maps.example.test',
                'status': 'active',
                'config': {},
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        integration.refresh_from_db()
        self.assertEqual(integration.api_key, 'keep-existing-secret')
        self.assertNotIn('api_key', response.data)

    def test_customer_cannot_read_inactive_integration_detail(self):
        integration = ExternalIntegration.objects.create(
            name='Inactive test',
            integration_type='mapping_service',
            api_endpoint='https://maps.example.test',
            status='inactive',
        )
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(f'/api/integration/{integration.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
