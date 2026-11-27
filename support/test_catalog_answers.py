from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from orders.models import MenuItem
from restaurants.models import Restaurant
from users.models import User
from .catalog_answers import catalog_answer


class CatalogAnswerTests(TestCase):
    def setUp(self):
        cache.clear()
        self.restaurant = Restaurant.objects.create(name='Bahandi Burger', address='Public')
        self.burger = MenuItem.objects.create(restaurant=self.restaurant, name='Бургер курица', category='Бургеры', price='1500.00')
        MenuItem.objects.create(restaurant=self.restaurant, name='Бургер говядина', category='Бургеры', price='1650.00')
        MenuItem.objects.create(restaurant=self.restaurant, name='Картофель фри', category='Гарниры', price='750.00')
        self.salam = Restaurant.objects.create(name='Salam Bro', address='Public')

    def answer(self, text, language='ru', previous=None):
        messages = [{'sender': 'customer', 'body': value} for value in ([previous] if previous else []) + [text]]
        return catalog_answer(language, messages)

    def test_doner_in_bahandi_does_not_get_the_price_of_fries(self):
        reply = self.answer('сколько стоит донер в баханди')
        self.assertIn('не найдено', reply)
        self.assertNotIn('750', reply)
        self.assertNotIn('1500', reply)

    def test_current_price_tracks_database_changes_without_training(self):
        MenuItem.objects.create(restaurant=self.restaurant, name='Чизбургер курица', category='Бургеры', price='1700.00')
        reply = self.answer('сколько стоит бургер курица в Баханди')
        self.assertIn('Бургер курица', reply)
        self.assertIn('1500.00 ₸', reply)
        self.assertNotIn('1650', reply)
        self.assertNotIn('1700', reply)
        self.burger.price = Decimal('1735.25')
        self.burger.save()
        reply = self.answer('сколько стоит бургер курица в Баханди')
        self.assertIn('1735.25 ₸', reply)
        self.assertNotIn('1500', reply)

    def test_missing_menu_never_borrows_bahandi_price(self):
        reply = self.answer('Сколько стоят бургеры в Салам Броэ?')
        self.assertIn('меню ещё не загружено', reply)
        self.assertNotIn('1500', reply)

    def test_restaurant_change_in_follow_up_keeps_dish_type(self):
        reply = self.answer('а в баханди?', previous='Сколько стоит донер в Салам Бро?')
        self.assertIn('Bahandi Burger', reply)
        self.assertIn('не найдено', reply)
        self.assertNotIn('750', reply)

    def test_exact_prices_and_unavailability_in_all_three_languages(self):
        self.burger.is_active = False
        self.burger.save()
        for language, question, word in [
            ('ru', 'Цены на бургеры в Bahandi Burger', 'недоступно'),
            ('en', 'burger prices at Bahandi Burger', 'unavailable'),
            ('kk', 'Bahandi Burger бургер бағасы қанша?', 'қолжетімсіз'),
        ]:
            with self.subTest(language=language):
                reply = self.answer(question, language)
                self.assertIn('1500.00 ₸', reply)
                self.assertIn('1650.00 ₸', reply)
                self.assertIn(word, reply)
                self.assertNotIn('750.00', reply)

    def test_ambiguous_restaurant_requires_clarification_and_not_random_prices(self):
        reply = self.answer('сколько стоит бургер?')
        self.assertIn('Уточните название ресторана', reply)
        self.assertNotIn('1500', reply)

    def test_payment_and_promotions_are_not_routed_to_the_menu(self):
        self.assertIsNone(self.answer('Почему не начислили JetPoints?'))
        self.assertIsNone(self.answer('Какая минимальная сумма заказа для WELCOME?'))

    @patch('support.views.generate_support_reply', side_effect=AssertionError('LLM must not author prices'))
    def test_real_chat_api_persists_catalog_source_and_reads_latest_price(self, provider):
        user = User.objects.create_user(username='catalog-customer')
        client = APIClient()
        client.force_authenticate(user)
        case = client.post('/api/support/cases/', {'language': 'ru'}, format='json')
        self.assertEqual(case.status_code, 201, case.data)
        url = f"/api/support/cases/{case.data['id']}/messages/"
        for index, price in enumerate(['1500.00', '1777.35']):
            MenuItem.objects.filter(pk=self.burger.pk).update(price=price)
            result = client.post(url, {'body': 'сколько стоит бургер курица в баханди', 'request_id': f'catalog-{index}'}, format='json')
            self.assertEqual(result.status_code, 200, result.data)
            answer = result.data['messages'][-1]
            self.assertEqual(answer['source'], 'catalog')
            self.assertIn(price+' ₸', answer['body'])
        restored = client.get(f"/api/support/cases/{case.data['id']}/")
        self.assertEqual(restored.data['messages'][-1]['source'], 'catalog')
        provider.assert_not_called()
