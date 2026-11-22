from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from orders.models import MenuItem
from restaurants.models import Restaurant, RestaurantBranch


CATALOG = [
    {
        'key': 'doner-na-abaya',
        'name': 'Doner na Abaya',
        'cuisine': 'Донер и шаурма',
        'branches': [
            ('abaya-89', 'проспект Абая, 89', '70000001094746199'),
            ('abaya-160-5', 'проспект Абая, 160/5', '70000001102712445'),
            ('microdistrict-8-1a', '8-й микрорайон, 1А', '70000001088824870'),
        ],
        'menu_source_url': 'https://eda.yandex.kz/r/doner_na_abaya',
        'dishes': [
            ('Комбо', 'Комбо 1,5 куриного донера и напиток', '2672'),
            ('Комбо', 'Комбо 1,5 ассорти донера и напиток', '3186'),
            ('Комбо', 'Комбо 1,5 говяжьего донера и напиток', '3276'),
        ],
    },
    {
        'key': 'doner-na-satpayeva',
        'name': 'Doner na Satpaeva',
        'cuisine': 'Донер и шаурма',
        'branches': [
            ('baitursynov-106', 'улица Байтурсынова, 106', '70000001066773731'),
            ('sary-arka-4-28-1', '4-й микрорайон, 28/1', '70000001093057202'),
            ('radostovtsa-292-4', 'улица Радостовца, 292/4', '70000001079768705'),
        ],
        'menu_source_url': 'https://eda.yandex.kz/r/doner_na_satpayeva',
        'dishes': [
            ('Комбо', 'Комбо Level up Assorti 1,5', '3120'),
            ('Донеры', 'Донер в лаваше 1,5 говяжий и Напиток днс', '3200'),
            ('Донеры', 'Донер в лаваше 1,5 куриный и Напиток днс', '2960'),
            ('Комбо', 'Комбо Чипс Донер Куриный Днс', '1920'),
        ],
    },
    {
        'key': 'popeyes',
        'name': 'Popeyes',
        'cuisine': 'Жареная курица',
        'branches': [
            ('rozybakiev-162-3', 'улица Розыбакиева, 162/3', '70000001093686407'),
            ('abay-60', 'проспект Абая, 60', '70000001088226560'),
            ('panfilov-92', 'улица Панфилова, 92', '70000001100626766'),
        ],
        'menu_source_url': '',
        'dishes': [],
    },
    {
        'key': 'bahandi-burger',
        'name': 'Bahandi Burger',
        'cuisine': 'Бургеры',
        'branches': [
            ('abay-27', 'проспект Абая, 27', '70000001038820501'),
            ('samal-3-4d', 'Самал-3, 4Д', '70000001028948209'),
            ('tole-bi-229-3', 'улица Толе би, 229/3', '70000001047782771'),
        ],
        'menu_source_url': 'https://takeaway-web.choco.kz/filials/6219',
        'branch_hours': {
            'abay-27': ('11:00', '23:45'),
        },
        'delivery_branches': {
            'abay-27': True,
        },
        'dishes': [
            ('Комбо', 'Комбо чизбургер курица', '2800',
             'Бургер с куриной котлетой с сыром, картофель фри, напиток и соус на выбор.'),
            ('Комбо', 'Комбо чизбургер говядина', '3200',
             'Бургер с говяжьей котлетой с сыром, картофель фри, напиток и соус на выбор.'),
            ('Комбо', 'Комбо чизбургер курица х2', '3200',
             'Бургер с двойной куриной котлетой с сыром, картофель фри, напиток и соус на выбор.'),
            ('Комбо', 'Комбо чизбургер говядина х2', '3800',
             'Бургер с двойной говяжьей котлетой с сыром, картофель фри, напиток и соус на выбор.'),
            ('Комбо', 'Комбо чизбургер микс x2', '3550',
             'Бургер с говяжьей и куриной котлетами с сыром, картофель фри, напиток и соус на выбор.'),
            ('Бургеры', 'Бургер говядина', '1650', 'Говяжий бургер с одной котлетой.'),
            ('Бургеры', 'Бургер курица', '1500', 'Куриный бургер с одной котлетой.'),
            ('Бургеры', 'Чизбургер говядина', '1900', 'Говяжий бургер с одной котлетой и сыром.'),
            ('Бургеры', 'Чизбургер курица', '1700', 'Куриный бургер с котлетой и сыром.'),
            ('Гарниры', 'Картофель фри', '750', ''),
        ],
    },
    {
        'key': 'okadzaki',
        'name': 'Okadzaki',
        'cuisine': 'Паназиатская кухня',
        'branches': [
            ('tole-bi-274a', 'улица Толе би, 274А', '70000001110912545'),
            ('abaya-160-5', 'проспект Абая, 160/5', '70000001094788756'),
            ('rozybakiev-336-15', 'улица Розыбакиева, 336, блок 15', '70000001088050245'),
        ],
        'menu_source_url': 'https://eda.yandex.kz/r/okadzaki_1671017717',
        'dishes': [
            ('Сеты', 'Сет Бонапарт (80 шт и Пепперони и Маргарита и Кола 2 л)', '24780'),
            ('Сеты', 'Сет Венеция (64 шт и Пепперони и Кола)', '18960'),
            ('Комбо', 'Комбо №1', '5250'),
            ('Комбо', 'Комбо №2', '7980'),
        ],
    },
    {
        'key': 'samurai',
        'name': 'Samurai',
        'cuisine': 'Суши и японская кухня',
        'branches': [
            ('oraz-zhandosov-57', 'улица Ораза Жандосова, 57', '70000001027663370'),
            ('dostyk-91-1', 'проспект Достык, 91/1', '70000001019547543'),
            ('sholokhov-13', 'улица Шолохова, 13', '70000001024009276'),
        ],
        'menu_source_url': '',
        'dishes': [],
    },
    {
        'key': 'kausar',
        'name': 'Kausar',
        'cuisine': 'Казахская кухня',
        'branches': [
            ('zhambyl-77', 'улица Жамбыла, 77', '70000001102966995'),
            ('samal-1-2b', 'Самал-1, 2Б', '70000001086700592'),
            ('microdistrict-5-12a', '5-й микрорайон, 12А', '70000001099411797'),
        ],
        'menu_source_url': '',
        'dishes': [],
    },
    {
        'key': 'salam-bro',
        'name': 'Salam Bro',
        'cuisine': 'Фастфуд и донер',
        'branches': [
            ('microdistrict-8-1a', '8-й микрорайон, 1А', '70000001044724676'),
            ('samal-3-4d-1', 'Самал-3, 4Д/1', '70000001043560435'),
            ('zhibek-zholy-106', 'улица Жибек Жолы, 106', '70000001044217224'),
        ],
        'menu_source_url': '',
        'dishes': [],
    },
    {
        'key': 'wendys',
        'name': "Wendy's",
        'cuisine': 'Бургеры',
        'branches': [
            ('timiryazev-42-3', 'улица Тимирязева, 42/3', '70000001080816628'),
            ('rozybakiev-336-2', 'улица Розыбакиева, 336, блок 2', '70000001116196262'),
            ('satpaeva-90-21', 'проспект Сатпаева, 90/21', '70000001111493420'),
        ],
        'menu_source_url': '',
        'dishes': [],
    },
]


