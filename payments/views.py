from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from orders.models import Order

from .models import Payment
from .serializers import CardPaymentSerializer, PaymentSerializer, RefundSerializer
from .services import create_simulated_transaction_id, detect_card_brand


class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Payment.objects.select_related('order', 'order__customer', 'order__delivery_person')
        if user.role in ['admin', 'manager']:
            return queryset
        if user.role == 'delivery':
            return queryset.filter(order__delivery_person=user)
        return queryset.filter(order__customer=user)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def pay_order(request, order_id):
    from django.conf import settings
    if not settings.PAYMENTS_ALLOW_LEGACY_SIMULATION:
        return Response({"detail": "Card collection and local simulation are disabled. Use hosted checkout."}, status=410)
    if request.user.role != 'customer':
        raise PermissionDenied('Only the customer who owns the order can pay.')

    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update().filter(customer=request.user),
            pk=order_id,
        )
        payment = get_object_or_404(
            Payment.objects.select_for_update().filter(order=order),
        )

        if payment.status == 'paid':
            result = PaymentSerializer(payment).data
            result['message'] = 'Payment already completed.'
            return Response(result)
        if payment.method != 'online':
            return Response(
                {'detail': 'Only online orders can be paid by card.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if order.status != 'pending' or payment.status not in ['pending', 'failed']:
            return Response(
                {'detail': 'This order is no longer available for payment.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CardPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        card_number = serializer.validated_data['card_number']
        payment.card_brand = detect_card_brand(card_number)
        payment.card_last4 = card_number[-4:]

        if card_number in ['4000000000000002', '4000000000009995']:
            payment.status = 'failed'
            payment.paid_at = None
            payment.transaction_id = ''
            payment.failure_reason = (
                'Card declined'
                if card_number == '4000000000000002'
                else 'Insufficient funds'
            )
            result_message = payment.failure_reason
        else:
            payment.status = 'paid'
            payment.paid_at = timezone.now()
            payment.transaction_id = create_simulated_transaction_id()
            payment.failure_reason = ''
            order.status = 'confirmed'
            order.save(update_fields=['status', 'updated_at'])
            result_message = 'Payment approved.'

        payment.save(update_fields=[
            'status', 'paid_at', 'transaction_id', 'card_brand', 'card_last4',
            'failure_reason', 'updated_at',
        ])
        from loyalty.services import synchronize
        synchronize(order)
        result = PaymentSerializer(payment).data
        result['message'] = result_message

    return Response(result, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_receipt(request, payment_id):
    user = request.user
    if user.role in ['admin', 'manager']:
        queryset = Payment.objects.select_related('order', 'order__customer')
    elif user.role == 'customer':
        queryset = Payment.objects.select_related('order', 'order__customer').filter(
            order__customer=user
        )
    else:
        raise PermissionDenied('Only the customer or payment managers can view receipts.')

    payment = get_object_or_404(queryset, pk=payment_id)
    return Response(PaymentSerializer(payment).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def confirm_cash_payment(request, payment_id):
    user = request.user
    if user.role not in ['admin', 'manager', 'delivery']:
        raise PermissionDenied('Permission denied.')

    owned = get_object_or_404(Payment.objects.select_related('order'), pk=payment_id)
    from loyalty.services import lock_wallet
    with transaction.atomic():
        lock_wallet(owned.order.customer_id)
        payment = get_object_or_404(
            Payment.objects.select_for_update().select_related('order'),
            pk=payment_id,
        )
        if user.role == 'delivery':
            if payment.order.delivery_person_id != user.id:
                raise PermissionDenied('This payment is not assigned to you.')
            if payment.order.status != 'delivered':
                return Response(
                    {'detail': 'Cash can be confirmed only after delivery.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if payment.method != 'cash' or payment.status != 'pending':
            return Response(
                {'detail': 'Only pending cash payments can be confirmed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payment.mark_paid()

    return Response(PaymentSerializer(payment).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def refund_payment(request, payment_id):
    if request.user.role not in ['admin', 'manager']:
        raise PermissionDenied('Only admins and managers can issue refunds.')

    serializer = RefundSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    existing = get_object_or_404(Payment.objects.select_related('order'), pk=payment_id)
    if existing.provider == 'bonuses':
        from loyalty.services import lock_wallet, apply_refund
        with transaction.atomic():
            lock_wallet(existing.order.customer_id)
            payment = Payment.objects.select_for_update().get(pk=existing.pk)
            if payment.status == 'refunded':
                return Response(PaymentSerializer(payment).data)
            if payment.status not in ['paid', 'refund_requested']:
                return Response({'detail': 'Payment is not refundable.'}, status=409)
            payment.status = 'refunded'
            payment.refund_reason = serializer.validated_data['reason']
            payment.refunded_at = timezone.now()
            payment.save(update_fields=['status', 'refund_reason', 'refunded_at', 'updated_at'])
            apply_refund(payment.order, 0, full=True)
        return Response(PaymentSerializer(payment).data)
    if existing.provider == 'freedompay':
        from .hosted import hosted_refund
        return hosted_refund(request, existing)
    from django.conf import settings
    if existing.method == 'online' and not settings.PAYMENTS_ALLOW_LEGACY_SIMULATION:
        return Response({'detail': 'Legacy simulated payment: no real refund can be issued.'}, status=409)
    with transaction.atomic():
        payment = get_object_or_404(
            Payment.objects.select_for_update().select_related('order', 'order__customer'),
            pk=payment_id,
        )
        if payment.status not in ['paid', 'refund_requested']:
            return Response(
                {'detail': 'Only paid payments can be refunded.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payment.refunded_amount = payment.amount
        payment.status = 'refunded'
        payment.refund_reason = serializer.validated_data['reason']
        payment.refunded_at = timezone.now()
        payment.save(update_fields=['status', 'refunded_amount', 'refund_reason', 'refunded_at', 'updated_at'])
        from loyalty.services import apply_refund
        apply_refund(payment.order, payment.amount, full=True)

    return Response(PaymentSerializer(payment).data)
