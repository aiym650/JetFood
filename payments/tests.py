from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from orders.models import MenuItem, Order
from .models import Payment

User = get_user_model()


class PaymentApiTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='customer', password='pass12345', role='customer'
        )
        self.other_customer = User.objects.create_user(
            username='other-customer', password='pass12345', role='customer'
        )
        self.manager = User.objects.create_user(
            username='manager', password='pass12345', role='manager'
        )
        self.courier = User.objects.create_user(
            username='courier', password='pass12345', role='delivery'
        )
        self.menu_item = MenuItem.objects.create(
            name='Payment test meal',
            category='Test',
            price='25.00',
        )
        self.client = APIClient()

    def create_order(self, method='cash'):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post('/api/orders/', {
            'delivery_address': '1 Main Street',
            'payment_method': method,
            'items': [{'item_id': self.menu_item.id, 'quantity': 1}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return Order.objects.get(pk=response.data['id'])

    def test_online_payment_is_simulated_and_customer_history_is_private(self):
        order = self.create_order('online')
        payment = Payment.objects.get(order=order)
        self.assertEqual(payment.status, 'paid')
        self.assertTrue(payment.transaction_id.startswith('SIM-'))
        self.assertIsNotNone(payment.paid_at)

        response = self.client.get('/api/payments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['order_number'], order.order_number)

        self.client.force_authenticate(user=self.other_customer)
        response = self.client.get('/api/payments/')
        self.assertEqual(response.data['results'], [])

    def test_cash_payment_requires_delivery_confirmation(self):
        order = self.create_order('cash')
        payment = Payment.objects.get(order=order)
        self.assertEqual(payment.status, 'pending')
        order.delivery_person = self.courier
        order.save(update_fields=['delivery_person'])
        self.client.force_authenticate(user=self.courier)

        early = self.client.post(f'/api/payments/{payment.id}/confirm-cash/')
        self.assertEqual(early.status_code, status.HTTP_400_BAD_REQUEST)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'pending')

        order.status = 'delivered'
        order.save(update_fields=['status'])
        confirmed = self.client.post(f'/api/payments/{payment.id}/confirm-cash/')
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'paid')
        self.assertIsNotNone(payment.paid_at)

    def test_cancelled_online_order_requests_manager_refund(self):
        order = self.create_order('online')
        payment = Payment.objects.get(order=order)
        self.client.force_authenticate(user=self.customer)
        cancelled = self.client.post(f'/api/orders/{order.id}/status/', {
            'status': 'cancelled',
        }, format='json')
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'refund_requested')

        forbidden = self.client.post(
            f'/api/payments/{payment.id}/refund/',
            {'reason': 'Order cancelled'},
            format='json',
        )
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.manager)
        refunded = self.client.post(
            f'/api/payments/{payment.id}/refund/',
            {'reason': 'Order was cancelled before preparation.'},
            format='json',
        )
        self.assertEqual(refunded.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'refunded')
        self.assertIsNotNone(payment.refunded_at)

        repeated = self.client.post(
            f'/api/payments/{payment.id}/refund/',
            {'reason': 'Duplicate request'},
            format='json',
        )
        self.assertEqual(repeated.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelled_cash_order_does_not_remain_payable(self):
        order = self.create_order('cash')
        payment = Payment.objects.get(order=order)
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(f'/api/orders/{order.id}/status/', {
            'status': 'cancelled',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'cancelled')
