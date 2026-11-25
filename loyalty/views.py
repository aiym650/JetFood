from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from .models import LoyaltyOrder, LoyaltyPolicy, Wallet, SecondOrderReward
from .services import balances, completed_orders, level_summary
from .amounts import display


def account_data(user, before=None):
    policy = LoyaltyPolicy.current()
    wallet = Wallet.objects.filter(user=user).first()
    available, reserved, debt = balances(wallet)
    entries = wallet.entries.select_related('order').all() if wallet else []
    earned = redeemed = 0
    if wallet:
        for entry in entries:
            credit = entry.available_delta+entry.reserved_delta-entry.debt_delta
            if entry.kind == 'earn' or (entry.kind == 'adjustment' and entry.order_id):
                earned += credit
            if entry.kind == 'spend':
                redeemed -= credit
            elif entry.kind == 'refund':
                redeemed -= credit
        if before:
            entries = entries.filter(id__lt=before)
    page = list(entries[:51])
    has_more = len(page) > 50
    page = page[:50]
    history = []
    for entry in page:
        credit = entry.available_delta+entry.reserved_delta-entry.debt_delta
        history.append({'id': entry.pk, 'order_id': entry.order_id, 'kind': entry.kind, 'category': entry.category,
            'order_number': entry.order.order_number if entry.order_id else None,
            'amount_minor': -entry.reserved_delta if entry.kind in ['reserve', 'release'] else credit,
            'available_delta': display(entry.available_delta), 'reserved_delta': display(entry.reserved_delta),
            'debt_delta': display(entry.debt_delta), 'reason': entry.reason, 'created_at': entry.created_at})
    reward = SecondOrderReward.objects.filter(user=user).first()
    now = timezone.now()
    status = reward.status if reward else 'waiting'
    deadline = reward.deadline if reward else None
    first_order_id = reward.first_order_id if reward else None
    second_order_id = reward.second_order_id if reward else None
    if reward is None:
        from datetime import timedelta
        historical = list(completed_orders(user.pk)[:2])
        if historical:
            first_order_id = historical[0].order_id
            deadline = historical[0].completed_at + timedelta(days=policy.second_order_days)
            status = 'eligible' if now <= deadline else 'expired'
            if len(historical) > 1:
                second_order_id = historical[1].order_id
                status = 'not_eligible' if historical[1].completed_at < policy.jetpoints_started_at else 'expired'
    if status == 'eligible' and deadline and now > deadline:
        status = 'expired'
    remaining = max(0, int((deadline-now).total_seconds())) if deadline else 0
    reward_amount = reward.amount if reward else policy.second_order_bonus
    return {
        'name': 'JetPoints', 'minor_units_per_point': 100, 'kzt_per_point': 1,
        'available': display(available), 'reserved': display(reserved), 'debt': display(debt),
        'balance_minor': available, 'reserved_minor': reserved, 'debt_minor': debt,
        'total_earned_minor': max(0, earned), 'total_redeemed_minor': max(0, redeemed),
        'level': level_summary(user.pk),
        'second_order': {'status': status, 'reward_minor': reward_amount, 'deadline': deadline,
            'seconds_remaining': remaining, 'first_order_id': first_order_id,
            'second_order_id': second_order_id, 'awarded_minor': reward.awarded if reward else 0},
        'policy': {key: str(getattr(policy, key)) for key in ['base_percent', 'promotional_percent', 'spend_percent', 'silver_percent', 'gold_percent', 'silver_orders', 'gold_orders', 'second_order_days']},
        'entries': history, 'has_more': has_more, 'next_before': page[-1].pk if page and has_more else None,
        'completed_rewards': [{'order_id': row.order_id, 'order_number': row.order.order_number, 'earned_minor': row.percentage_reward+row.milestone_reward} for row in LoyaltyOrder.objects.filter(order__customer=user, order__status='delivered', percentage_reward__gt=0).select_related('order').order_by('-completed_at')[:10]],
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def account(request):
    if request.user.role != 'customer':
        raise PermissionDenied('JetPoints accounts are available to customers only.')
    before = request.query_params.get('before')
    if before:
        try:
            before = int(before)
            if before < 1:
                raise ValueError
        except ValueError:
            raise ValidationError({'before': 'Use a positive history cursor.'})
    return Response(account_data(request.user, before))
