from rest_framework import serializers
from django.contrib.auth import get_user_model
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
        queryset=MenuItem.objects.filter(is_active=True).filter(
            Q(restaurant__isnull=True) | Q(restaurant__is_active=True)
        ),
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
                  'delivery_started_at', 'estimated_arrival_time', 'actual_delivery_time',
                  'delivery_confirmed_at', 'created_at',
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


class CourierAssignmentSerializer(serializers.Serializer):
    delivery_person_id = serializers.PrimaryKeyRelatedField(
        source='delivery_person',
        queryset=get_user_model().objects.filter(role='delivery', is_active=True),
    )


class OrderModificationItemSerializer(serializers.Serializer):
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=MenuItem.objects.filter(is_active=True).filter(
            Q(restaurant__isnull=True) | Q(restaurant__is_active=True)
        )
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
    origin_latitude = serializers.FloatField(read_only=True, allow_null=True)
    origin_longitude = serializers.FloatField(read_only=True, allow_null=True)
    destination_latitude = serializers.FloatField(read_only=True, allow_null=True)
    destination_longitude = serializers.FloatField(read_only=True, allow_null=True)

    class Meta:
        model = DeliveryRoute
        fields = [
            'id', 'order', 'origin_address', 'destination_address', 'notes',
            'origin_latitude', 'origin_longitude',
            'destination_latitude', 'destination_longitude',
            'route_distance_meters', 'estimated_duration_seconds',
            'directions_url', 'updated_by', 'updated_by_name', 'updated_at',
        ]
        read_only_fields = ['id', 'order', 'destination_address', 'directions_url',
                            'updated_by', 'updated_by_name', 'updated_at']
        read_only_fields += ['route_distance_meters', 'estimated_duration_seconds']

    def get_directions_url(self, route):
        if all([
            route.origin_latitude is not None,
            route.origin_longitude is not None,
            route.destination_latitude is not None,
            route.destination_longitude is not None,
        ]):
            return (
                'https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route='
                f'{route.origin_latitude},{route.origin_longitude};'
                f'{route.destination_latitude},{route.destination_longitude}'
            )
        return ''


class DeliveryRouteInputSerializer(serializers.Serializer):
    origin_address = serializers.CharField(max_length=500, trim_whitespace=True)
    origin_latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=-90, max_value=90, required=False
    )
    origin_longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=-180, max_value=180, required=False
    )
    destination_latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=-90, max_value=90, required=False
    )
    destination_longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=-180, max_value=180, required=False
    )
    route_distance_meters = serializers.IntegerField(min_value=1, max_value=1_000_000, required=False)
    estimated_duration_seconds = serializers.IntegerField(min_value=1, max_value=86_400, required=False)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate(self, attrs):
        coordinate_fields = [
            'origin_latitude', 'origin_longitude',
            'destination_latitude', 'destination_longitude',
        ]
        supplied = [field in attrs for field in coordinate_fields]
        if any(supplied) and not all(supplied):
            raise serializers.ValidationError(
                'Provide all four coordinates to plan a map route.'
            )
        metric_fields = ['route_distance_meters', 'estimated_duration_seconds']
        supplied_metrics = [field in attrs for field in metric_fields]
        if any(supplied_metrics) and not all(supplied_metrics):
            raise serializers.ValidationError(
                'Provide both route distance and estimated duration.'
            )
        if any(supplied) and not all(supplied_metrics):
            raise serializers.ValidationError(
                'Recalculate the route distance and estimated duration after changing route points.'
            )
        return attrs
