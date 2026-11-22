from rest_framework import serializers

from orders.models import Order
from .models import SupportCase, SupportMessage


class SupportMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportMessage
        fields = ['id', 'sender', 'body', 'created_at']
        read_only_fields = fields


class SupportCaseSerializer(serializers.ModelSerializer):
    messages = SupportMessageSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.username', read_only=True)

    class Meta:
        model = SupportCase
        fields = [
            'id', 'customer', 'customer_name', 'order', 'order_number',
            'issue_description', 'status', 'resolution', 'messages',
            'language', 'operator_requested',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class SupportCaseCreateSerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=['ru', 'kk', 'en'], default='en')
    operator_requested = serializers.BooleanField(default=False)
    order_number = serializers.CharField(
        max_length=50,
        trim_whitespace=True,
        required=False,
        allow_blank=True,
        default='',
    )
    issue_description = serializers.CharField(max_length=4000, trim_whitespace=True, required=False, allow_blank=True, default='')

    def validate_order_number(self, value):
        if not value:
            self.order = None
            return ''
        order = Order.objects.filter(
            order_number__iexact=value,
            customer=self.context['request'].user,
        ).first()
        if order is None:
            raise serializers.ValidationError(
                'Enter an order number belonging to your account.'
            )
        self.order = order
        return order.order_number

    def create(self, validated_data):
        return SupportCase.objects.create(
            customer=self.context['request'].user,
            order=getattr(self, 'order', None),
            **validated_data,
        )


class SupportMessageInputSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=4000, trim_whitespace=True)
    request_id = serializers.CharField(max_length=100, required=False)
