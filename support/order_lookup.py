"""Shared read-only order resolver; ownership is enforced for every lookup."""
import re
from django.db.models import Q
from orders.models import Order


def resolve_order(case, conversation):
    texts = [row['body'] for row in conversation if row['sender'] == 'customer'][-3:]
    for text in reversed(texts):
        query = Q(pk__in=[])
        explicit = False
        discussing = bool(re.search(r'заказ|order|тапсырыс', text, re.I))
        for reference in re.findall(r'\b[A-Za-z0-9][A-Za-z0-9_-]{3,49}\b', text)[:30]:
            if ('-' in reference or '_' in reference) and ('ORD' in reference.upper() or discussing):
                query |= Q(order_number__iexact=reference)
                explicit = True
        ids = re.findall(r'(?:заказ(?:а|у|ом)?|order|тапсырыс(?:ым|тың|ы)?)\s*[№#]?\s*(\d{1,12})\b', text, re.I)
        if ids:
            query |= Q(pk__in=ids[:5])
            explicit = True
        if explicit:
            return Order.objects.filter(query, customer_id=case.customer_id).select_related('payment').first(), True
    linked = getattr(case, 'order', None)
    if linked:
        return (linked if linked.customer_id == case.customer_id else None), True
    latest = texts[-1] if texts else ''
    if re.search(r'последн\w*\s+заказ|(?:latest|last)\s+order|соңғы\s+тапсырыс', latest, re.I):
        return Order.objects.filter(customer_id=case.customer_id).select_related('payment').order_by('-created_at', '-id').first(), True
    return None, False
