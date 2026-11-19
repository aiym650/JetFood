import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from orders.models import Order
from payments.models import Payment
from .assistant import SupportAIUnavailable, generate_support_reply
from .models import SupportCase, SupportMessage


User = get_user_model()


class SupportCaseApiTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='support-customer',
            email='support-customer@example.com',
            password='testpass123',
            role='customer',
        )
        self.other_customer = User.objects.create_user(
            username='other-customer',
            email='other-customer@example.com',
            password='testpass123',
            role='customer',
        )
        self.manager = User.objects.create_user(
            username='support-manager',
            email='support-manager@example.com',
            password='testpass123',
            role='manager',
        )
        self.order = Order.objects.create(
            order_number='SUPPORT-ORDER-1',
            customer=self.customer,
            status='delivering',
            priority='normal',
            total_amount='50.00',
            delivery_address='1 Main Street',
        )
        self.client = APIClient()

    def create_case(self, description):
        self.client.force_authenticate(user=self.customer)
        return self.client.post('/api/support/cases/', {
            'order_number': self.order.order_number,
            'issue_description': description,
        }, format='json')

    @patch('support.views.generate_support_reply', return_value='Ваш заказ доставляется.')
    def test_customer_case_gets_ai_answer_and_saved_transcript(self, generate_reply):
        response = self.create_case('Где мой заказ? Хочу узнать статус.')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['order_number'], self.order.order_number)
        self.assertEqual(response.data['status'], 'waiting_for_customer')
        self.assertEqual(len(response.data['messages']), 2)
        self.assertEqual(response.data['messages'][0]['sender'], 'customer')
        self.assertEqual(response.data['messages'][1]['sender'], 'assistant')
        self.assertEqual(response.data['messages'][1]['body'], 'Ваш заказ доставляется.')
        self.assertEqual(SupportMessage.objects.filter(support_case_id=response.data['id']).count(), 2)
        generate_reply.assert_called_once()

    def test_customer_must_own_the_order_number(self):
        self.client.force_authenticate(user=self.other_customer)

        response = self.client.post('/api/support/cases/', {
            'order_number': self.order.order_number,
            'issue_description': 'Please help with this order.',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SupportCase.objects.count(), 0)

    @patch('support.views.generate_support_reply', return_value='Конечно, помогу.')
    def test_customer_can_start_ai_chat_without_an_order_number(self, generate_reply):
        self.client.force_authenticate(user=self.customer)

        response = self.client.post('/api/support/cases/', {
            'issue_description': 'Как изменить адрес доставки?',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['order'])
        self.assertEqual(response.data['order_number'], '')
        self.assertEqual(response.data['messages'][-1]['sender'], 'assistant')
        generate_reply.assert_called_once()

    @patch('support.views.generate_support_reply', return_value='Проверьте состав заказа.')
    def test_ai_answers_unknown_issues_instead_of_queueing_for_staff(self, _generate_reply):
        response = self.create_case('В заказе отсутствует один из товаров.')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'waiting_for_customer')
        self.assertEqual(response.data['messages'][-1]['sender'], 'assistant')
        self.assertEqual(response.data['messages'][-1]['body'], 'Проверьте состав заказа.')
        self.assertNotIn('сотруднику поддержки', response.data['messages'][-1]['body'])

    @patch('support.views.generate_support_reply', return_value='ИИ проверит информацию по оплате.')
    def test_customer_can_continue_the_ai_conversation(self, _generate_reply):
        created = self.create_case('Мне нужна помощь с заказом.')
        case_id = created.data['id']

        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            f'/api/support/cases/{case_id}/messages/',
            {'body': 'Проблема связана с возвратом денег.'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'waiting_for_customer')
        self.assertEqual(response.data['messages'][-1]['sender'], 'assistant')
        self.assertEqual(response.data['messages'][-1]['body'], 'ИИ проверит информацию по оплате.')
        self.assertFalse(any(message['sender'] == 'staff' for message in response.data['messages']))

    @patch('support.views.generate_support_reply', return_value='Здравствуйте, чем помочь?')
    def test_staff_cannot_read_or_reply_to_ai_conversations(self, _generate_reply):
        created = self.create_case('Нужна помощь.')
        case_id = created.data['id']
        self.client.force_authenticate(user=self.manager)

        list_response = self.client.get('/api/support/cases/')
        reply_response = self.client.post(
            f'/api/support/cases/{case_id}/messages/',
            {'body': 'Я отвечаю вместо ИИ.'},
            format='json',
        )

        self.assertEqual(list_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(reply_response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(
        'support.views.generate_support_reply',
        side_effect=SupportAIUnavailable(),
    )
    def test_unavailable_ai_keeps_the_chat_and_message_for_retry(self, _generate_reply):
        response = self.create_case('Пожалуйста, помогите с заказом.')

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(SupportCase.objects.count(), 1)
        self.assertEqual(SupportMessage.objects.count(), 1)
        self.assertEqual(response.data['case_id'], SupportCase.objects.get().pk)

    def test_customer_cannot_read_another_customers_case(self):
        case = SupportCase.objects.create(
            customer=self.customer,
            order=self.order,
            order_number=self.order.order_number,
            issue_description='A private support request.',
        )
        self.client.force_authenticate(user=self.other_customer)

        response = self.client.post(
            f'/api/support/cases/{case.id}/messages/',
            {'body': 'Trying to access another case.'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SupportOllamaTests(TestCase):
    def setUp(self):
        customer = User.objects.create_user(
            username='ollama-customer',
            password='testpass123',
            role='customer',
        )
        order = Order.objects.create(
            order_number='OLLAMA-ORDER-1',
            customer=customer,
            status='delivering',
            priority='normal',
            total_amount='50.00',
            delivery_address='Private address must not be sent.',
            estimated_arrival_time=timezone.now(),
        )
        Payment.objects.create(
            order=order,
            method='online',
            status='paid',
            amount='50.00',
            paid_at=timezone.now(),
            transaction_id='private-transaction-id',
        )
        self.case = SupportCase.objects.create(
            customer=customer,
            order=order,
            order_number=order.order_number,
            issue_description='Где мой заказ?',
        )

    @override_settings(
        SUPPORT_OLLAMA_BASE_URL='http://127.0.0.1:11434/',
        SUPPORT_OLLAMA_MODEL='test-model',
        SUPPORT_OLLAMA_TIMEOUT=7,
    )
    @patch('support.assistant.urlopen')
    def test_request_uses_local_ollama_and_minimized_order_context(self, urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({
            'message': {'content': 'Ваш заказ доставляется.'},
        }).encode('utf-8')
        response.__enter__.return_value = response
        urlopen.return_value = response

        reply = generate_support_reply(
            self.case,
            [{'sender': 'customer', 'body': 'Где мой заказ?'}],
        )

        request = urlopen.call_args.args[0]
        request_data = json.loads(request.data.decode('utf-8'))
        self.assertEqual(request.full_url, 'http://127.0.0.1:11434/api/chat')
        self.assertEqual(urlopen.call_args.kwargs['timeout'], 7)
        self.assertEqual(request_data['model'], 'test-model')
        self.assertFalse(request_data['stream'])
        self.assertEqual(reply, 'Ваш заказ доставляется.')
        self.assertIn('OLLAMA-ORDER-1', request_data['messages'][0]['content'])
        self.assertIn('Online simulation', request_data['messages'][0]['content'])
        self.assertNotIn('Private address', request_data['messages'][0]['content'])
        self.assertNotIn('private-transaction-id', request_data['messages'][0]['content'])
        self.assertEqual(request_data['messages'][1]['role'], 'user')

    @patch('support.assistant.urlopen', side_effect=URLError('connection refused'))
    def test_ollama_connection_error_is_reported_as_ai_unavailable(self, _urlopen):
        with self.assertRaises(SupportAIUnavailable):
            generate_support_reply(
                self.case,
                [{'sender': 'customer', 'body': 'Помогите.'}],
            )
