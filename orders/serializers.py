from rest_framework import serializers
from django.db.models import Q
from .models import DeliveryRoute, MenuItem, Order, OrderItem
from django.conf import settings


class MenuItemSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'description', 'category', 'price', 'image_url',
            'rating', 'restaurant', 'restaurant_name', 'is_active',
        ]
        read_only_fields = ['id', 'rating', 'restaurant_name']


class OrderItemSerializer(serializers.ModelSerializer):
    quantity = serializers.IntegerField(min_value=1)
    menu_item_id = serializers.IntegerField(read_only=True, allow_null=True)
    item_id = serializers.PrimaryKeyRelatedField(
        source='menu_item',
        queryset=MenuItem.objects.filter(is_active=True, restaurant__is_active=True),
        write_only=True,
    )
    item_name = serializers.CharField(read_only=True)
    price_per_item = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'item_id', 'menu_item_id', 'item_name', 'quantity',
            'price_per_item', 'subtotal',
        ]
        read_only_fields = ['id', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    payment_method = serializers.ChoiceField(
        choices=[('online', 'Online simulation'), ('cash', 'Cash on delivery')],
        required=False,
        default='cash',
        write_only=True,
    )
    customer_name = serializers.CharField(source='customer.username', read_only=True)
    delivery_person_name = serializers.CharField(source='delivery_person.username', read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'customer', 'customer_name', 'delivery_person',
                  'delivery_person_name', 'status', 'priority', 'total_amount',
                  'delivery_address', 'delivery_notes', 'estimated_delivery_time',
                  'actual_delivery_time', 'delivery_confirmed_at', 'created_at',
                  'updated_at', 'items',
                  'payment_method']
        read_only_fields = [
            'id', 'order_number', 'customer', 'customer_name',
            'delivery_person', 'delivery_person_name', 'status', 'priority',
            'total_amount', 'created_at', 'updated_at',
        ]
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        validated_data.pop('payment_method', 'cash')
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            menu_item = item_data.pop('menu_item')
            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                item_name=menu_item.name,
                price_per_item=menu_item.price,
                **item_data,
            )
        return order


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)


class OrderModificationItemSerializer(serializers.Serializer):
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=MenuItem.objects.filter(is_active=True, restaurant__is_active=True)
    )
    quantity = serializers.IntegerField(min_value=1)


class OrderModificationSerializer(serializers.Serializer):
    delivery_address = serializers.CharField(required=False, allow_blank=False)
    delivery_notes = serializers.CharField(required=False, allow_blank=True)
    items = OrderModificationItemSerializer(many=True, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError('Provide an address, notes, or updated items.')
        if 'items' in attrs and not attrs['items']:
            raise serializers.ValidationError({'items': 'An order must contain at least one dish.'})
        return attrs


class DeliveryRouteSerializer(serializers.ModelSerializer):
    destination_address = serializers.CharField(source='order.delivery_address', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True)
    directions_url = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryRoute
        fields = [
            'id', 'order', 'origin_address', 'destination_address', 'notes',
            'directions_url', 'updated_by', 'updated_by_name', 'updated_at',
        ]
        read_only_fields = ['id', 'order', 'destination_address', 'directions_url',
                            'updated_by', 'updated_by_name', 'updated_at']

    def get_directions_url(self, route):
        from urllib.parse import urlencode

        query = urlencode({
            'api': 1,
            'origin': route.origin_address,
            'destination': route.order.delivery_address,
        })
        return f'https://www.google.com/maps/dir/?{query}'


class DeliveryRouteInputSerializer(serializers.Serializer):
    origin_address = serializers.CharField(max_length=500, trim_whitespace=True)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)
