"""Authoritative catalog tool results. Prices are never authored by the LLM."""
import re
from decimal import Decimal

from .project_context import catalog_context, matching_restaurants

FOODS = r'чизбургер|cheeseburger|бургер|burger|донер|doner|шаурм\w*|shawarma|пицц\w*|pizza|суши|sushi|ролл\w*|roll|фри|fries|комбо|combo|суп\w*|soup|рамен|ramen|салат\w*|salad|паста|pasta|стейк|steak|тако|taco'
MODIFIERS = r'говя\w*|beef|сиыр|куриц\w*|курин\w*|chicken|тауық'
CATALOG_INTENT = r'цен[а-я]*|сто[ия]т|стоимость|сколько|поч[её]м|меню|price|cost|how much|menu|баға|қанша|м[әе]зір'


def catalog_answer(language, conversation):
    questions = [row['body'] for row in conversation if row['sender'] == 'customer'][-3:]
    if not questions:
        return None
    text = questions[-1]
    previous = questions[-2] if len(questions) > 1 else ''
    intent = bool(re.search(CATALOG_INTENT, text, re.I))
    food = bool(re.search(FOODS, text, re.I))
    named = bool(matching_restaurants(text))
    previous_catalog = bool(re.search(CATALOG_INTENT, previous, re.I))
    followup = previous_catalog and (named or bool(re.search(FOODS + '|' + MODIFIERS, text, re.I)))
    # A general question about delivery fees, account prices or promo minimums is not a dish-price lookup.
    if not ((intent and (food or named or re.search(r'меню|menu|м[әе]зір', text, re.I))) or (food and named) or followup
            or (intent and previous_catalog and len(text.split()) <= 7)):
        return None
    search = text
    if not food and previous_catalog:
        search += ' ' + ' '.join(re.findall(FOODS, previous, re.I))
    if not re.search(MODIFIERS, text, re.I) and re.search(r'его|этот|она|он\b|it\b|that|оның|осы', text, re.I):
        search += ' ' + ' '.join(re.findall(MODIFIERS, previous, re.I))
    catalog = catalog_context(search, questions[:-1])
    labels = {
        'ru': {
            'choose': 'Уточните название ресторана из каталога, чтобы я показал его цены.',
            'unresolved': 'Не удалось однозначно определить ресторан. Уточните название из каталога.',
            'no_menu': 'Для этого ресторана меню ещё не загружено. Подтверждённых цен в JetFood нет.',
            'no_dish': 'В загруженном меню этого ресторана блюдо по вашему запросу не найдено. Цену для него назвать не могу. Уточните название блюда или попросите всё меню.',
            'unavailable': ' — недоступно для заказа',
            'more': 'Показано {shown} из {total} позиций. Уточните блюдо или категорию.',
            'source': 'Цены из текущего каталога JetFood, за одну позицию; скидки и доставка считаются отдельно.',
        },
        'en': {
            'choose': 'Please specify the restaurant from the catalog so I can show its prices.',
            'unresolved': 'I could not identify the restaurant reliably. Please give its catalog name.',
            'no_menu': 'This restaurant menu has not been loaded. JetFood has no verified prices for it.',
            'no_dish': 'No dish matching your request was found in this restaurant menu. I cannot quote a price for it. Clarify the dish name or ask for the full menu.',
            'unavailable': ' — unavailable to order',
            'more': 'Showing {shown} of {total} positions. Specify a dish or category.',
            'source': 'Current JetFood catalog prices per position; discounts and delivery are calculated separately.',
        },
        'kk': {
            'choose': 'Бағасын көрсету үшін каталогтағы мейрамхана атауын нақтылаңыз.',
            'unresolved': 'Мейрамхананы сенімді анықтау мүмкін болмады. Каталогтағы атауын нақтылаңыз.',
            'no_menu': 'Бұл мейрамхананың мәзірі әлі жүктелмеген. JetFood-та расталған бағалар жоқ.',
            'no_dish': 'Бұл мейрамхананың жүктелген мәзірінен сұраған тағам табылмады. Оның бағасын айта алмаймын. Тағам атауын нақтылаңыз немесе толық мәзірді сұраңыз.',
            'unavailable': ' — тапсырыс беруге қолжетімсіз',
            'more': '{total} позицияның {shown} көрсетілді. Тағамды немесе санатты нақтылаңыз.',
            'source': 'JetFood каталогындағы бір позицияның ағымдағы бағасы; жеңілдік пен жеткізу бөлек есептеледі.',
        },
    }[language]
    if catalog['restaurant_unresolved']:
        return labels['unresolved']
    restaurants = catalog['selected_restaurants']
    if not restaurants:
        return labels['choose']
    heading = ', '.join(row['name'] for row in restaurants) + ':'
    if not catalog['dishes']:
        return heading + '\n' + labels['no_menu' if not any(r['menu_loaded'] for r in restaurants) else 'no_dish']
    rows = []
    for dish in catalog['dishes']:
        name = dish['name']
        if len(restaurants) > 1:
            name = dish['restaurant__name'] + ' / ' + name
        amount = format(Decimal(dish['price']), '.2f')
        rows.append(f"• {name} [{dish['category']}] — {amount} ₸" + ('' if dish['is_active'] else labels['unavailable']))
    if catalog['truncated']:
        rows.append(labels['more'].format(shown=len(rows), total=catalog['matching_dish_count']))
    return heading + '\n' + '\n'.join(rows) + '\n\n' + labels['source']
