from django.db import migrations


def seed(apps, schema_editor):
    FAQ = apps.get_model('support', 'FAQ')
    entries = [
        ('order-status', 'Где мой заказ?', 'Откройте «Заказы». Там показан текущий статус. Время прибытия, если указано, является оценкой. В чате можно привязать только свой заказ.',
         'Тапсырысым қайда?', '«Тапсырыстар» бөлімін ашыңыз. Онда ағымдағы күйі көрсетіледі. Келу уақыты көрсетілсе, ол — болжам. Чатқа тек өз тапсырысыңызды байланыстыра аласыз.',
         'Where is my order?', 'Open Orders for the current status. Any arrival time is an estimate. You can link only your own order in chat.'),
        ('promo', 'Почему не применяется промокод?', 'Проверьте срок действия, ресторан, минимальную стоимость товаров и лимиты. Пробелы по краям и регистр не влияют. На заказ действует один код. Скидка на товары не уменьшает доставку.',
         'Промокод неге қолданылмайды?', 'Мерзімді, мейрамхананы, тауарлардың ең төменгі сомасын және лимиттерді тексеріңіз. Шеткі бос орындар мен әріп регистрі әсер етпейді. Бір тапсырысқа бір код қолданылады. Тауар жеңілдігі жеткізу құнын азайтпайды.',
         'Why does my promo code fail?', 'Check dates, restaurant, minimum item subtotal and limits. Surrounding spaces and case do not matter. One code applies per order. Item discounts do not reduce delivery fees.'),
        ('payment', 'Как работает оплата?', 'Онлайн-оплата в текущей версии — симуляция. Также доступна оплата наличными при доставке. Чат не выполняет платежи и возвраты. Не отправляйте платёжные данные в чат.',
         'Төлем қалай жасалады?', 'Қазіргі нұсқада онлайн төлем — симуляция. Жеткізгенде қолма-қол төлеуге де болады. Чат төлем мен қайтарымды орындамайды. Төлем деректерін чатқа жібермеңіз.',
         'How do payments work?', 'Online payment in this version is a simulation. Cash on delivery is also available. Chat cannot make payments or refunds. Do not send payment details in chat.'),
        ('support', 'Как обратиться к сотруднику?', 'Опишите проблему и нажмите «Создать обращение оператору». Обращение и история сохранятся для просмотра сотрудниками в админке. Подключение оператора в реальном времени и срок ответа не предусмотрены.',
         'Қызметкерге қалай хабарласамын?', 'Мәселені сипаттап, «Операторға өтініш жасау» түймесін басыңыз. Өтініш пен әңгіме тарихы әкімшілік панельде қарау үшін сақталады. Оператордың бірден қосылуы мен жауап мерзімі қарастырылмаған.',
         'How do I contact staff?', 'Describe the issue and choose Create operator request. Your request and transcript are saved for staff in admin. Live operator connection and a response deadline are not available.'),
    ]
    fields = ['question_ru', 'answer_ru', 'question_kk', 'answer_kk', 'question_en', 'answer_en']
    for slug, *values in entries:
        FAQ.objects.using(schema_editor.connection.alias).get_or_create(slug=slug, defaults=dict(zip(fields, values)))


class Migration(migrations.Migration):
    dependencies = [('support', '0002_faq_supportcase_language_and_more')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
