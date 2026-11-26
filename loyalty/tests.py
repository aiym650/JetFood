from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import time
from django.db import close_old_connections, OperationalError, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient
from orders.models import MenuItem, Order
from restaurants.models import Restaurant
from users.models import User
from .models import Wallet, LoyaltyOrder, LedgerEntry, LoyaltyPolicy
from .services import allocate, apply_refund, journal, lock_wallet, synchronize


class CashbackTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='safe-password')
        self.other = User.objects.create_user(username='another', password='safe-password')
        self.restaurant = Restaurant.objects.create(name='Kitchen', address='Test', opening_time='09:00', closing_time='22:00')
        self.dish = MenuItem.objects.create(name='Meal', category='Main', restaurant=self.restaurant, price='4000.00')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.wallet = Wallet.objects.create(user=self.user, available=500000)
        LedgerEntry.objects.create(wallet=self.wallet, kind='adjustment', category='opening', available_delta=500000, reason='Synthetic test funding', event_key='fund:'+str(self.user.pk))

    def checkout(self, key='checkout-1', **extra):
        return self.client.post('/api/orders/', {'items': [{'item_id': self.dish.pk, 'quantity': 1}], 'delivery_address': 'Test address', 'payment_method': 'cash', **extra}, format='json', HTTP_IDEMPOTENCY_KEY=key)

    def completed(self, key='checkout-1', **extra):
        response = self.checkout(key, **extra)
        self.assertEqual(response.status_code, 201, response.data)
        order = Order.objects.get(pk=response.data['id'])
        order.status = 'delivered'
        order.save()
        order.payment.mark_paid()
        return order

    def test_server_recalculates_amount_and_reserves_once(self):
        first = self.checkout(cashback_amount='1000.00', total_amount='1.00', discount_amount='9999.00')
        again = self.checkout(cashback_amount='1000.00', total_amount='1.00', discount_amount='9999.00')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(first.data['total_amount'], '3000.00')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available, 400000)
        self.assertEqual(self.wallet.reserved, 100000)
        self.assertEqual(LedgerEntry.objects.filter(kind='reserve').count(), 1)

    def test_delivery_does_not_increase_bonus_spending_limit(self):
        with override_settings(ORDER_DELIVERY_FEE='900.00'):
            response = self.client.post('/api/orders/quote/', {'items': [{'item_id': self.dish.pk, 'quantity': 1}], 'cashback_amount': '1200.00'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['cashback_max'], '1200.00')
        self.assertEqual(response.data['total_amount'], '3700.00')
        self.assertEqual(response.data['cashback_forecast'], '140.00')

    def test_spending_limit_and_balance_enforced(self):
        self.assertEqual(self.checkout(cashback_amount='1200.01').status_code, 400)
        with transaction.atomic():
            wallet = lock_wallet(self.user.pk)
            journal(wallet, 'adjustment', 'Test balance reduction', credit=-499900)
        self.assertEqual(self.checkout(cashback_amount='2').status_code, 400)

    def test_only_payment_and_delivery_together_award_once(self):
        response = self.checkout(cashback_amount='1000')
        order = Order.objects.get(pk=response.data['id'])
        order.payment.mark_paid()
        self.assertFalse(LedgerEntry.objects.filter(kind='earn').exists())
        order.status = 'delivered'
        order.save()
        synchronize(order)
        self.assertEqual(LedgerEntry.objects.filter(kind='earn').count(), 1)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available, 415000)
        self.assertEqual(self.wallet.reserved, 0)

    def test_delivery_before_payment_converges(self):
        order = self.completed()
        synchronize(order)
        self.assertEqual(order.loyalty.percentage_reward, 20000)

    def test_mixed_rates_and_exact_allocation(self):
        self.assertEqual(allocate(2, [100]*3), [1, 1, 0])
        promo = MenuItem.objects.create(name='Special', category='Main', restaurant=self.restaurant, price='4000', cashback_promotional=True)
        response = self.client.post('/api/orders/quote/', {'items': [{'item_id': self.dish.pk, 'quantity': 1}, {'item_id': promo.pk, 'quantity': 1}], 'cashback_amount': '2000'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['cashback_forecast'], '360.00')

    def test_partial_refund_returns_bonuses_and_reverses_earnings_idempotently(self):
        order = self.completed(cashback_amount='1000')
        apply_refund(order, Decimal('1500'))
        apply_refund(order, Decimal('1500'))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available, 457500)
        self.assertEqual(LedgerEntry.objects.filter(kind='refund').count(), 1)
        self.assertEqual(LoyaltyOrder.objects.get(order=order).percentage_reward, 7500)

    def test_refund_of_spent_awards_creates_debt_then_future_earnings_repay(self):
        order = self.completed()
        self.wallet.refresh_from_db()
        with transaction.atomic():
            wallet = lock_wallet(self.user.pk)
            journal(wallet, 'adjustment', 'Test spending of existing balance', credit=-wallet.available)
        apply_refund(order, Decimal('4000'), full=True)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available, 0)
        self.assertEqual(self.wallet.debt, 20000)
        self.completed('next-order')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.debt, 0)
        self.assertEqual(self.wallet.available, 0)

    def test_old_fifth_bonus_is_not_issued_for_new_jetpoints_orders(self):
        orders = [self.completed(f'order-{n}') for n in range(6)]
        self.assertFalse(LoyaltyOrder.objects.exclude(milestone_reward=0).exists())
        self.assertEqual(LedgerEntry.objects.filter(category='second_order').count(), 1)
        apply_refund(orders[0], Decimal('4000'), full=True)
        self.assertFalse(LoyaltyOrder.objects.exclude(milestone_reward=0).exists())

    def test_order_below_threshold_after_bonuses_not_counted(self):
        order = self.completed(cashback_amount='1200')
        self.assertEqual(order.loyalty.milestone_reward, 0)

    def test_failed_payment_releases_reservation_once(self):
        response = self.checkout(cashback_amount='1000')
        order = Order.objects.get(pk=response.data['id'])
        payment = order.payment
        payment.status = 'failed'
        payment.save()
        synchronize(order)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available, 500000)
        self.assertEqual(self.wallet.reserved, 0)

    def test_unknown_payment_keeps_reservation(self):
        response = self.checkout(cashback_amount='1000')
        synchronize(Order.objects.get(pk=response.data['id']))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.reserved, 100000)

    def test_wallet_and_order_are_user_scoped(self):
        response = self.checkout(cashback_amount='1000')
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/loyalty/').data['available'], '0.00')
        self.assertEqual(self.client.get(f"/api/orders/{response.data['id']}/").status_code, 404)

    def test_spending_limit_is_rounded_down_to_never_exceed_thirty_percent(self):
        self.dish.price = Decimal('10.02')
        self.dish.save()
        response = self.client.post('/api/orders/quote/', {'items': [{'item_id': self.dish.pk, 'quantity': 1}]}, format='json')
        self.assertEqual(response.data['cashback_max'], '3.00')

    def test_full_bonus_payment_requires_no_external_charge_when_policy_allows(self):
        LoyaltyPolicy.objects.filter(pk=LoyaltyPolicy.current().pk).update(spend_percent=100)
        response = self.checkout(cashback_amount='4000', payment_method='online')
        self.assertEqual(response.status_code, 201, response.data)
        order = Order.objects.get(pk=response.data['id'])
        self.assertEqual(order.payment.amount, 0)
        self.assertEqual(order.payment.provider, 'bonuses')
        self.assertEqual(order.payment.status, 'paid')
        self.assertEqual(order.loyalty.state, 'spent')
        admin = User.objects.create_user(username='bonus-refund-admin', role='admin')
        self.client.force_authenticate(admin)
        for _ in range(2):
            refunded = self.client.post(f'/api/payments/{order.payment.pk}/refund/', {'reason': 'Full bonus order refund'}, format='json')
            self.assertEqual(refunded.status_code, 200, refunded.data)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available, 500000)
        self.assertEqual(LedgerEntry.objects.filter(kind='refund').count(), 1)

    def test_pending_order_without_redemption_keeps_existing_item_editing(self):
        response = self.checkout()
        order = Order.objects.get(pk=response.data['id'])
        modified = self.client.patch(f'/api/orders/{order.pk}/modify/', {'items': [{'item_id': self.dish.pk, 'quantity': 2}]}, format='json')
        self.assertEqual(modified.status_code, 200, modified.data)
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal('8000'))
        self.assertEqual(order.payment.amount, Decimal('8000'))
        order.status = 'delivered'
        order.save()
        order.payment.mark_paid()
        self.assertEqual(LoyaltyOrder.objects.get(order=order).percentage_reward, 40000)

    def test_only_admin_can_choose_the_promotional_cashback_dishes(self):
        owner = User.objects.create_user(username='restaurant-owner', role='manager')
        self.restaurant.owner = owner
        self.restaurant.save()
        self.client.force_authenticate(owner)
        response = self.client.patch(f'/api/orders/menu/{self.dish.pk}/', {'cashback_promotional': True}, format='json')
        self.assertEqual(response.status_code, 403)
        admin = User.objects.create_user(username='programme-admin', role='admin')
        self.client.force_authenticate(admin)
        response = self.client.patch(f'/api/orders/menu/{self.dish.pk}/', {'cashback_promotional': True}, format='json')
        self.assertEqual(response.status_code, 200, response.data)


class ConcurrentSpendingTests(TransactionTestCase):
    def test_two_checkouts_cannot_reserve_the_same_balance(self):
        user = User.objects.create_user(username='race-buyer')
        restaurant = Restaurant.objects.create(name='Race Kitchen', address='Test', opening_time='09:00', closing_time='22:00')
        dish = MenuItem.objects.create(name='Meal', category='Main', restaurant=restaurant, price='4000')
        wallet = Wallet.objects.create(user=user, available=100000)
        LedgerEntry.objects.create(wallet=wallet, kind='adjustment', category='opening', available_delta=100000, reason='Synthetic race test funding', event_key='race-funding')
        def run(key):
            close_old_connections()
            try:
                api = APIClient()
                api.force_authenticate(user)
                return api.post('/api/orders/', {'delivery_address': 'Test', 'cashback_amount': '1000', 'items': [{'item_id': dish.pk, 'quantity': 1}]}, format='json', HTTP_IDEMPOTENCY_KEY=key).status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(run, ['race-1', 'race-2']))
        self.assertEqual(sorted(statuses), [201, 400])
        wallet = Wallet.objects.get(user=user)
        self.assertEqual(wallet.available, 0)
        self.assertEqual(wallet.reserved, 100000)
