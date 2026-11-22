"""Server-only quotes. Preview never reserves or consumes a redemption."""
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .models import MenuItem, PromoCode, PromoRedemption


def money(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def fail(code):
    raise ValidationError({'promo_error': code})


def quote(user, items, code='', consume=False):
    if not items or sum(i['quantity'] for i in items) > 50:
        raise ValidationError({'items': 'Use 1 to 50 dishes.'})
    ids = [i['menu_item'].pk for i in items]
    query = MenuItem.objects.select_related('restaurant').filter(pk__in=ids)
    if consume:
        query = query.select_for_update()
    dishes = {dish.pk: dish for dish in query}
    restaurant_ids = set()
    amount = Decimal('0')
    for line in items:
        dish = dishes.get(line['menu_item'].pk)
        if not dish or not dish.is_active or not dish.restaurant.is_active:
            raise ValidationError({'items': 'A dish or restaurant is unavailable.'})
        line['menu_item'] = dish
        restaurant_ids.add(dish.restaurant_id)
        amount += dish.price * line['quantity']
    if len(restaurant_ids) != 1:
        raise ValidationError({'items': 'One restaurant per order is supported.'})
    fee = money(settings.ORDER_DELIVERY_FEE)
    discount = delivery_discount = Decimal('0.00')
    code = code.strip().upper()
    promo = None
    if code:
        promos = PromoCode.objects.all()
        if consume:
            promos = promos.select_for_update()
        promo = promos.filter(code=code).first()
        if not promo:
            fail('not_found')
        now = timezone.now()
        if not promo.is_active:
            fail('inactive')
        if promo.starts_at and now < promo.starts_at:
            fail('not_started')
        if promo.ends_at and now >= promo.ends_at:
            fail('expired')
        if promo.restaurant_id and promo.restaurant_id not in restaurant_ids:
            fail('restaurant')
        if amount < promo.minimum_amount:
            fail('minimum')
        if promo.usage_limit is not None and promo.used_count >= promo.usage_limit:
            fail('limit')
        if promo.per_user_limit is not None and PromoRedemption.objects.filter(promo=promo, user=user).count() >= promo.per_user_limit:
            fail('user_limit')
        if promo.kind == 'percent':
            discount = money(amount * promo.value / 100)
            if promo.maximum_discount is not None:
                discount = min(discount, promo.maximum_discount)
        elif promo.kind == 'fixed':
            discount = promo.value
        else:
            delivery_discount = fee
        discount = min(amount, discount)
        if consume:
            updated = PromoCode.objects.filter(pk=promo.pk).filter(Q(usage_limit__isnull=True) | Q(used_count__lt=F('usage_limit'))).update(used_count=F('used_count') + 1)
            if not updated:
                fail('limit')
    return {
        'items_amount': money(amount), 'discount_amount': money(discount),
        'delivery_fee': fee, 'delivery_discount': money(delivery_discount),
        'total_amount': money(amount - discount + fee - delivery_discount),
        'promo_code': code,
    }, promo
