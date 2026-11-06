from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import Payment
from .serializers import PaymentSerializer, RefundSerializer


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
def confirm_cash_payment(request, payment_id):
    user = request.user
    if user.role not in ['admin', 'manager', 'delivery']:
        raise PermissionDenied('Permission denied.')

    with transaction.atomic():
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
        payment.status = 'refunded'
        payment.refund_reason = serializer.validated_data['reason']
        payment.refunded_at = timezone.now()
        payment.save(update_fields=['status', 'refund_reason', 'refunded_at', 'updated_at'])

    return Response(PaymentSerializer(payment).data)
