from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    customer_name = serializers.CharField(source='order.customer.username', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'customer_name', 'method', 'status',
            'amount', 'transaction_id', 'refund_reason', 'created_at',
            'paid_at', 'refunded_at',
        ]
        read_only_fields = fields


class RefundSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, trim_whitespace=True)
