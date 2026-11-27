from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from orders.models import MenuItem
from .models import Restaurant, RestaurantBranch

User = get_user_model()


class CatalogImageTests(TestCase):
    def setUp(self):
        self.initial_restaurants = Restaurant.objects.count()
        self.initial_dishes = MenuItem.objects.count()

    def seed(self, **options):
        call_command('seed_restaurant_catalog', allow_production=True, verbosity=0, **options)

    def test_seed_restores_team_images_and_preserves_custom_photos_on_repeat(self):
        self.seed()
        self.assertEqual(Restaurant.objects.filter(catalog_key__startswith='almaty-').exclude(image_url='').count(), 9)
        self.assertEqual(MenuItem.objects.filter(catalog_key__startswith='almaty-').exclude(image_url='').count(), 17)
        restaurant = Restaurant.objects.get(catalog_key='almaty-bahandi-burger')
        dish = MenuItem.objects.get(catalog_key='almaty-bahandi-burger-dish-1')
        restaurant.image_url = 'https://example.com/my-restaurant.jpg'
        restaurant.save()
        dish.image_url = 'https://example.com/my-dish.jpg'
        dish.save()
        self.seed()
        restaurant.refresh_from_db()
        dish.refresh_from_db()
        self.assertEqual(restaurant.image_url, 'https://example.com/my-restaurant.jpg')
        self.assertEqual(dish.image_url, 'https://example.com/my-dish.jpg')
        self.assertEqual(Restaurant.objects.count(), self.initial_restaurants + 9)
        self.assertEqual(MenuItem.objects.count(), self.initial_dishes + 21)

    def test_images_only_preserves_other_catalog_fields_and_does_not_create_records(self):
        restaurant = Restaurant.objects.create(
            catalog_key='almaty-bahandi-burger', name='My edited restaurant',
            description='My description', address='My address', is_active=False,
        )
        dish = MenuItem.objects.create(
            catalog_key='almaty-bahandi-burger-dish-1', restaurant=restaurant,
            name='My edited dish', category='Main', price='1234.56', is_active=False,
        )
        self.seed(images_only=True)
        restaurant.refresh_from_db()
        dish.refresh_from_db()
        self.assertTrue(restaurant.image_url.startswith('https://'))
        self.assertEqual(dish.image_url, 'https://bahandi.kz/netcat_files/20/31/menu_cheese_burger_chicken_550x550.jpg')
        self.assertEqual(restaurant.name, 'My edited restaurant')
        self.assertEqual(restaurant.description, 'My description')
        self.assertEqual(restaurant.address, 'My address')
        self.assertFalse(restaurant.is_active)
        self.assertEqual(dish.name, 'My edited dish')
        self.assertEqual(str(dish.price), '1234.56')
        self.assertFalse(dish.is_active)
        self.assertEqual(Restaurant.objects.count(), self.initial_restaurants + 1)
        self.assertEqual(MenuItem.objects.count(), self.initial_dishes + 1)
        self.seed(images_only=True)
        self.assertEqual(Restaurant.objects.count(), self.initial_restaurants + 1)
        self.assertEqual(MenuItem.objects.count(), self.initial_dishes + 1)


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
            owner=self.manager,
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

    def test_customer_catalog_includes_verified_branch_data_read_only(self):
        branch = RestaurantBranch.objects.create(
            restaurant=self.restaurant,
            address='Main Street 1, unit 2',
            source_url='https://2gis.kz/almaty/firm/123456789',
            delivery_available=None,
        )
        self.client.force_authenticate(self.customer)

        response = self.client.get('/api/restaurants/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = next(item for item in response.data['results'] if item['id'] == self.restaurant.id)
        self.assertEqual(item['branches'][0]['id'], branch.id)
        self.assertEqual(item['branches'][0]['source_url'], branch.source_url)
        self.assertIsNone(item['branches'][0]['delivery_available'])

        self.client.force_authenticate(self.manager)
        ignored = self.client.patch(
            f'/api/restaurants/{self.restaurant.id}/',
            {'branches': [{'address': 'Unverified address'}]},
            format='json',
        )
        self.assertEqual(ignored.status_code, status.HTTP_200_OK)
        branch.refresh_from_db()
        self.assertEqual(branch.address, 'Main Street 1, unit 2')

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

    def test_restaurant_schedule_allows_unknown_hours_but_not_partial_hours(self):
        self.client.force_authenticate(self.manager)
        unknown = self.client.post('/api/restaurants/', {
            'name': 'Unknown Hours Kitchen',
            'address': 'Main Street 5',
            'working_days': [],
        }, format='json')
        self.assertEqual(unknown.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(unknown.data['opening_time'])
        self.assertIsNone(unknown.data['closing_time'])

        partial = self.client.post('/api/restaurants/', {
            'name': 'Partial Hours Kitchen',
            'address': 'Main Street 6',
            'opening_time': '09:00',
            'working_days': [],
        }, format='json')
        self.assertEqual(partial.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('closing_time', partial.data)

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
