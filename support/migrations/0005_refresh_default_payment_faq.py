from django.db import migrations


def refresh_defaults(apps, schema_editor):
    FAQ = apps.get_model('support', 'FAQ')
    updates = {
        'answer_en': (
            'Online payment in this version is a simulation. Cash on delivery is also available. Chat cannot make payments or refunds. Do not send payment details in chat.',
            'Online payment uses the Freedom Pay hosted page when merchant credentials are configured. Test mode is labelled explicitly. The backend verifies payment; a redirect alone is not confirmation. Cash on delivery is also available. Chat cannot make payments or refunds. Never send card details in chat.'),
        'answer_ru': (
            'Онлайн-оплата в текущей версии — симуляция. Также доступна оплата наличными при доставке. Чат не выполняет платежи и возвраты. Не отправляйте платёжные данные в чат.',
            'Онлайн-оплата проходит на странице Freedom Pay, если настроены ключи продавца. Тестовый режим обозначен отдельно. Оплату подтверждает сервер; возврат на сайт сам по себе не подтверждает платёж. Также можно оплатить наличными при доставке. Чат не проводит платежи и возвраты. Не отправляйте данные карты в чат.'),
        'answer_kk': (
            'Қазіргі нұсқада онлайн төлем — симуляция. Жеткізгенде қолма-қол төлеуге де болады. Чат төлем мен қайтарымды орындамайды. Төлем деректерін чатқа жібермеңіз.',
            'Сатушы кілттері бапталса, онлайн төлем Freedom Pay бетінде жасалады. Сынақ режимі бөлек белгіленеді. Төлемді сервер тексереді; сайтқа оралу төлемді растамайды. Жеткізгенде қолма-қол төлеуге болады. Чат төлем мен қайтарымды орындамайды. Карта деректерін чатқа жібермеңіз.'),
    }
    for field, (old, new) in updates.items():
        # Never overwrite manually edited FAQ in any language.
        FAQ.objects.using(schema_editor.connection.alias).filter(slug='payment', **{field: old}).update(**{field: new})


class Migration(migrations.Migration):
    dependencies = [('support', '0004_supportcase_ai_busy_until')]
    operations = [migrations.RunPython(refresh_defaults, migrations.RunPython.noop)]
