from datetime import time
from decimal import Decimal
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from restaurants.models import Restaurant, MenuCategory
from orders.models import MenuItem


# Fictional establishments; these are example prices, not live restaurant offers.
CATALOG = [
    ('pizza', 'Demo: Stone Oven', 'Italian', [
        ('Pizza', 'Margherita', 'Tomato, mozzarella and basil', 2900, 'margherita.jpg'),
        ('Pizza', 'Pepperoni', 'Tomato, mozzarella and pepperoni', 3400, ''),
        ('Pizza', 'Four cheese', 'Mozzarella, parmesan, blue cheese and gouda', 3800, ''),
        ('Pizza', 'Mushroom pizza', 'Mushrooms, mozzarella and herbs', 3200, ''),
        ('Pasta', 'Tomato spaghetti', 'Spaghetti with tomato sauce', 2600, ''),
        ('Pasta', 'Mushroom penne', 'Penne with mushrooms and cream', 3000, ''),
        ('Salads', 'Caprese', 'Tomato, mozzarella and basil salad', 2400, ''),
        ('Sides', 'Garlic bread', 'Toasted bread with garlic butter', 900, ''),
        ('Desserts', 'Tiramisu', 'Coffee and mascarpone dessert', 1800, ''),
        ('Drinks', 'Lemonade', 'Lemon drink, 400 ml', 850, ''),
    ]),
    ('grill', 'Demo: Ember Kitchen', 'Grill', [
        ('Burgers', 'Beef burger', 'Beef patty, lettuce and tomato', 2700, ''),
        ('Burgers', 'Cheeseburger', 'Beef patty and cheddar', 2900, ''),
        ('Burgers', 'Chicken burger', 'Chicken breast and fresh vegetables', 2500, ''),
        ('Grill', 'Chicken skewers', 'Grilled chicken with onions', 3100, ''),
        ('Grill', 'Beef skewers', 'Grilled beef with onions', 3900, ''),
        ('Sides', 'French fries', 'Salted fried potatoes', 1100, 'fries.jpg'),
        ('Sides', 'Grilled vegetables', 'Peppers, zucchini and aubergine', 1600, ''),
        ('Salads', 'Garden salad', 'Cucumber, tomato and greens', 1500, ''),
        ('Desserts', 'Brownie', 'Chocolate cake', 1400, ''),
        ('Drinks', 'Berry drink', 'Berry drink, 400 ml', 800, ''),
    ]),
    ('steppe', 'Demo: Steppe Table', 'Kazakh', [
        ('Main dishes', 'Beshbarmak', 'Beef with pasta and onion broth', 4200, ''),
        ('Main dishes', 'Quyrdaq', 'Fried beef with potatoes and onions', 3800, ''),
        ('Main dishes', 'Beef pilaf', 'Rice, carrots and beef', 2800, ''),
        ('Soups', 'Shorpa', 'Beef broth with vegetables', 2100, ''),
        ('Soups', 'Noodle soup', 'Chicken broth with noodles', 1900, ''),
        ('Sides', 'Baursak', 'Traditional fried dough, 200 g', 900, ''),
        ('Sides', 'Rice', 'Steamed rice, 150 g', 650, ''),
        ('Salads', 'Radish salad', 'Radish, carrot and herbs', 1300, ''),
        ('Desserts', 'Honey cake', 'Layered honey cake', 1600, ''),
        ('Drinks', 'Milk tea', 'Black tea with milk, 400 ml', 700, ''),
    ]),
    ('noodle', 'Demo: Noodle Corner', 'Asian', [
        ('Noodles', 'Chicken ramen', 'Noodles, chicken broth and egg', 3200, ''),
        ('Noodles', 'Vegetable udon', 'Udon noodles and stir fried vegetables', 2700, ''),
        ('Noodles', 'Beef noodles', 'Noodles with beef and peppers', 3400, ''),
        ('Rice', 'Chicken fried rice', 'Rice with chicken, egg and vegetables', 2800, ''),
        ('Rice', 'Vegetable fried rice', 'Rice with seasonal vegetables', 2400, ''),
        ('Soups', 'Miso soup', 'Miso broth, tofu and seaweed', 1700, ''),
        ('Sides', 'Chicken dumplings', 'Steamed chicken dumplings, 6 pieces', 2200, ''),
        ('Salads', 'Cucumber salad', 'Cucumber with sesame dressing', 1400, ''),
        ('Desserts', 'Mochi', 'Rice dough dessert, 2 pieces', 1500, ''),
        ('Drinks', 'Jasmine tea', 'Jasmine tea, 400 ml', 750, ''),
    ]),
    ('garden', 'Demo: Garden Lunch', 'Vegetarian', [
        ('Bowls', 'Chickpea bowl', 'Chickpeas, rice and vegetables', 2500, ''),
        ('Bowls', 'Lentil bowl', 'Lentils, carrots and herbs', 2400, ''),
        ('Bowls', 'Quinoa bowl', 'Quinoa, tomato and avocado', 3100, ''),
        ('Soups', 'Lentil soup', 'Red lentils and vegetables', 1800, ''),
        ('Soups', 'Pumpkin soup', 'Pumpkin cream soup', 2000, ''),
        ('Salads', 'Greek salad', 'Vegetables, olives and feta', 2200, ''),
        ('Salads', 'Beetroot salad', 'Baked beetroot with walnuts', 1700, ''),
        ('Sides', 'Baked potatoes', 'Potatoes with herbs', 1200, ''),
        ('Desserts', 'Apple pie', 'Apple and cinnamon pie', 1400, ''),
        ('Drinks', 'Mint lemonade', 'Lemon and mint drink, 400 ml', 900, ''),
    ]),
]


class Command(BaseCommand):
    help = 'Create 5 fictional demo restaurants and 50 dishes; never overwrite existing records.'

    def add_arguments(self, parser):
        parser.add_argument('--allow-production', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG and not options['allow_production']:
            raise CommandError('Demo data is disabled in production. Use --allow-production explicitly on a demo environment.')
        count = 0
        for index, (key, name, cuisine, dishes) in enumerate(CATALOG, 1):
            restaurant, created = Restaurant.objects.get_or_create(demo_key=f'catalog-v1-{key}', defaults={
                'name': name, 'cuisine': cuisine,
                'description': 'Fictional demonstration restaurant. Example KZT prices, not a real menu.',
                'address': f'Demo address {index}, not a delivery location',
                'opening_time': time(9), 'closing_time': time(22),
            })
            count += int(created)
            for number, (category_name, dish, description, price, photo) in enumerate(dishes, 1):
                demo_key = f'catalog-v1-{key}-{number}'
                if MenuItem.objects.filter(demo_key=demo_key).exists():
                    continue
                # A manually created collision is preserved rather than adopted or overwritten.
                if MenuItem.objects.filter(restaurant=restaurant, name=dish).exists():
                    continue
                category, _ = MenuCategory.objects.get_or_create(restaurant=restaurant, name=category_name)
                image_exists = photo and (Path(settings.BASE_DIR) / 'frontend/public/assets/demo-food' / photo).is_file()
                MenuItem.objects.create(demo_key=demo_key, restaurant=restaurant, menu_category=category,
                    category=category.name, name=dish, description=description, price=Decimal(price),
                    image_url=f'/assets/demo-food/{photo}' if image_exists else '')
        self.stdout.write(self.style.SUCCESS(f'Created {count} demo restaurants. Existing records were preserved.'))
