from django.core.management.base import BaseCommand
from support.models import FAQ


class Command(BaseCommand):
    help = 'Add verified service FAQ without overwriting administrator edits. Live monetary rules come from backend context.'

    def handle(self, *args, **options):
        entries = [
            ('verified-checkout', 'Как оформить заказ?', 'Выберите ресторан и блюда, откройте корзину, укажите адрес и способ оплаты. Сумму, промокод и допустимое списание бонусов проверяет сервер.',
             'How do I place an order?', 'Choose a restaurant and dishes, open the cart, enter an address and payment method. The server verifies prices, promo and allowed bonus redemption.',
             'Тапсырысты қалай беремін?', 'Мейрамхана мен тағамдарды таңдап, себетті ашыңыз. Мекенжай мен төлем тәсілін көрсетіңіз. Баға, промокод пен бонусты сервер тексереді.'),
            ('verified-payment', 'Как проверить оплату?', 'Откройте раздел «Платежи». Онлайн-оплату подтверждает сервер после проверки у провайдера. Возвращение на сайт само по себе не означает успешную оплату. Не вводите данные карты в чат.',
             'How do I check payment?', 'Open Payments. The backend confirms online payment with the provider. Returning to the website alone does not mean payment succeeded. Never enter card details in chat.',
             'Төлемді қалай тексеремін?', '«Төлемдер» бөлімін ашыңыз. Онлайн төлемді сервер провайдерден тексерген соң растайды. Сайтқа оралу төлемнің сәтті болғанын білдірмейді. Карта деректерін чатқа жазбаңыз.'),
            ('verified-cashback', 'Где посмотреть бонусы?', 'Доступный баланс и история операций находятся в профиле. В корзине сервер показывает лимит списания и прогноз начисления. Доставка бонусами не оплачивается. Актуальные проценты и условия помощник получает с сервера.',
             'Where can I see my bonuses?', 'Your profile shows available bonuses and ledger history. The cart displays the server spending limit and earnings forecast. Bonuses do not pay for delivery. Current rates and terms are read from backend settings.',
             'Бонустарды қайдан көремін?', 'Қолжетімді бонус пен операциялар тарихы профильде көрсетіледі. Себетте сервер есептеген шек пен болжам бар. Жеткізуге бонус жұмсалмайды. Ағымдағы шарттар серверден алынады.'),
            ('verified-reviews', 'Как исправить отзыв?', 'В разделе «Заказы» найдите свой отзыв и нажмите «Редактировать». После изменения он снова проходит модерацию и временно не публикуется. Причину отклонения видит автор. Обычная негативная оценка разрешена.',
             'How do I edit a review?', 'Find your review in Orders and select Edit. An edited review is hidden until moderation approves it again. Its author can see the rejection reason. Ordinary negative feedback is allowed.',
             'Пікірді қалай түзетемін?', '«Тапсырыстар» бөлімінен өз пікіріңізді тауып, «Өңдеу» батырмасын басыңыз. Өзгерген пікір модерацияға жіберіліп, мақұлданғанша жарияланбайды. Бас тарту себебі авторға көрінеді.'),
        ]
        created = 0
        for slug, qr, ar, qe, ae, qk, ak in entries:
            _, new = FAQ.objects.get_or_create(slug=slug, defaults=dict(question_ru=qr, answer_ru=ar, question_en=qe, answer_en=ae, question_kk=qk, answer_kk=ak))
            created += new
        self.stdout.write(f'Created {created} FAQ entries; existing edits preserved.')
