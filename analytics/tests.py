from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import AnalyticsEvent, SystemMetric

User = get_user_model()


class AnalyticsTestCase(TestCase):
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

    def test_create_system_metric(self):
        """Test creating system metric"""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/analytics/metrics/', {
            'name': 'server_load',
            'value': 75.5,
            'unit': '%',
            'description': 'Current server load'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SystemMetric.objects.count(), 1)

    def test_system_analysis_admin_only(self):
        """Test that only admins/managers/analysts can access system analysis"""
        self.client.force_authenticate(user=self.customer)
        response = self.client.get('/api/analytics/analysis/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/analytics/analysis/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
