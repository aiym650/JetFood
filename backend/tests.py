from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from orders.models import MenuItem, Order


class GlobalSearchTests(TestCase):
    def setUp(self):
        self.customer = get_user_model().objects.create_user(
            username='customer',
            email='customer@example.com',
            password='testpass123',
            role='customer',
        )
        self.other_customer = get_user_model().objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123',
            role='customer',
        )
        self.admin = get_user_model().objects.create_user(
            username='search-admin',
            email='admin@example.com',
            password='testpass123',
            role='admin',
        )
        self.menu_item = MenuItem.objects.get(
            name='Пицца Маргарита',
        )
        MenuItem.objects.create(
            name='Hidden pizza',
            description='Not available',
            category='Pizza',
            price='800.00',
            is_active=False,
            restaurant=self.menu_item.restaurant,
        )
        Order.objects.create(
            order_number='ORD-SEARCH-001',
            customer=self.customer,
            total_amount='900.00',
            delivery_address='Search street',
        )
        Order.objects.create(
            order_number='ORD-SEARCH-002',
            customer=self.other_customer,
            total_amount='900.00',
            delivery_address='Other street',
        )
        self.client = APIClient()

    def test_customer_search_returns_menu_and_only_own_orders(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.get('/api/search/', {'q': 'Search'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [order['order_number'] for order in response.data['orders']],
            ['ORD-SEARCH-001'],
        )
        self.assertEqual(response.data['menu_items'], [])
        self.assertEqual(response.data['users'], [])

    def test_admin_search_includes_user_results(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get('/api/search/', {'q': 'customer'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([user['username'] for user in response.data['users']], ['customer'])

    def test_english_dish_search_matches_russian_menu_records(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.get('/api/search/', {'q': 'pizza'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item['id'] for item in response.data['menu_items']],
            [self.menu_item.id],
        )

    def test_lowercase_russian_dish_search_matches_title_case_catalog(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.get('/api/search/', {'q': 'пицца'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item['id'] for item in response.data['menu_items']],
            [self.menu_item.id],
        )
