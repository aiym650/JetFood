from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from orders.models import MenuItem
from .models import Restaurant

User = get_user_model()


class RestaurantApiTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='customer', password='pass12345', role='customer'
        )
        self.manager = User.objects.create_user(
            username='manager', password='pass12345', role='manager'
        )
        self.client = APIClient()
        self.restaurant = Restaurant.objects.create(
            name='North Kitchen',
            address='Main Street 1',
            opening_time='09:00',
            closing_time='21:00',
            working_days=[0, 1, 2, 3, 4, 5, 6],
        )

    def test_customers_can_browse_active_restaurants_only(self):
        Restaurant.objects.create(
            name='Closed Kitchen',
            address='Main Street 2',
            opening_time='09:00',
            closing_time='21:00',
            is_active=False,
        )
        self.client.force_authenticate(self.customer)

        response = self.client.get('/api/restaurants/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item['name'] for item in response.data['results']]
        self.assertIn('North Kitchen', names)
        self.assertNotIn('Closed Kitchen', names)

    def test_only_managers_can_create_or_edit_restaurants(self):
        self.client.force_authenticate(self.customer)
        forbidden = self.client.post('/api/restaurants/', {
            'name': 'Customer Kitchen',
            'address': 'Main Street 3',
            'opening_time': '09:00',
            'closing_time': '21:00',
            'working_days': [0, 1],
        }, format='json')
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.manager)
        response = self.client.post('/api/restaurants/', {
            'name': 'Manager Kitchen',
            'address': 'Main Street 3',
            'opening_time': '10:00',
            'closing_time': '22:00',
            'working_days': [0, 1, 2],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['working_days'], [0, 1, 2])

    def test_restaurant_schedule_rejects_invalid_hours_and_weekdays(self):
        self.client.force_authenticate(self.manager)
        response = self.client.post('/api/restaurants/', {
            'name': 'Invalid Kitchen',
            'address': 'Main Street 4',
            'opening_time': '21:00',
            'closing_time': '09:00',
            'working_days': [7],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_menu_management_and_customer_availability_filter(self):
        self.client.force_authenticate(self.manager)
        created = self.client.post('/api/orders/menu/', {
            'name': 'Soup',
            'description': 'Daily soup',
            'category': 'Lunch',
            'price': '8.50',
            'image_url': '',
            'restaurant': self.restaurant.id,
            'is_active': True,
        }, format='json')
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.customer)
        visible = self.client.get('/api/orders/menu/', {'restaurant': self.restaurant.id})
        self.assertEqual(visible.status_code, status.HTTP_200_OK)
        self.assertEqual([item['name'] for item in visible.data], ['Soup'])

        item = MenuItem.objects.get(name='Soup')
        item.is_active = False
        item.save()
        hidden = self.client.get('/api/orders/menu/', {'restaurant': self.restaurant.id})
        self.assertEqual(hidden.data, [])

    def test_customers_cannot_manage_menu_items(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post('/api/orders/menu/', {
            'name': 'Soup',
            'category': 'Lunch',
            'price': '8.50',
            'restaurant': self.restaurant.id,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_menu_item_requires_a_restaurant(self):
        self.client.force_authenticate(self.manager)
        response = self.client.post('/api/orders/menu/', {
            'name': 'Unassigned soup',
            'category': 'Lunch',
            'price': '8.50',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('restaurant', response.data)
