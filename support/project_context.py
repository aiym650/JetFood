"""Read-only allowlist: no model-selected URLs, SQL, user IDs or state changes."""
import re
from django.conf import settings
from django.db.models import Q
from loyalty.models import LoyaltyPolicy, Wallet
from payments.freedompay import configured


def commerce_facts(case):
    from loyalty.views import account_data
    from users.models import User
    account = account_data(User.objects.get(pk=case.customer_id))
    programme = account['policy']
    return {
        'cashback': {
            'programme': 'JetPoints', 'one_bonus_kzt': '1.00', 'available': account['available'],
            'reserved': account['reserved'], 'debt': account['debt'], 'level': account['level'],
            'second_order': account['second_order'], **account['policy'],
            'rules': f"1 JetPoint = 1 KZT. Bronze {programme['base_percent']}%, Silver {programme['silver_percent']}% after {programme['silver_orders']} paid/delivered orders in the current Kazakhstan calendar month, Gold {programme['gold_percent']}% after {programme['gold_orders']}. Redeem up to {programme['spend_percent']}% of discounted merchandise; no delivery. Earn on money-paid merchandise after redemption, using the highest applicable tier/promotional rate. Second-order offer amount and deadline are in second_order; it is only claimable once. Refund/cancellation excludes an order from tier/retention counting; corresponding rewards are reversed. No expiry. Never claim payment is confirmed without backend evidence.",
        },
        'payments': {'provider': 'Freedom Pay Kazakhstan', 'configured': configured(),
            'test_mode': settings.FREEDOMPAY_TEST_MODE, 'card_entry': 'Only on provider hosted page',
            'confirmation': 'Verified backend provider status; redirect alone never confirms payment.'},
        'reviews': 'Only owner of delivered order; one review per order, four integer ratings 1..5, text 10..1000 characters. Owner can edit. Edited review hidden until moderation approves. Ordinary negative reviews allowed. Published ratings include approved reviews only.',
        'registration': 'Username and password required (minimum 8 characters); email and phone optional.',
        'promos': 'One code per order, uppercase and trim; preview does not consume. Consumption at successful order creation, retained on cancellation. All prices and limits checked by backend.',
        'navigation': {'checkout': '/dashboard', 'orders': '/orders', 'payment_history': '/payments', 'cashback_balance_history': '/profile'},
    }


def matching_menu(text):
    from orders.models import MenuItem
    words = re.findall(r'[\w-]{3,60}', text, flags=re.UNICODE)[:12]
    query = Q(pk__in=[])
    for word in words:
        query |= Q(name__icontains=word) | Q(restaurant__name__icontains=word) | Q(category__icontains=word)
    return list(MenuItem.objects.filter(query, restaurant__is_active=True).values('id', 'name', 'restaurant_id', 'restaurant__name', 'category', 'price', 'is_active')[:25])


def retrieve_faq(language, text):
    from .models import FAQ
    tokens = set(re.findall(r'\w{3,}', text.casefold()))
    entries = list(FAQ.objects.filter(is_active=True)[:100])
    # Small editable corpus: lexical retrieval avoids an embedding service and stale vector index.
    def score(entry):
        content = f'{getattr(entry, "question_"+language)} {getattr(entry, "answer_"+language)}'.casefold()
        return sum(token in content for token in tokens)
    return sorted(entries, key=score, reverse=True)[:8]
