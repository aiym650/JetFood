"""JetPoints: integer minor units, ledger authority and user-serialized updates."""
from datetime import timedelta
from zoneinfo import ZoneInfo
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from users.models import User
from .models import LedgerEntry, LoyaltyOrder, LoyaltyPolicy, SecondOrderReward, Wallet
from .amounts import allocate, basis_points, decimal_amount, display, rounded_ratio, to_minor


def balances(wallet):
    if wallet is None:
        return 0, 0, 0
    totals = wallet.entries.aggregate(a=Sum('available_delta'), r=Sum('reserved_delta'), d=Sum('debt_delta'))
    return totals['a'] or 0, totals['r'] or 0, totals['d'] or 0


def lock_wallet(user_id):
    # First transaction statement is a write, also serializing SQLite checkouts.
    User.objects.filter(pk=user_id).update(last_login=F('last_login'))
    wallet, _ = Wallet.objects.get_or_create(user_id=user_id)
    wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
    wallet.available, wallet.reserved, wallet.debt = balances(wallet)
    wallet.save(update_fields=['available', 'reserved', 'debt'])
    return wallet


@transaction.atomic
def journal(wallet, kind, reason, order=None, credit=0, reserve=0, event_key=None, category='legacy'):
    if type(credit) is not int or type(reserve) is not int:
        raise ValidationError('Ledger operations require integer minor units.')
    User.objects.filter(pk=wallet.user_id).update(last_login=F('last_login'))
    wallet.available, wallet.reserved, wallet.debt = balances(wallet)
    if event_key:
        previous = LedgerEntry.objects.filter(event_key=event_key).first()
        if previous:
            if previous.wallet_id != wallet.pk or previous.available_delta-previous.debt_delta != credit or previous.reserved_delta != reserve:
                raise ValidationError('Ledger event key conflicts with a different operation.')
            return previous
    before = wallet.available, wallet.reserved, wallet.debt
    if credit >= 0:
        repaid = min(credit, wallet.debt)
        wallet.debt -= repaid
        wallet.available += credit - repaid
    else:
        taken = min(wallet.available, -credit)
        wallet.available -= taken
        wallet.debt += -credit - taken
    wallet.reserved += reserve
    if wallet.reserved < 0:
        raise ValidationError('Invalid JetPoints reservation state.')
    entry = LedgerEntry.objects.create(wallet=wallet, order=order, kind=kind, reason=reason,
        available_delta=wallet.available-before[0], reserved_delta=wallet.reserved-before[1],
        debt_delta=wallet.debt-before[2], event_key=event_key or uuid4().hex, category=category)
    wallet.save(update_fields=['available', 'reserved', 'debt'])
    return entry


def completed_orders(user_id):
    # Any confirmed refund disqualifies the order for level/retention counting.
    return LoyaltyOrder.objects.filter(order__customer_id=user_id, order__status='delivered',
        order__payment__paid_at__isnull=False, order__payment__status__in=['paid', 'refund_requested'],
        completed_at__isnull=False, refunded_cash=0).select_related('order__payment').order_by('completed_at', 'order_id')


def monthly_count(user_id, now=None, through=None):
    local = (now or timezone.now()).astimezone(ZoneInfo(getattr(settings, 'JETPOINTS_TIME_ZONE', 'Asia/Qyzylorda')))
    start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = (start.replace(day=28)+timedelta(days=4)).replace(day=1)
    orders = completed_orders(user_id).filter(completed_at__gte=start, completed_at__lt=end)
    if through is not None:
        orders = orders.filter(Q(completed_at__lt=through.completed_at) | Q(completed_at=through.completed_at, order_id__lte=through.order_id))
    return orders.count()


def level_for_count(count, policy):
    if count >= policy.gold_orders:
        return 'gold', max(basis_points(policy.base_percent), basis_points(policy.silver_percent), basis_points(policy.gold_percent)), None
    if count >= policy.silver_orders:
        return 'silver', max(basis_points(policy.base_percent), basis_points(policy.silver_percent)), policy.gold_orders
    return 'bronze', basis_points(policy.base_percent), policy.silver_orders


