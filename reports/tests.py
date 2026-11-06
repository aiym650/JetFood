from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import Report
from orders.models import Order
from django.utils import timezone
from datetime import datetime

User = get_user_model()


class ReportTestCase(TestCase):
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

    def test_create_report(self):
        """Test creating a report"""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/reports/', {
            'report_type': 'sales',
            'title': 'Monthly Sales Report',
            'format': 'pdf',
            'parameters': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-31'
            }
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_sales_report_includes_the_entire_end_date(self):
        order = Order.objects.create(
            order_number='ORD-REPORT-001',
            customer=self.customer,
            status='delivered',
            priority='normal',
            total_amount='50.00',
            delivery_address='123 Test St',
        )
        Order.objects.filter(pk=order.pk).update(
            created_at=timezone.make_aware(datetime(2024, 1, 31, 12))
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/reports/', {
            'report_type': 'sales',
            'title': 'January Sales Report',
            'format': 'pdf',
            'parameters': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-31',
            },
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['parameters']['total_orders'], 1)

    def test_report_list(self):
        """Test listing reports"""
        Report.objects.all().delete()  # Clear any existing reports
        Report.objects.create(
            report_type='sales',
            title='Test Report',
            status='completed',
            format='pdf',
            generated_by=self.admin
        )
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/reports/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_report_download(self):
        """Test downloading a report"""
        report = Report.objects.create(
            report_type='sales',
            title='Test Report',
            status='completed',
            format='pdf',
            file_path='/reports/test.pdf',
            generated_by=self.admin
        )
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f'/api/reports/{report.id}/download/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_schedule(self):
        """Test creating a report schedule"""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/reports/schedules/', {
            'report_type': 'sales',
            'frequency': 'monthly',
            'recipients': [self.customer.id]
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
