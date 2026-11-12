from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import DeliveryRoute, MenuItem, Order, OrderItem

User = get_user_model()


class OrderTestCase(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@example.com',
            password='pass123',
            role='customer'
        )
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123',
            role='admin'
        )
        self.pizza = MenuItem.objects.get(name='Пицца Маргарита')
        self.client = APIClient()

    def test_menu_lists_active_items_for_authenticated_users(self):
        response = self.client.get('/api/orders/menu/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.customer)
        response = self.client.get('/api/orders/menu/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 8)
        self.assertEqual(response.data[0]['name'], 'Пицца Маргарита')
        self.assertEqual(response.data[0]['price'], '890.00')
        self.assertTrue(all(item['restaurant'] and item['restaurant_name'] for item in response.data))

        self.pizza.is_active = False
        self.pizza.save()
        response = self.client.get('/api/orders/menu/')
        self.assertEqual(len(response.data), 7)

    def test_order_creation(self):
        """Test order creation"""
        delivery_person = User.objects.create_user(
            username='courier',
            email='courier@example.com',
            password='pass123',
            role='delivery'
        )
        self.client.force_authenticate(user=self.customer)
        response = self.client.post('/api/orders/', {
            'status': 'delivered',
            'priority': 'urgent',
            'delivery_person': delivery_person.id,
            'delivery_address': '123 Test St',
            'items': [
                {
                    'item_id': self.pizza.id,
                    'item_name': 'Подменённое название',
                    'quantity': 2,
                    'price_per_item': '0.01'
                }
            ]
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['customer'], self.customer.id)
        self.assertTrue(response.data['order_number'])
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(response.data['priority'], 'normal')
        self.assertIsNone(response.data['delivery_person'])
        self.assertEqual(response.data['items'][0]['item_name'], self.pizza.name)
        self.assertEqual(str(response.data['items'][0]['price_per_item']), '890.00')
        self.assertEqual(str(response.data['total_amount']), '1780.00')
        order_item = OrderItem.objects.get(order_id=response.data['id'])
        self.assertEqual(order_item.menu_item, self.pizza)

    def test_order_rejects_non_positive_quantity_or_unknown_menu_item(self):
        self.client.force_authenticate(user=self.customer)
        for item_id, quantity in [(self.pizza.id, 0), (99999, 1)]:
            with self.subTest(item_id=item_id, quantity=quantity):
                response = self.client.post('/api/orders/', {
                    'delivery_address': '123 Test St',
                    'items': [{
                        'item_id': item_id,
                        'quantity': quantity,
                    }],
                }, format='json')
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_rejects_more_than_50_items(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post('/api/orders/', {
            'delivery_address': '123 Test St',
            'items': [{
                'item_id': self.pizza.id,
                'quantity': 51,
            }],
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_rejects_total_below_business_minimum(self):
        cheap_item = MenuItem.objects.create(
            name='Дешёвый тестовый товар',
            category='Тест',
            price='5.00',
            restaurant=self.pizza.restaurant,
        )
        self.client.force_authenticate(user=self.customer)
        response = self.client.post('/api/orders/', {
            'delivery_address': '123 Test St',
            'items': [{
                'item_id': cheap_item.id,
                'quantity': 1,
            }],
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_rejects_estimated_delivery_time_in_the_past(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post('/api/orders/', {
            'delivery_address': '123 Test St',
            'estimated_delivery_time': '2020-01-01T10:00:00Z',
            'items': [{
                'item_id': self.pizza.id,
                'quantity': 1,
            }],
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_list_customer(self):
        """Test that customers only see their own orders"""
        self.client.force_authenticate(user=self.customer)
        Order.objects.create(
            order_number='ORD-001',
            customer=self.customer,
            status='pending',
            priority='normal',
            total_amount=50.00,
            delivery_address='123 Test St'
        )
        
        other_customer = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='pass123',
            role='customer'
        )
        Order.objects.create(
            order_number='ORD-002',
            customer=other_customer,
            status='pending',
            priority='normal',
            total_amount=30.00,
            delivery_address='456 Other St'
        )
        
        response = self.client.get('/api/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['order_number'], 'ORD-001')

    def test_order_status_update(self):
        """Test order status update"""
        order = Order.objects.create(
            order_number='ORD-001',
            customer=self.customer,
            status='pending',
            priority='normal',
            total_amount=50.00,
            delivery_address='123 Test St'
        )
        
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(f'/api/orders/{order.id}/status/', {
            'status': 'cancelled'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')

    def test_customer_cannot_cancel_another_customers_order(self):
        other_customer = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='pass123',
            role='customer'
        )
        order = Order.objects.create(
            order_number='ORD-OTHER-001',
            customer=other_customer,
            status='pending',
            priority='normal',
            total_amount=50.00,
            delivery_address='456 Other St'
        )

        self.client.force_authenticate(user=self.customer)
        response = self.client.post(f'/api/orders/{order.id}/status/', {
            'status': 'cancelled'
        })

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')

    def test_delivery_person_must_follow_order_status_transitions(self):
        delivery_person = User.objects.create_user(
            username='courier',
            email='courier@example.com',
            password='pass123',
            role='delivery'
        )
        order = Order.objects.create(
            order_number='ORD-DELIVERY-001',
            customer=self.customer,
            delivery_person=delivery_person,
            status='confirmed',
            priority='normal',
            total_amount=50.00,
            delivery_address='123 Test St'
        )
        self.client.force_authenticate(user=delivery_person)

        response = self.client.post(f'/api/orders/{order.id}/status/', {
            'status': 'delivered'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')

        order.status = 'preparing'
        order.save()
        response = self.client.post(f'/api/orders/{order.id}/status/', {
            'status': 'delivering'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(f'/api/orders/{order.id}/status/', {
            'status': 'delivered'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        order.refresh_from_db()
        self.assertEqual(order.status, 'delivered')
        self.assertIsNotNone(order.actual_delivery_time)

    def test_customer_can_confirm_receipt_only_after_delivery(self):
        order = Order.objects.create(
            order_number='ORD-RECEIPT-001',
            customer=self.customer,
            status='delivering',
            priority='normal',
            total_amount=50.00,
            delivery_address='123 Test St',
        )
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(f'/api/orders/{order.id}/confirm-delivery/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsNone(Order.objects.get(id=order.id).delivery_confirmed_at)

        order.status = 'delivered'
        order.save()
        response = self.client.post(f'/api/orders/{order.id}/confirm-delivery/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertIsNotNone(order.delivery_confirmed_at)

        response = self.client.post(f'/api/orders/{order.id}/confirm-delivery/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        other_customer = User.objects.create_user(
            username='receipt-other',
            email='receipt-other@example.com',
            password='pass123',
            role='customer',
        )
        self.client.force_authenticate(user=other_customer)
        response = self.client.post(f'/api/orders/{order.id}/confirm-delivery/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_assigned_courier_can_manage_route_and_customer_can_view_it(self):
        courier = User.objects.create_user(
            username='route-courier',
            email='route-courier@example.com',
            password='pass123',
            role='delivery',
        )
        order = Order.objects.create(
            order_number='ORD-ROUTE-001',
            customer=self.customer,
            delivery_person=courier,
            status='confirmed',
            priority='normal',
            total_amount=50.00,
            delivery_address='123 Customer Street, Almaty',
        )

        self.client.force_authenticate(user=courier)
        response = self.client.put(
            f'/api/orders/{order.id}/route/',
            {'origin_address': 'JetFood Kitchen, Almaty', 'notes': 'Use the side entrance'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['origin_address'], 'JetFood Kitchen, Almaty')
        self.assertEqual(response.data['destination_address'], order.delivery_address)
        self.assertIn('origin=JetFood+Kitchen', response.data['directions_url'])

        self.client.force_authenticate(user=self.customer)
        response = self.client.get(f'/api/orders/{order.id}/route/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['notes'], 'Use the side entrance')
        response = self.client.patch(
            f'/api/orders/{order.id}/route/',
            {'notes': 'Customer must not edit route'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_route_cannot_be_created_without_origin_or_by_unassigned_courier(self):
        courier = User.objects.create_user(
            username='route-courier-unassigned',
            email='route-courier-unassigned@example.com',
            password='pass123',
            role='delivery',
        )
        order = Order.objects.create(
            order_number='ORD-ROUTE-002',
            customer=self.customer,
            status='confirmed',
            priority='normal',
            total_amount=50.00,
            delivery_address='123 Customer Street, Almaty',
        )
        self.client.force_authenticate(user=courier)
        response = self.client.put(
            f'/api/orders/{order.id}/route/',
            {'origin_address': 'Kitchen'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        order.delivery_person = courier
        order.save()
        response = self.client.patch(
            f'/api/orders/{order.id}/route/',
            {'notes': 'Missing origin'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(DeliveryRoute.objects.filter(order=order).exists())

    def test_customer_cannot_edit_or_delete_order_fields_directly(self):
        order = Order.objects.create(
            order_number='ORD-OWN-001',
            customer=self.customer,
            status='pending',
            priority='normal',
            total_amount=50.00,
            delivery_address='123 Test St'
        )
        self.client.force_authenticate(user=self.customer)

        response = self.client.patch(f'/api/orders/{order.id}/', {
            'status': 'delivered',
            'total_amount': '1.00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.delete(f'/api/orders/{order.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')
        self.assertEqual(str(order.total_amount), '50.00')

    def test_customer_can_modify_pending_order_items_and_address(self):
        order = Order.objects.create(
            order_number='ORD-MODIFY-001',
            customer=self.customer,
            status='pending',
            priority='normal',
            total_amount=self.pizza.price,
            delivery_address='Old address',
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.pizza,
            item_name=self.pizza.name,
            quantity=1,
            price_per_item=self.pizza.price,
            subtotal=self.pizza.price,
        )
        self.client.force_authenticate(user=self.customer)

        response = self.client.patch(f'/api/orders/{order.id}/modify/', {
            'delivery_address': 'New address',
            'delivery_notes': 'Leave at reception',
            'items': [{'item_id': self.pizza.id, 'quantity': 2}],
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.delivery_address, 'New address')
        self.assertEqual(order.delivery_notes, 'Leave at reception')
        self.assertEqual(str(order.total_amount), '1780.00')
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.get().quantity, 2)
        self.assertEqual(response.data['items'][0]['menu_item_id'], self.pizza.id)

    def test_customer_cannot_modify_order_after_confirmation(self):
        order = Order.objects.create(
            order_number='ORD-MODIFY-002',
            customer=self.customer,
            status='confirmed',
            priority='normal',
            total_amount='890.00',
            delivery_address='Old address',
        )
        self.client.force_authenticate(user=self.customer)

        response = self.client.patch(f'/api/orders/{order.id}/modify/', {
            'delivery_address': 'New address',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.delivery_address, 'Old address')

    def test_customer_cannot_modify_another_customers_order(self):
        other_customer = User.objects.create_user(
            username='modify-other',
            email='modify-other@example.com',
            password='pass123',
            role='customer',
        )
        order = Order.objects.create(
            order_number='ORD-MODIFY-003',
            customer=other_customer,
            status='pending',
            priority='normal',
            total_amount='890.00',
            delivery_address='Private address',
        )
        self.client.force_authenticate(user=self.customer)

        response = self.client.patch(f'/api/orders/{order.id}/modify/', {
            'delivery_address': 'Changed address',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        order.refresh_from_db()
        self.assertEqual(order.delivery_address, 'Private address')

    def test_order_summary(self):
        """Test order summary endpoint"""
        self.client.force_authenticate(user=self.admin)
        Order.objects.create(
            order_number='ORD-001',
            customer=self.customer,
            status='delivered',
            priority='normal',
            total_amount=50.00,
            delivery_address='123 Test St'
        )
        
        response = self.client.get('/api/orders/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_orders', response.data)
        self.assertIn('total_revenue', response.data)