def level_summary(user_id, now=None):
    policy = LoyaltyPolicy.current()
    count = monthly_count(user_id, now)
    code, rate, target = level_for_count(count, policy)
    return {'code': code, 'cashback_percent': display(rate), 'completed_orders': count,
        'next_level': 'silver' if code == 'bronze' else 'gold' if code == 'silver' else None,
        'target_orders': target, 'orders_remaining': max(0, target-count) if target else 0,
        'progress_percent': min(100, count*100//target) if target else 100,
        'month': (now or timezone.now()).astimezone(ZoneInfo(getattr(settings, 'JETPOINTS_TIME_ZONE', 'Asia/Qyzylorda'))).strftime('%Y-%m')}


def quote_bonus(user, items, totals, requested=0):
    if user.role != 'customer' and to_minor(requested):
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied('Only customers can redeem JetPoints.')
    policy = LoyaltyPolicy.current()
    wallet = Wallet.objects.filter(user=user).first()
    available = balances(wallet)[0]
    goods = to_minor(totals['items_amount']) - to_minor(totals['discount_amount'])
    limit = min(available, goods*basis_points(policy.spend_percent)//10000)
    requested = to_minor(requested)
    if requested < 0 or requested > limit:
        raise ValidationError({'cashback_amount': 'Requested JetPoints exceed the balance or merchandise spending limit.', 'cashback_max': display(limit)})
    weights = [to_minor(item['menu_item'].price)*item['quantity'] for item in items]
    discounts = allocate(to_minor(totals['discount_amount']), weights)
    discounted = [amount-discount for amount, discount in zip(weights, discounts)]
    bonuses = allocate(requested, discounted)
    _, projected_rate, _ = level_for_count(monthly_count(user.pk)+1, policy)
    if user.role != 'customer':
        projected_rate = 0
    lines = [{'goods': amount, 'bonus': bonus, 'rate_bps': projected_rate,
        'promotional_bps': basis_points(policy.promotional_percent) if user.role == 'customer' and item['menu_item'].cashback_promotional else 0}
        for item, amount, bonus in zip(items, discounted, bonuses)]
    forecast = sum(rounded_ratio((line['goods']-line['bonus'])*max(projected_rate, line['promotional_bps']), 10000) for line in lines)
    totals['total_amount'] = decimal_amount(to_minor(totals['total_amount'])-requested)
    return {'cashback_amount': display(requested), 'cashback_max': display(limit), 'cashback_balance': display(available),
        'cashback_forecast': display(forecast), 'cashback_spend_percent': str(policy.spend_percent),
        'jetpoints_balance_minor': available, 'jetpoints_max_minor': limit, 'jetpoints_redeemed_minor': requested,
        'jetpoints_forecast_minor': forecast, 'jetpoints_level': level_summary(user.pk)}, lines


def reserve_order(order, amount, lines):
    wallet = lock_wallet(order.customer_id)
    amount = to_minor(amount)
    if amount > wallet.available:
        raise ValidationError({'cashback_amount': 'Insufficient JetPoints balance.'})
    policy = LoyaltyPolicy.current()
    LoyaltyOrder.objects.create(order=order, program_version=2 if order.customer.role == 'customer' else 0, reserved=amount, lines=lines,
        delivery_cash=to_minor(order.delivery_fee)-to_minor(order.delivery_discount),
        minimum=to_minor(policy.milestone_minimum), every=policy.milestone_every, milestone=to_minor(policy.milestone_bonus))
    if amount:
        journal(wallet, 'reserve', 'JetPoints checkout reservation', order, credit=-amount, reserve=amount,
            event_key=f'reserve:{order.pk}', category='redemption')


@transaction.atomic
def synchronize(order):
    wallet = lock_wallet(order.customer_id)
    record = LoyaltyOrder.objects.select_for_update().filter(order=order).first()
    if not record:
        return
    order.refresh_from_db()
    payment = order.payment
    if record.state == 'reserved':
        if payment.paid_at:
            record.state = 'spent'
            if record.reserved:
                journal(wallet, 'spend', 'Payment confirmed: JetPoints spent', order, reserve=-record.reserved, category='redemption')
        elif payment.status in ['failed', 'cancelled', 'expired']:
            record.state = 'released'
            if record.reserved:
                journal(wallet, 'release', 'Payment ended without a charge', order, credit=record.reserved, reserve=-record.reserved, category='redemption')
        record.save(update_fields=['state'])
    recalculate_rewards(wallet)


def recalculate_rewards(wallet):
    policy = LoyaltyPolicy.current()
    eligible_legacy_count = 0
    records = list(LoyaltyOrder.objects.filter(order__customer_id=wallet.user_id).select_related('order__payment').order_by('order__created_at', 'order_id'))
    for record in records:
        order = record.order
        if not hasattr(order, 'payment'):
            continue
        if record.completed_at is None and order.status == 'delivered' and order.payment.paid_at:
            record.completed_at = max(order.actual_delivery_time or order.updated_at, order.payment.paid_at)
            record.save(update_fields=['completed_at'])
    for record in records:
        order = record.order
        if record.program_version == 0 or not hasattr(order, 'payment'):
            continue  # Historical delivered orders count toward levels, with no retroactive issuance.
        cash_weights = [line['goods']-line['bonus'] for line in record.lines]
        cash_goods = sum(cash_weights)
        refund_goods = allocate(min(record.refunded_cash, cash_goods+record.delivery_cash), [cash_goods, record.delivery_cash])[0]
        remaining = allocate(cash_goods-refund_goods, cash_weights)
        completed = bool(order.payment.paid_at) and order.status == 'delivered' and order.payment.status in ['paid', 'partially_refunded', 'refund_requested']
        completed = completed and (wallet.user.role == 'customer' or record.percentage_reward > 0 or record.milestone_reward > 0)
        if completed and record.program_version == 2 and record.cashback_bps is None:
            _, record.cashback_bps, _ = level_for_count(monthly_count(wallet.user_id, record.completed_at, through=record), policy)
        percentage = 0
        if completed:
            percentage = sum(rounded_ratio(part*(max(record.cashback_bps, line.get('promotional_bps', 0)) if record.program_version == 2 else line['rate_bps']), 10000)
                for line, part in zip(record.lines, remaining))
        milestone = 0
        if record.program_version == 1 and completed and sum(remaining) >= record.minimum:
            eligible_legacy_count += 1
            if eligible_legacy_count % record.every == 0:
                milestone = record.milestone
        difference = percentage+milestone-record.percentage_reward-record.milestone_reward
        if difference:
            journal(wallet, 'earn' if difference > 0 else 'adjustment', 'JetPoints completed-order cashback' if record.program_version == 2 else 'Legacy cashback recalculation', order, credit=difference, category='cashback')
        record.percentage_reward, record.milestone_reward = percentage, milestone
        record.save(update_fields=['percentage_reward', 'milestone_reward', 'cashback_bps'])
    refresh_second_order_reward(wallet, policy)


def refresh_second_order_reward(wallet, policy):
    if wallet.user.role != 'customer' and not SecondOrderReward.objects.filter(user_id=wallet.user_id, claimed_at__isnull=False).exists():
        return
    reward, _ = SecondOrderReward.objects.get_or_create(user_id=wallet.user_id, defaults={'amount': policy.second_order_bonus})
    completed = completed_orders(wallet.user_id)
    if reward.claimed_at:
        valid = completed.filter(order_id__in=[reward.first_order_id, reward.second_order_id]).count() == 2
        if not valid and reward.awarded:
            journal(wallet, 'adjustment', 'JetPoints second-order bonus reversed', reward.second_order, credit=-reward.awarded, category='second_order_reversal')
            reward.awarded = 0
            reward.status = 'reversed'
            reward.save(update_fields=['awarded', 'status'])
        return
    candidates = list(completed[:2])
    if not candidates:
        reward.first_order = reward.second_order = None
        reward.deadline = None
        reward.status = 'waiting'
    else:
        first = candidates[0]
        if reward.first_order_id != first.order_id or reward.deadline is None:
            reward.first_order_id = first.order_id
            reward.deadline = first.completed_at+timedelta(days=policy.second_order_days)
            reward.amount = policy.second_order_bonus
        reward.second_order_id = candidates[1].order_id if len(candidates) == 2 else None
        if len(candidates) == 2:
            second = candidates[1]
            if second.completed_at < policy.jetpoints_started_at:
                reward.status = 'not_eligible'
            elif second.completed_at <= reward.deadline:
                reward.awarded = reward.amount
                reward.claimed_at = timezone.now()
                reward.status = 'awarded'
                journal(wallet, 'earn', 'JetPoints second-order bonus', second.order, credit=reward.amount,
                    event_key=f'second-order:{wallet.user_id}', category='second_order')
            else:
                reward.status = 'expired'
        else:
            reward.status = 'eligible' if timezone.now() <= reward.deadline else 'expired'
    reward.save()


@transaction.atomic
def apply_refund(order, cumulative_cash, full=False):
    wallet = lock_wallet(order.customer_id)
    record = LoyaltyOrder.objects.select_for_update().filter(order=order).first()
    if not record:
        return
    total_cash = sum(line['goods']-line['bonus'] for line in record.lines)+record.delivery_cash
    cumulative_cash = to_minor(cumulative_cash)
    if cumulative_cash < record.refunded_cash or cumulative_cash > total_cash:
        raise ValidationError('Invalid cumulative refund.')
    cash_goods = total_cash-record.delivery_cash
    goods_refund = allocate(cumulative_cash, [cash_goods, record.delivery_cash])[0]
    target = record.reserved if full else (rounded_ratio(record.reserved*goods_refund, cash_goods) if cash_goods else 0)
    delta = max(0, target-record.returned_bonus)
    if delta and record.state == 'spent':
        journal(wallet, 'refund', 'Returned redeemed JetPoints', order, credit=delta, category='refund')
    record.returned_bonus = target
    record.refunded_cash = cumulative_cash
    record.save(update_fields=['returned_bonus', 'refunded_cash'])
    recalculate_rewards(wallet)
