from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from .models import DeliveryRoute, MenuItem, Order, OrderItem, RefundRequest
from restaurants.models import MenuCategory
from django.conf import settings
from decimal import Decimal


class MenuItemSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))

    class Meta:
        model = MenuItem
        fields = [
            "id",
            "name",
            "description",
            "category", "menu_category",
            "price",
            "image_url",
            "catalog_key",
            "source_url",
            "rating",
            "restaurant",
            "restaurant_name",
            "is_active", "cashback_promotional",
        ]
        read_only_fields = ["id", "catalog_key", "source_url", "rating", "restaurant_name"]
        extra_kwargs = {'category': {'required': False}}

    def validate(self, attrs):
        restaurant = attrs.get('restaurant', getattr(self.instance, 'restaurant', None))
        category = attrs.get('menu_category', getattr(self.instance, 'menu_category', None))
        if not category and not attrs.get('category', getattr(self.instance, 'category', '')).strip():
            raise serializers.ValidationError({'category': 'Choose or enter a category.'})
        if category and category.restaurant_id != restaurant.pk:
            raise serializers.ValidationError({'menu_category': 'Category belongs to another restaurant.'})
        user = self.context['request'].user
        if 'cashback_promotional' in attrs and attrs['cashback_promotional'] != getattr(self.instance, 'cashback_promotional', False) and user.role != 'admin' and not user.is_superuser:
            raise PermissionDenied('Only administrators can select promotional cashback dishes.')
        if user.role not in ['admin', 'manager']:
            raise PermissionDenied('Only admins and restaurant owners can manage menus.')
        if user.role != 'admin' and restaurant.owner_id != user.pk:
            raise PermissionDenied('You can only manage your own restaurant.')
        return attrs

    def _category(self, data):
        category = data.get('menu_category')
        restaurant = data.get('restaurant', getattr(self.instance, 'restaurant', None))
        if 'category' in data and 'menu_category' not in data:
            category, _ = MenuCategory.objects.get_or_create(restaurant=restaurant, name=data['category'])
            data['menu_category'] = category
        if category:
            data['category'] = category.name
        return data

    def create(self, validated_data):
        return super().create(self._category(validated_data))

    def update(self, instance, validated_data):
        return super().update(instance, self._category(validated_data))


class OrderItemSerializer(serializers.ModelSerializer):
    quantity = serializers.IntegerField(min_value=1)
    menu_item_id = serializers.IntegerField(read_only=True, allow_null=True)
    item_id = serializers.PrimaryKeyRelatedField(
        source="menu_item",
        queryset=MenuItem.objects.filter(is_active=True, restaurant__is_active=True),
        write_only=True,
    )
    item_name = serializers.CharField(read_only=True)
    price_per_item = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "item_id",
            "menu_item_id",
            "item_name",
            "quantity",
            "price_per_item",
            "subtotal",
        ]
        read_only_fields = ["id", "subtotal"]


