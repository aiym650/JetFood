from datetime import time

from django.db import migrations, models
import django.db.models.deletion


def attach_menu_items_to_restaurants(apps, schema_editor):
    Restaurant = apps.get_model('restaurants', 'Restaurant')
    MenuItem = apps.get_model('orders', 'MenuItem')

    definitions = [
        ('Джет Пицца', 'Пицца и паста', 'Алматы, улица Абая, 10'),
        ('Гриль Хаус', 'Бургеры и блюда на гриле', 'Алматы, улица Сатпаева, 25'),
        ('Азиатская кухня', 'Супы и суши', 'Алматы, улица Панфилова, 8'),
        ('Свежий стол', 'Салаты и легкие блюда', 'Алматы, проспект Достык, 14'),
    ]
    restaurants = {}
    for name, description, address in definitions:
        restaurant, _ = Restaurant.objects.get_or_create(
            name=name,
            defaults={
                'description': description,
                'address': address,
                'opening_time': time(9, 0),
                'closing_time': time(22, 0),
                'working_days': list(range(7)),
                'is_active': True,
            },
        )
        restaurants[name] = restaurant

    category_restaurants = {
        'Пицца': 'Джет Пицца',
        'Паста': 'Джет Пицца',
        'Бургеры': 'Гриль Хаус',
        'Мясо': 'Гриль Хаус',
        'Мексиканская': 'Гриль Хаус',
        'Супы': 'Азиатская кухня',
        'Суши': 'Азиатская кухня',
        'Салаты': 'Свежий стол',
    }

    for item in MenuItem.objects.filter(restaurant__isnull=True).iterator():
        preferred = restaurants[category_restaurants.get(item.category, 'Джет Пицца')]
        candidates = [preferred, *[value for value in restaurants.values() if value.pk != preferred.pk]]
        item.restaurant = next((
            candidate for candidate in candidates
            if not MenuItem.objects.filter(restaurant=candidate, name=item.name).exists()
        ), None)
        if item.restaurant is None:
            item.restaurant = Restaurant.objects.create(
                name=f'Дополнительное меню {item.pk}',
                description='Блюда без категории из предыдущего каталога',
                address='Алматы',
                opening_time=time(9, 0),
                closing_time=time(22, 0),
                working_days=list(range(7)),
                is_active=True,
            )
        item.save(update_fields=['restaurant'])


class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0006_menuitem_menuitem_price_positive_and_more'),
        ('restaurants', '0002_restaurant_restaurant_opening_differs_from_closing'),
    ]

    operations = [
        migrations.RunPython(attach_menu_items_to_restaurants, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='menuitem',
            name='restaurant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='menu_items',
                to='restaurants.restaurant',
            ),
        ),
    ]