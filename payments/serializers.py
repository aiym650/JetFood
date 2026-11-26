import re

from django.utils import timezone
from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    customer = serializers.IntegerField(source='order.customer_id', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    customer_name = serializers.CharField(source='order.customer.username', read_only=True)
    order_status = serializers.CharField(source='order.status', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'provider', 'is_test', 'refunded_amount', 'order', 'order_number', 'order_status', 'customer', 'customer_name',
            'method', 'status', 'amount', 'transaction_id', 'card_brand',
            'card_last4', 'failure_reason', 'refund_reason', 'created_at',
            'paid_at', 'refunded_at',
        ]
        read_only_fields = fields


class CardPaymentSerializer(serializers.Serializer):
    card_number = serializers.CharField(max_length=25, write_only=True)
    expiry = serializers.CharField(max_length=5, write_only=True)
    cvv = serializers.CharField(max_length=3, write_only=True)
    cardholder_name = serializers.CharField(max_length=120, trim_whitespace=True, write_only=True)

    def validate_card_number(self, value):
        card_number = value.replace(' ', '')
        if not card_number.isdigit() or len(card_number) != 16:
            raise serializers.ValidationError('Enter a 16-digit card number.')
        return card_number

    def validate_expiry(self, value):
        if not re.fullmatch(r'(0[1-9]|1[0-2])/[0-9]{2}', value):
            raise serializers.ValidationError('Enter expiry as MM/YY.')

        month, short_year = map(int, value.split('/'))
        expiry_year = 2000 + short_year
        current_date = timezone.localdate()
        if (expiry_year, month) < (current_date.year, current_date.month):
            raise serializers.ValidationError('Card expiry must be in the future.')
        return value

    def validate_cvv(self, value):
        if not re.fullmatch(r'[0-9]{3}', value):
            raise serializers.ValidationError('Enter a 3 digit CVV.')
        return value

    def validate_cardholder_name(self, value):
        if not re.fullmatch(r'[A-Z]+(?:[ -][A-Z]+)*', value):
            raise serializers.ValidationError('Enter the cardholder name in uppercase Latin letters.')
        return value


class RefundSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, trim_whitespace=True)