class OrderSerializer(serializers.ModelSerializer):
    cashback = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()

    def get_payment(self, obj):
        payment = getattr(obj, 'payment', None)
        return {'id': payment.id, 'method': payment.method, 'status': payment.status} if payment else None

    def get_cashback(self, obj):
        from loyalty.models import LoyaltyOrder
        record = LoyaltyOrder.objects.filter(order=obj).first()
        from loyalty.amounts import display
        return {'amount': display(record.reserved), 'state': record.state, 'earned': display(record.percentage_reward + record.milestone_reward), 'returned': display(record.returned_bonus), 'amount_minor': record.reserved, 'earned_minor': record.percentage_reward + record.milestone_reward} if record else None

    cashback_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False, default=Decimal("0"), write_only=True)
    promo_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    items = OrderItemSerializer(many=True)
    payment_method = serializers.ChoiceField(
        choices=[("online", "Online hosted payment"), ("cash", "Cash on delivery")],
        required=False,
        default="cash",
        write_only=True,
    )
    customer_name = serializers.CharField(source="customer.username", read_only=True)
    delivery_person_name = serializers.CharField(
        source="delivery_person.username", read_only=True
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "customer",
            "customer_name",
            "delivery_person",
            "delivery_person_name",
            "status",
            "priority",
            "total_amount",
            "items_amount", "discount_amount", "delivery_fee", "delivery_discount", "promo_code",
            "delivery_address",
            "delivery_notes",
            "estimated_delivery_time",
            "actual_delivery_time",
            "delivery_confirmed_at",
            "created_at",
            "updated_at",
            "items",
            "payment_method", "cashback_amount", "cashback", "payment",
        ]
        read_only_fields = [
            "id",
            "order_number",
            "customer",
            "customer_name",
            "delivery_person",
            "delivery_person_name",
            "status",
            "priority",
            "total_amount",
            "items_amount", "discount_amount", "delivery_fee", "delivery_discount",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        if self.instance and ('items' in attrs or 'promo_code' in attrs or 'cashback_amount' in attrs):
            raise serializers.ValidationError({'items': 'Use the order modification endpoint. Promo snapshots cannot be edited.'})
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        validated_data.pop("payment_method", "cash")
        validated_data.pop("cashback_amount", None)
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            menu_item = item_data.pop("menu_item")
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
            raise serializers.ValidationError(
                "Provide an address, notes, or updated items."
            )
        if "items" in attrs and not attrs["items"]:
            raise serializers.ValidationError(
                {"items": "An order must contain at least one dish."}
            )
        return attrs


class DeliveryRouteSerializer(serializers.ModelSerializer):
    destination_address = serializers.CharField(
        source="order.delivery_address", read_only=True
    )
    updated_by_name = serializers.CharField(
        source="updated_by.username", read_only=True
    )
    directions_url = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryRoute
        fields = [
            "id",
            "order",
            "origin_address",
            "destination_address",
            "notes",
            "directions_url",
            "updated_by",
            "updated_by_name",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "order",
            "destination_address",
            "directions_url",
            "updated_by",
            "updated_by_name",
            "updated_at",
        ]

    def get_directions_url(self, route):
        from urllib.parse import urlencode

        query = urlencode(
            {
                "api": 1,
                "origin": route.origin_address,
                "destination": route.order.delivery_address,
            }
        )
        return f"https://www.google.com/maps/dir/?{query}"


class DeliveryRouteInputSerializer(serializers.Serializer):
    origin_address = serializers.CharField(max_length=500, trim_whitespace=True)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    origin_latitude = serializers.FloatField(required=False, allow_null=True)
    origin_longitude = serializers.FloatField(required=False, allow_null=True)
    destination_latitude = serializers.FloatField(required=False, allow_null=True)
    destination_longitude = serializers.FloatField(required=False, allow_null=True)
    route_distance_meters = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    estimated_duration_seconds = serializers.IntegerField(required=False, allow_null=True, min_value=0)


class InstantOrderCancellationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, trim_whitespace=True)


class RefundRequestCreateSerializer(serializers.Serializer):
    request_type = serializers.ChoiceField(choices=["cancel", "refund"])
    reason_category = serializers.CharField(required=False, allow_blank=True, max_length=20, default="")
    reason_text = serializers.CharField(min_length=10, max_length=5000, trim_whitespace=True)

    def validate(self, attrs):
        request_type = attrs["request_type"]
        category = attrs["reason_category"]
        if request_type == "cancel" and category:
            raise serializers.ValidationError({
                "reason_category": "Cancellation requests do not use a refund category."
            })
        refund_categories = {value for value, _ in RefundRequest.REASON_CATEGORY_CHOICES}
        if request_type == "refund" and category not in refund_categories:
            raise serializers.ValidationError({
                "reason_category": "Choose a valid refund reason category."
            })
        return attrs


class RefundRequestDecisionSerializer(serializers.Serializer):
    refund_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
    )
    decision_note = serializers.CharField(
        max_length=1000,
        trim_whitespace=True,
        required=False,
        allow_blank=True,
        default="",
    )


class RefundRequestRejectionSerializer(serializers.Serializer):
    decision_note = serializers.CharField(
        min_length=1,
        max_length=1000,
        trim_whitespace=True,
    )


class RefundRequestSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    order_status = serializers.CharField(source="order.status", read_only=True)
    customer_name = serializers.CharField(source="order.customer.username", read_only=True)
    requested_by_name = serializers.CharField(source="requested_by.username", read_only=True)
    decided_by_name = serializers.CharField(source="decided_by.username", read_only=True, allow_null=True)
    amount_paid = serializers.SerializerMethodField()

    class Meta:
        model = RefundRequest
        fields = [
            "id", "order", "order_number", "order_status", "customer_name",
            "requested_by", "requested_by_name", "request_type", "reason_category",
            "reason_text", "status", "decided_by", "decided_by_name", "decided_at",
            "decision_note", "refund_amount", "amount_paid", "created_at",
        ]
        read_only_fields = fields

    def get_amount_paid(self, request):
        try:
            payment = request.order.payment
        except ObjectDoesNotExist:
            return Decimal("0.00")
        if payment.status not in {"paid", "refund_requested", "refunded"}:
            return Decimal("0.00")
        return payment.amount
