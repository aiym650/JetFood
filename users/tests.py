from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO
from orders.models import Order
from .models import DeliveryAddress, Notification, User

User = get_user_model()


class UserTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='customer'
        )
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123',
            role='admin'
        )
        self.client = APIClient()

    def test_user_creation(self):
        """Test user creation"""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.role, 'customer')

    def test_create_demo_roles_command_generates_role_accounts_once(self):
        output = StringIO()
        call_command('create_demo_roles', stdout=output)
        demo_admin = User.objects.get(username='demo_admin')
        demo_manager = User.objects.get(username='demo_manager')
        demo_courier = User.objects.get(username='demo_courier')

        self.assertEqual(demo_admin.role, 'admin')
        self.assertTrue(demo_admin.is_superuser)
        self.assertEqual(demo_manager.role, 'manager')
        self.assertEqual(demo_courier.role, 'delivery')
        self.assertTrue(demo_admin.check_password(output.getvalue().split('demo_admin / ')[1].splitlines()[0]))

        repeated_output = StringIO()
        call_command('create_demo_roles', stdout=repeated_output)
        self.assertIn('already exist', repeated_output.getvalue())

    def test_create_demo_roles_command_does_not_elevate_existing_user(self):
        User.objects.create_user(
            username='demo_manager',
            email='existing@example.com',
            password='safe-password',
            role='customer',
        )
        with self.assertRaises(CommandError):
            call_command('create_demo_roles', stdout=StringIO())
        self.assertEqual(User.objects.get(username='demo_manager').role, 'customer')

    def test_user_login(self):
        """Test user login endpoint"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_invalid_login(self):
        """Test invalid login credentials"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_registration(self):
        """Test user registration"""
        response = self.client.post('/api/auth/register/', {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'role': 'admin'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get(username='newuser').role, 'customer')

    def test_registration_reports_duplicate_username_and_email(self):
        duplicate_username = self.client.post('/api/auth/register/', {
            'username': 'testuser',
            'email': 'new@example.com',
            'password': 'newpass123',
        }, format='json')
        self.assertEqual(duplicate_username.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', duplicate_username.data)

        duplicate_email = self.client.post('/api/auth/register/', {
            'username': 'anotheruser',
            'email': 'TEST@example.com',
            'password': 'newpass123',
        }, format='json')
        self.assertEqual(duplicate_email.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', duplicate_email.data)

    def test_logout_revokes_token(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.post('/api/auth/logout/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Token.objects.filter(user=self.user).exists())
        self.assertEqual(
            self.client.get('/api/auth/profile/').status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_users_cannot_change_their_own_role(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(f'/api/auth/users/{self.user.id}/', {
            'username': self.user.username,
            'email': self.user.email,
            'role': 'admin',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'customer')

        response = self.client.patch('/api/auth/profile/', {'role': 'admin'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'customer')

    def test_admin_user_creation_is_admin_only_and_accepts_role(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/auth/users/create/', {
            'username': 'blockeduser',
            'email': 'blocked@example.com',
            'password': 'newpass123',
            'role': 'manager',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(User.objects.filter(username='blockeduser').exists())

        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/auth/users/create/', {
            'username': 'manageduser',
            'email': 'managed@example.com',
            'password': 'newpass123',
            'role': 'manager',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get(username='manageduser').role, 'manager')

    def test_non_admin_cannot_retrieve_other_users_by_id(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/auth/users/{self.admin.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_role_update_admin_only(self):
        """Test that only admins can update roles"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/auth/users/{self.user.id}/role/', {
            'role': 'manager'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/auth/users/{self.user.id}/role/', {
            'role': 'manager'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_address_book_defaults_and_is_private_to_the_owner(self):
        other_user = User.objects.create_user(
            username='other', password='pass12345', role='customer'
        )
        self.client.force_authenticate(user=self.user)
        first = self.client.post('/api/auth/addresses/', {
            'label': 'Home',
            'address_line': '1 Main Street',
            'city': 'Astana',
        }, format='json')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertTrue(first.data['is_default'])

        second = self.client.post('/api/auth/addresses/', {
            'label': 'Work',
            'address_line': '2 Office Road',
            'city': 'Astana',
            'is_default': True,
        }, format='json')
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertFalse(DeliveryAddress.objects.get(pk=first.data['id']).is_default)
        self.assertTrue(DeliveryAddress.objects.get(pk=second.data['id']).is_default)

        self.client.force_authenticate(user=other_user)
        response = self.client.get('/api/auth/addresses/')
        self.assertEqual(response.data['results'], [])
        response = self.client.get(f"/api/auth/addresses/{first.data['id']}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_address_deleting_default_promotes_another_address(self):
        first = DeliveryAddress.objects.create(
            user=self.user, label='Home', address_line='1 Main Street',
            city='Astana', is_default=True,
        )
        second = DeliveryAddress.objects.create(
            user=self.user, label='Work', address_line='2 Office Road',
            city='Astana',
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(f'/api/auth/addresses/{first.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        second.refresh_from_db()
        self.assertTrue(second.is_default)

    def test_change_password_requires_the_current_password(self):
        self.client.force_authenticate(user=self.user)
        invalid = self.client.post('/api/auth/change-password/', {
            'old_password': 'wrong-password',
            'new_password': 'newpass456',
        }, format='json')
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('testpass123'))

        valid = self.client.post('/api/auth/change-password/', {
            'old_password': 'testpass123',
            'new_password': 'newpass456',
        }, format='json')
        self.assertEqual(valid.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass456'))

    def test_account_deletion_is_blocked_while_orders_are_active(self):
        Order.objects.create(
            order_number='ORD-ACTIVE-001',
            customer=self.user,
            total_amount='100.00',
            delivery_address='1 Main Street',
            status='preparing',
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.delete('/api/auth/account/', {
            'password': 'testpass123',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_account_deletion_anonymizes_and_preserves_order_history(self):
        address = DeliveryAddress.objects.create(
            user=self.user,
            label='Home',
            address_line='1 Main Street',
            city='Astana',
            is_default=True,
        )
        order = Order.objects.create(
            order_number='ORD-DONE-001',
            customer=self.user,
            total_amount='100.00',
            delivery_address='1 Main Street, Astana',
            delivery_notes='Call me at 12345',
            status='delivered',
        )
        notification = Notification.objects.create(
            user=self.user,
            notification_type='system',
            title='Account notice',
            message='Personal notification',
        )
        token = Token.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user)

        response = self.client.delete('/api/auth/account/', {
            'password': 'testpass123',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        order.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.has_usable_password())
        self.assertEqual(self.user.email, '')
        self.assertEqual(order.delivery_address, '')
        self.assertEqual(order.delivery_notes, '')
        self.assertFalse(DeliveryAddress.objects.filter(pk=address.pk).exists())
        self.assertFalse(Notification.objects.filter(pk=notification.pk).exists())
        self.assertFalse(Token.objects.filter(pk=token.pk).exists())
