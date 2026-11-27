from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.cache import cache
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from restaurants.models import Restaurant, RestaurantBranch, MenuCategory
from .models import MenuItem, Order, PromoCode, PromoRedemption

User = get_user_model()


def setup_catalog():
    user = User.objects.create_user(username='promo-customer', password='testpass123')
    restaurant = Restaurant.objects.create(name='Promo Kitchen', address='Demo', opening_time='09:00', closing_time='22:00')
    dish = MenuItem.objects.create(restaurant=restaurant, name='Test meal', category='Mains', price='2500.00')
    return user, restaurant, dish


@override_settings(ORDER_DELIVERY_FEE='500.00')
class PromotionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user, self.restaurant, self.dish = setup_catalog()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.promo = PromoCode.objects.create(code=' save10 ', kind='percent', value=10)

    def payload(self, code='save10', quantity=2):
        return {'delivery_address': 'Test address', 'promo_code': code, 'items': [
            {'item_id': self.dish.pk, 'quantity': quantity, 'price_per_item': '0.01', 'item_name': 'Forged'}],
            'total_amount': '0.01', 'discount_amount': '99999'}

    def create_order(self, key='one', code='save10'):
        return self.client.post('/api/orders/', self.payload(code), format='json', HTTP_IDEMPOTENCY_KEY=key)

    def test_percent_quote_recalculates_without_consuming_and_caps(self):
        self.promo.maximum_discount = Decimal('350')
        self.promo.save()
        for quantity, expected in [(1, '250.00'), (2, '350.00')]:
            response = self.client.post('/api/orders/quote/', self.payload(' SAVE10 ', quantity), format='json')
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(str(response.data['discount_amount']), expected)
            self.assertEqual(str(response.data['delivery_fee']), '500.00')
        self.promo.refresh_from_db()
        self.assertEqual(self.promo.used_count, 0)
        self.assertFalse(PromoRedemption.objects.exists())

    def test_fixed_discount_never_reduces_delivery_or_goes_negative(self):
        self.promo.kind, self.promo.value = 'fixed', Decimal('8000')
        self.promo.save()
        result = self.create_order()
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(result.data['total_amount'], '500.00')
        self.assertEqual(result.data['discount_amount'], '5000.00')

    def test_free_delivery_only_affects_delivery(self):
        self.promo.kind = 'delivery'
        self.promo.save()
        result = self.create_order()
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(result.data['discount_amount'], '0.00')
        self.assertEqual(result.data['delivery_discount'], '500.00')
        self.assertEqual(result.data['total_amount'], '5000.00')

    def test_server_prices_and_historical_snapshots_and_payment(self):
        result = self.create_order(code=' SAVE10 ')
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(result.data['total_amount'], '5000.00')
        order = Order.objects.get(pk=result.data['id'])
        self.assertEqual(order.promo_code, 'SAVE10')
        self.assertEqual(order.payment.amount, Decimal('5000'))
        self.dish.name, self.dish.price = 'Changed', Decimal('7000')
        self.dish.save()
        item = order.items.get()
        self.assertEqual(item.item_name, 'Test meal')
        self.assertEqual(item.price_per_item, Decimal('2500'))

    def test_unavailable_dish_cannot_be_ordered(self):
        self.dish.is_active = False
        self.dish.save()
        self.assertEqual(self.create_order().status_code, 400)
        self.assertFalse(PromoRedemption.objects.exists())

    def test_date_activity_minimum_and_limits(self):
        for attrs, expected in [
            ({'ends_at': timezone.now() - timedelta(seconds=1)}, 'expired'),
            ({'starts_at': timezone.now() + timedelta(days=1)}, 'not_started'),
            ({'is_active': False}, 'inactive'),
            ({'minimum_amount': 6000}, 'minimum'),
            ({'usage_limit': 0}, 'limit'),
            ({'per_user_limit': 0}, 'user_limit'),
        ]:
            with self.subTest(expected=expected):
                PromoCode.objects.filter(pk=self.promo.pk).update(**attrs)
                response = self.create_order(key=expected)
                self.assertEqual(response.status_code, 400, response.data)
                self.assertEqual(str(response.data['promo_error']), expected)
                PromoCode.objects.filter(pk=self.promo.pk).update(starts_at=None, ends_at=None, is_active=True, minimum_amount=0, usage_limit=None, per_user_limit=None)

    def test_other_restaurant_and_mixed_order_rejected(self):
        other = Restaurant.objects.create(name='Another kitchen', address='Demo', opening_time='09:00', closing_time='22:00')
        self.promo.restaurant = other
        self.promo.save()
        response = self.create_order()
        self.assertEqual(str(response.data['promo_error']), 'restaurant')
        dish = MenuItem.objects.create(restaurant=other, name='Test meal', category='Mains', price='3500')
        response = self.client.post('/api/orders/quote/', {'items': [{'item_id': self.dish.pk, 'quantity': 1}, {'item_id': dish.pk, 'quantity': 1}]}, format='json')
        self.assertEqual(response.status_code, 400)
        for restaurant, expected in [(self.restaurant, '2500.00'), (other, '3500.00')]:
            data = self.client.get('/api/orders/menu/', {'restaurant': restaurant.pk}).data
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['price'], expected)

    def test_idempotency_reuses_order_even_after_promo_is_disabled(self):
        first = self.create_order()
        self.promo.is_active = False
        self.promo.save()
        second = self.create_order()
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(first.data['id'], second.data['id'])
        self.promo.refresh_from_db()
        self.assertEqual(self.promo.used_count, 1)
        self.assertEqual(PromoRedemption.objects.count(), 1)
        changed = self.client.post('/api/orders/', self.payload(quantity=1), format='json', HTTP_IDEMPOTENCY_KEY='one')
        self.assertEqual(changed.status_code, 409)

    def test_cancellation_does_not_release_code_and_own_order_is_private(self):
        self.promo.per_user_limit = 1
        self.promo.save()
        first = self.create_order()
        order_id = first.data['id']
        self.assertEqual(self.client.post(
            f'/api/orders/{order_id}/status/',
            {'status': 'cancelled', 'reason': 'I no longer need this order.'},
        ).status_code, 200)
        self.assertEqual(self.create_order(key='two').status_code, 400)
        other = User.objects.create_user(username='intruder')
        self.client.force_authenticate(other)
        for method, suffix, body in [('get', '/', {}), ('post', '/status/', {'status': 'cancelled'}), ('patch', '/modify/', {'delivery_address': 'x'}), ('get', '/route/', {})]:
            result = getattr(self.client, method)(f'/api/orders/{order_id}{suffix}', body, format='json')
            self.assertEqual(result.status_code, 404)

    def test_foreign_category_and_menu_owner_access(self):
        manager = User.objects.create_user(username='owner', role='manager')
        self.client.force_authenticate(manager)
        response = self.client.patch(f'/api/orders/menu/{self.dish.pk}/', {'price': '1.00'}, format='json')
        self.assertEqual(response.status_code, 403)
        self.restaurant.owner = manager
        self.restaurant.save()
        other = Restaurant.objects.create(name='Other', address='x', opening_time='09:00', closing_time='21:00')
        category = MenuCategory.objects.create(restaurant=other, name='Foreign')
        response = self.client.patch(f'/api/orders/menu/{self.dish.pk}/', {'menu_category': category.pk}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_verified_catalog_seed_is_idempotent(self):
        call_command('seed_restaurant_catalog', verbosity=0, allow_production=True)
        restaurants = Restaurant.objects.filter(catalog_key__startswith='almaty-')
        branches = RestaurantBranch.objects.filter(restaurant__catalog_key__startswith='almaty-')
        dishes = MenuItem.objects.filter(catalog_key__startswith='almaty-')
        self.assertEqual(restaurants.count(), 9)
        self.assertEqual(branches.count(), 27)
        self.assertEqual(dishes.count(), 21)
        self.assertEqual(
            set(restaurants.values_list('name', flat=True)),
            {
                'Doner na Abaya', 'Doner na Satpaeva', 'Popeyes', 'Bahandi Burger',
                'Okadzaki', 'Samurai', 'Kausar', 'Salam Bro', "Wendy's",
            },
        )
        self.assertFalse(dishes.filter(restaurant__name='Popeyes').exists())
        bahandi = restaurants.get(name='Bahandi Burger')
        bahandi_branch = RestaurantBranch.objects.get(
            restaurant=bahandi,
            catalog_key='almaty-bahandi-burger-abay-27',
        )
        self.assertTrue(bahandi_branch.delivery_available)
        self.assertEqual(str(bahandi_branch.opening_time), '11:00:00')
        self.assertEqual(str(bahandi_branch.closing_time), '23:45:00')
        self.assertEqual(
            bahandi.menu_source_url,
            'https://takeaway-web.choco.kz/filials/6219',
        )

        call_command('seed_restaurant_catalog', verbosity=0, allow_production=True)
        self.assertEqual(restaurants.count(), 9)
        self.assertEqual(branches.count(), 27)
        self.assertEqual(dishes.count(), 21)


class ConcurrentPromotionTests(TransactionTestCase):
    def setUp(self):
        self.user, self.restaurant, self.dish = setup_catalog()
        self.other = User.objects.create_user(username='second-promo-customer')
        self.promo = PromoCode.objects.create(code='LAST', kind='fixed', value=100, usage_limit=1)

    def race(self, same_user=False, same_key=False):
        barrier = Barrier(2)
        def send(index):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(self.user if same_user or index == 0 else self.other)
                barrier.wait(timeout=5)
                response = client.post('/api/orders/', {'delivery_address': 'Demo', 'promo_code': 'LAST', 'items': [{'item_id': self.dish.pk, 'quantity': 1}]}, format='json', HTTP_IDEMPOTENCY_KEY='same' if same_key else f'race-{index}')
                return response.status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return sorted(pool.map(send, range(2)))

    def test_parallel_global_limit(self):
        self.assertEqual(self.race(), [201, 400])
        self.promo.refresh_from_db()
        self.assertEqual(self.promo.used_count, 1)
        self.assertEqual(PromoRedemption.objects.count(), 1)

    def test_parallel_idempotent_request(self):
        self.assertEqual(self.race(same_user=True, same_key=True), [200, 201])
        self.assertEqual(PromoRedemption.objects.count(), 1)

    def test_parallel_per_user_limit(self):
        self.promo.usage_limit, self.promo.per_user_limit = None, 1
        self.promo.save()
        self.assertEqual(self.race(same_user=True), [201, 400])
        self.assertEqual(PromoRedemption.objects.count(), 1)