class Command(BaseCommand):
    help = 'Create or refresh the verified Almaty restaurant catalog.'

    def add_arguments(self, parser):
        parser.add_argument('--allow-production', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG and not options['allow_production']:
            raise CommandError(
                'Catalog seeding is disabled in production. '
                'Pass --allow-production only after reviewing the curated data.'
            )

        for restaurant_data in CATALOG:
            restaurant_key = f"almaty-{restaurant_data['key']}"
            first_branch = restaurant_data['branches'][0]
            source_url = f'https://2gis.kz/almaty/firm/{first_branch[2]}'
            defaults = {
                'name': restaurant_data['name'],
                'cuisine': restaurant_data['cuisine'],
                'address': first_branch[1],
                'description': '',
                'phone': '',
                'image_url': '',
                'source_url': source_url,
                'menu_source_url': restaurant_data['menu_source_url'],
                'opening_time': None,
                'closing_time': None,
                'working_days': [],
                'is_active': True,
            }
            restaurant = Restaurant.objects.filter(catalog_key=restaurant_key).first()
            if restaurant is None:
                restaurant = Restaurant.objects.filter(name=restaurant_data['name']).first()
                if restaurant is None:
                    restaurant = Restaurant.objects.create(catalog_key=restaurant_key, **defaults)
                else:
                    restaurant.catalog_key = restaurant_key
                    for field, value in defaults.items():
                        setattr(restaurant, field, value)
                    restaurant.save()
            else:
                for field, value in defaults.items():
                    setattr(restaurant, field, value)
                restaurant.save()

            for branch_key, address, source_id in restaurant_data['branches']:
                hours = restaurant_data.get('branch_hours', {}).get(branch_key)
                branch_defaults = {
                    'restaurant': restaurant,
                    'address': address,
                    'phone': '',
                    'opening_time': hours[0] if hours else None,
                    'closing_time': hours[1] if hours else None,
                    'working_days': [],
                    'is_active': True,
                    'delivery_available': restaurant_data.get('delivery_branches', {}).get(branch_key),
                    'delivery_info': '',
                    'source_url': f'https://2gis.kz/almaty/firm/{source_id}',
                }
                branch_catalog_key = f'{restaurant_key}-{branch_key}'
                branch = RestaurantBranch.objects.filter(catalog_key=branch_catalog_key).first()
                if branch is None:
                    branch = RestaurantBranch.objects.filter(
                        restaurant=restaurant,
                        address=address,
                    ).first()
                if branch is None:
                    RestaurantBranch.objects.create(catalog_key=branch_catalog_key, **branch_defaults)
                else:
                    branch.catalog_key = branch_catalog_key
                    for field, value in branch_defaults.items():
                        setattr(branch, field, value)
                    branch.save()

            for index, dish in enumerate(restaurant_data['dishes'], 1):
                category, name, price = dish[:3]
                description = dish[3] if len(dish) > 3 else ''
                item_key = f'{restaurant_key}-dish-{index}'
                item_defaults = {
                    'restaurant': restaurant,
                    'name': name,
                    'description': description,
                    'category': category,
                    'price': Decimal(price),
                    'image_url': '',
                    'source_url': restaurant_data['menu_source_url'],
                    'is_active': True,
                }
                item = MenuItem.objects.filter(catalog_key=item_key).first()
                if item is None:
                    item = MenuItem.objects.filter(restaurant=restaurant, name=name).first()
                if item is None:
                    MenuItem.objects.create(catalog_key=item_key, **item_defaults)
                else:
                    item.catalog_key = item_key
                    for field, value in item_defaults.items():
                        setattr(item, field, value)
                    item.save()

        self.stdout.write(self.style.SUCCESS('Verified restaurant catalog is ready.'))
