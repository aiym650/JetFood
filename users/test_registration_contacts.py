from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class OptionalRegistrationContactsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_omitted_and_blank_contacts_both_work_and_password_is_preserved(self):
        for index, contacts in enumerate([{}, {'email': '', 'phone': ''}, {'email': '  ', 'phone': '  '}, {'phone': '+77011234567'}]):
            result = self.client.post('/api/auth/register/', {'username': f'optional-{index}', 'password': '  testpass123  ', **contacts}, format='json')
            self.assertEqual(result.status_code, 201, result.data)
            user = get_user_model().objects.get(username=f'optional-{index}')
            self.assertTrue(user.check_password('  testpass123  '))

    def test_invalid_contacts_report_the_drf_field(self):
        for field, value in [('phone', 'abc123'), ('email', 'test@')]:
            result = self.client.post('/api/auth/register/', {'username': 'bad-contact', 'password': 'testpass123', field: value}, format='json')
            self.assertEqual(result.status_code, 400)
            self.assertIn(field, result.data)
