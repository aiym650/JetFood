from django.db import migrations


def add_restaurant_photos(apps, schema_editor):
    Restaurant = apps.get_model('restaurants', 'Restaurant')
    MenuItem = apps.get_model('orders', 'MenuItem')
    featured_dishes = {
        'Джет Пицца': 'Пицца Маргарита',
        'Гриль Хаус': 'Бургер Классический',
        'Азиатская кухня': 'Суши сет',
        'Свежий стол': 'Салат Цезарь',
    }

    for restaurant_name, dish_name in featured_dishes.items():
        restaurant = Restaurant.objects.filter(name=restaurant_name).first()
        if restaurant is None or restaurant.image_url:
            continue

        image_url = MenuItem.objects.filter(
            restaurant_id=restaurant.pk,
            name=dish_name,
        ).exclude(image_url='').values_list('image_url', flat=True).first()
        if image_url:
            restaurant.image_url = image_url
            restaurant.save(update_fields=['image_url'])


class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0007_link_menu_items_to_restaurants'),
        ('restaurants', '0002_restaurant_restaurant_opening_differs_from_closing'),
    ]

    operations = [
        migrations.RunPython(add_restaurant_photos, migrations.RunPython.noop),
    ]