from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError as DRFValidationError,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from math import asin, cos, radians, sin, sqrt
from .models import DeliveryRoute, MenuItem, Order, OrderItem, RefundRequest
from .serializers import (
    MenuItemSerializer,
    OrderSerializer,
    OrderItemSerializer,
    OrderStatusUpdateSerializer,
    OrderModificationSerializer,
    DeliveryRouteSerializer,
    DeliveryRouteInputSerializer,
    InstantOrderCancellationSerializer,
    RefundRequestCreateSerializer,
    RefundRequestDecisionSerializer,
    RefundRequestRejectionSerializer,
    RefundRequestSerializer,
)
from .refund_requests import cancel_customer_order, create_customer_refund_request, decide_refund_request
from .date_filters import filter_by_created_date
from users.constraints import (
    BusinessConstraints,
    validate_order_amount,
    validate_delivery_time,
    validate_user_pending_orders,
)
import random
import string


class OrderListCreateView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Order.objects.all()
        elif user.role == "manager":
            return Order.objects.all()
        elif user.role == "delivery":
            return Order.objects.filter(delivery_person=user)
        else:
            return Order.objects.filter(customer=user)

    def create(self, request, *args, **kwargs):
        import time
        from django.db import OperationalError
        for attempt in range(5):
            try:
                return self._create_once(request)
            except OperationalError as exc:
                if 'locked' not in str(exc).lower():
                    raise
                if attempt == 4:
                    return Response({'detail': 'Checkout is busy. Retry with the same Idempotency-Key.'}, status=503, headers={'Retry-After': '1'})
                time.sleep(0.05 * 2 ** attempt)

    def _create_once(self, request):
        import hashlib
        import json
        import uuid
        from django.db.models import F
        from users.models import User
        from .models import PromoRedemption
        from .promotions import quote
        from payments.services import create_order_payment
        key = request.headers.get('Idempotency-Key', '').strip()
        if len(key) > 100:
            raise DRFValidationError({'detail': 'Idempotency-Key is too long.'})
        if request.data.get('promo_code') and not key:
            raise DRFValidationError({'detail': 'Idempotency-Key is required for promotional checkout.'})
        fingerprint = hashlib.sha256(json.dumps(request.data, sort_keys=True).encode()).hexdigest()
        with transaction.atomic():
            # First transaction statement is a write: serializes the customer even on SQLite.
            User.objects.filter(pk=request.user.pk).update(last_login=F('last_login'))
            if key:
                previous = Order.objects.filter(customer=request.user, idempotency_key=key).first()
                if previous:
                    if previous.request_fingerprint != fingerprint:
                        return Response({'detail': 'Idempotency-Key was used for another request.'}, status=409)
                    return Response(OrderSerializer(previous).data)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            if data.get('cashback_amount', 0) > 0 and not key:
                raise DRFValidationError({'detail': 'Idempotency-Key is required when redeeming bonuses.'})
            totals, promo = quote(request.user, data['items'], data.get('promo_code', ''), consume=True)
            from loyalty.services import quote_bonus, reserve_order
            bonus_quote, bonus_lines = quote_bonus(request.user, data['items'], totals, data.get('cashback_amount', 0))
            try:
                validate_user_pending_orders(request.user)
                validate_order_amount(totals['items_amount'])
                if data.get('estimated_delivery_time'):
                    validate_delivery_time(data['estimated_delivery_time'])
            except DjangoValidationError as error:
                raise DRFValidationError(error.messages) from error
            order = serializer.save(customer=request.user, order_number='ORD-' + uuid.uuid4().hex[:16].upper(),
                status='pending', priority='normal', delivery_person=None,
                idempotency_key=key or None, request_fingerprint=fingerprint, **totals)
            if promo:
                PromoRedemption.objects.create(promo=promo, user=request.user, order=order)
            reserve_order(order, bonus_quote['cashback_amount'], bonus_lines)
            create_order_payment(order, data.get('payment_method', 'cash'))
        return Response(OrderSerializer(order).data, status=201)


class MenuItemListCreateView(generics.ListCreateAPIView):
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        queryset = MenuItem.objects.select_related("restaurant")
        if user.role not in ["admin", "manager"]:
            queryset = queryset.filter(is_active=True, restaurant__is_active=True)
        restaurant_id = self.request.query_params.get("restaurant")
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__iexact=category)
        return queryset

    def perform_create(self, serializer):
        if self.request.user.role not in ["admin", "manager"]:
            raise PermissionDenied("Only admins and managers can manage menu items")
        instance = getattr(serializer, 'instance', None)
        if instance and self.request.user.role != 'admin' and instance.restaurant.owner_id != self.request.user.pk:
            raise PermissionDenied('Only the restaurant owner can edit this menu.')
        serializer.save()


class MenuItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = MenuItem.objects.select_related("restaurant")
        if user.role not in ["admin", "manager"]:
            queryset = queryset.filter(is_active=True, restaurant__is_active=True)
        return queryset

    def perform_update(self, serializer):
        if self.request.user.role not in ["admin", "manager"]:
            raise PermissionDenied("Only admins and managers can manage menu items")
        instance = getattr(serializer, 'instance', None)
        if instance and self.request.user.role != 'admin' and instance.restaurant.owner_id != self.request.user.pk:
            raise PermissionDenied('Only the restaurant owner can edit this menu.')
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.role not in ["admin", "manager"]:
            raise PermissionDenied("Only admins and managers can manage menu items")
        if self.request.user.role != 'admin' and instance.restaurant.owner_id != self.request.user.pk:
            raise PermissionDenied('Only the restaurant owner can edit this menu.')
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Order.objects.all()
        elif user.role == "manager":
            return Order.objects.all()
        elif user.role == "delivery":
            return Order.objects.filter(delivery_person=user)
        else:
            return Order.objects.filter(customer=user)

    def perform_update(self, serializer):
        if self.request.user.role not in ["admin", "manager"]:
            raise PermissionDenied("Only admins and managers can edit orders")
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.role not in ["admin", "manager"]:
            raise PermissionDenied("Only admins and managers can delete orders")
        from django.db.models.deletion import ProtectedError
        from rest_framework.exceptions import APIException
        try:
            instance.delete()
        except ProtectedError as error:
            conflict = APIException('This order has permanent loyalty or payment history. Use the order status workflow instead.')
            conflict.status_code = 409
            raise conflict from error


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def update_order_status(request, order_id):
    """Update order status"""
    serializer = OrderStatusUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = request.user
    if user.role not in ["customer", "delivery", "admin", "manager"]:
        raise PermissionDenied("Permission denied")

    if user.role in ["admin", "manager"]:
        queryset = Order.objects.all()
    elif user.role == "delivery":
        queryset = Order.objects.filter(delivery_person=user)
    else:
        queryset = Order.objects.filter(customer=user)

    order = get_object_or_404(queryset, id=order_id)
    target_status = serializer.validated_data["status"]
    if user.role == "customer" and target_status == "cancelled":
        cancellation_serializer = InstantOrderCancellationSerializer(data=request.data)
        cancellation_serializer.is_valid(raise_exception=True)
        cancelled_order = cancel_customer_order(
            order_id,
            user,
            cancellation_serializer.validated_data["reason"],
        )
        return Response(OrderSerializer(cancelled_order).data)

    if target_status != "cancelled":
        from payments.models import Payment

        payment = Payment.objects.filter(order=order, method="online").first()
        if payment and payment.status != "paid":
            return Response(
                {"detail": "Online payment must succeed before the order can proceed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if user.role == "customer":
        if (
            order.status not in ["pending"]
            or target_status != "cancelled"
        ):
            return Response(
                {"error": "You can only cancel pending orders"},
                status=status.HTTP_403_FORBIDDEN,
            )
    elif user.role == "delivery":
        allowed_transition = (
            order.status == "ready_for_pickup"
            and serializer.validated_data["status"] == "delivering"
        ) or (
            order.status == "delivering"
            and serializer.validated_data["status"] == "delivered"
        )
        if not allowed_transition:
            return Response(
                {
                    "error": "Delivery persons must move orders from preparing to delivering, then delivered"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

    if target_status == "cancelled":
        from payments.models import PaymentAttempt
        if PaymentAttempt.objects.filter(payment__order=order, status__in=["unknown", "pending"]).exists():
            return Response({"detail": "Payment result is not final. Reconcile the payment before cancellation."}, status=409)
    order.status = target_status

    if order.status == "delivered":
        order.actual_delivery_time = timezone.now()
        from datetime import timedelta
        from reviews.models import ReviewReminder
        ReviewReminder.objects.get_or_create(
            order=order,
            defaults={"due_at": timezone.now() + timedelta(minutes=45)},
        )

    order.save()
    if order.status == "cancelled":
        from payments.models import Payment

        payment = Payment.objects.filter(order=order).first()
        if payment:
            if payment.status == "paid":
                payment.status = "refund_requested"
            elif payment.status == "pending":
                payment.status = "cancelled"
            payment.save(update_fields=["status", "updated_at"])
    from loyalty.services import synchronize
    synchronize(order)
    return Response({"message": f"Order status updated to {order.status}"})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def cancel_order(request, order_id):
    if request.user.role != "customer":
        raise PermissionDenied("Only customers can cancel their own orders.")
    serializer = InstantOrderCancellationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    order = cancel_customer_order(
        order_id,
        request.user,
        serializer.validated_data["reason"],
    )
    return Response(OrderSerializer(order).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_refund_request(request, order_id):
    if request.user.role != "customer":
        raise PermissionDenied("Only customers can create order requests.")
    serializer = RefundRequestCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    refund_request = create_customer_refund_request(
        order_id=order_id,
        customer=request.user,
        request_type=serializer.validated_data["request_type"],
        reason_category=serializer.validated_data["reason_category"],
        reason_text=serializer.validated_data["reason_text"],
    )
    return Response(
        RefundRequestSerializer(refund_request).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def refund_request_list(request):
    user = request.user
    queryset = RefundRequest.objects.select_related(
        "order",
        "order__customer",
        "order__payment",
        "requested_by",
        "decided_by",
    )
    if user.role == "customer":
        queryset = queryset.filter(requested_by=user)
    elif user.role not in ["admin", "manager"]:
        raise PermissionDenied("Only customers, managers, and admins can view requests.")

    order_id = request.query_params.get("order")
    if order_id:
        try:
            order_id = int(order_id)
        except ValueError as error:
            raise DRFValidationError({"order": "Enter a valid order ID."}) from error
        if order_id < 1:
            raise DRFValidationError({"order": "Enter a valid order ID."})
        queryset = queryset.filter(order_id=order_id)
    request_status = request.query_params.get("status")
    if request_status:
        if request_status not in {value for value, _ in RefundRequest.STATUS_CHOICES}:
            raise DRFValidationError({"status": "Choose a valid request status."})
        queryset = queryset.filter(status=request_status)
    return Response(RefundRequestSerializer(queryset, many=True).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def approve_refund_request(request, request_id):
    if request.user.role not in ["admin", "manager"]:
        raise PermissionDenied("Only managers and admins can decide requests.")
    serializer = RefundRequestDecisionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    refund_request = decide_refund_request(
        request_id=request_id,
        manager=request.user,
        decision="approve",
        decision_note=serializer.validated_data["decision_note"],
        refund_amount=serializer.validated_data.get("refund_amount"),
    )
    return Response(RefundRequestSerializer(refund_request).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def reject_refund_request(request, request_id):
    if request.user.role not in ["admin", "manager"]:
        raise PermissionDenied("Only managers and admins can decide requests.")
    serializer = RefundRequestRejectionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    refund_request = decide_refund_request(
        request_id=request_id,
        manager=request.user,
        decision="reject",
        decision_note=serializer.validated_data["decision_note"],
    )
    return Response(RefundRequestSerializer(refund_request).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def confirm_delivery(request, order_id):
    if request.user.role != "customer":
        raise PermissionDenied("Only the customer can confirm receipt.")
    order = get_object_or_404(Order.objects.filter(customer=request.user), id=order_id)
    if order.status != "delivered":
        return Response(
            {
                "detail": "The courier must mark the order delivered before receipt can be confirmed."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if order.delivery_confirmed_at:
        return Response(
            {"detail": "Delivery has already been confirmed."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    order.delivery_confirmed_at = timezone.now()
    order.save(update_fields=["delivery_confirmed_at", "updated_at"])
    return Response(
        {
            "message": "Delivery confirmed.",
            "delivery_confirmed_at": order.delivery_confirmed_at,
        }
    )


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def delivery_route(request, order_id):
    user = request.user
    if user.role in ["admin", "manager"]:
        order_queryset = Order.objects.all()
    elif user.role == "delivery":
        order_queryset = Order.objects.filter(delivery_person=user)
    else:
        order_queryset = Order.objects.filter(customer=user)
    order = get_object_or_404(order_queryset, id=order_id)

    if request.method == "GET":
        route = (
            DeliveryRoute.objects.filter(order=order)
            .select_related("updated_by", "order")
            .first()
        )
        if route is None:
            return Response(
                {"detail": "A delivery route has not been planned."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(DeliveryRouteSerializer(route).data)

    if user.role not in ["admin", "manager"] and not (
        user.role == "delivery" and order.delivery_person_id == user.id
    ):
        raise PermissionDenied(
            "Only the assigned courier, a manager, or an admin can manage the route."
        )

    serializer = DeliveryRouteInputSerializer(
        data=request.data, partial=request.method == "PATCH"
    )
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        route = DeliveryRoute.objects.select_for_update().filter(order=order).first()
        if route is None:
            if not serializer.validated_data.get("origin_address"):
                raise DRFValidationError(
                    {"origin_address": "This field is required to plan a route."}
                )
            route = DeliveryRoute.objects.create(
                order=order,
                origin_address=serializer.validated_data["origin_address"],
                notes=serializer.validated_data.get("notes", ""),
                origin_latitude=serializer.validated_data.get("origin_latitude"),
                origin_longitude=serializer.validated_data.get("origin_longitude"),
                destination_latitude=serializer.validated_data.get("destination_latitude"),
                destination_longitude=serializer.validated_data.get("destination_longitude"),
                route_distance_meters=serializer.validated_data.get("route_distance_meters"),
                estimated_duration_seconds=serializer.validated_data.get("estimated_duration_seconds"),
                updated_by=user,
            )
        else:
            for field in ["origin_address", "notes"]:
                if field in serializer.validated_data:
                    setattr(route, field, serializer.validated_data[field])
            for field in [
                "origin_latitude",
                "origin_longitude",
                "destination_latitude",
                "destination_longitude",
                "route_distance_meters",
                "estimated_duration_seconds",
            ]:
                if field in serializer.validated_data:
                    setattr(route, field, serializer.validated_data[field])
            if route.origin_latitude is not None and route.origin_longitude is not None and route.destination_latitude is not None and route.destination_longitude is not None:
                lat1, lon1 = radians(route.origin_latitude), radians(route.origin_longitude)
                lat2, lon2 = radians(route.destination_latitude), radians(route.destination_longitude)
                haversine = 2 * 6371000 * asin(sqrt(sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2))
                if not route.route_distance_meters:
                    route.route_distance_meters = round(haversine)
                if not route.estimated_duration_seconds:
                    route.estimated_duration_seconds = max(60, round(haversine / 8))
            route.updated_by = user
            route.save()

    return Response(DeliveryRouteSerializer(route).data, status=status.HTTP_200_OK)


@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated])
def modify_order(request, order_id):
    if request.user.role != "customer":
        raise PermissionDenied("Only customers can modify their orders.")

    serializer = OrderModificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    updates = serializer.validated_data
    modified_items = updates.get("items")
    total_amount = None

    if modified_items is not None:
        item_count = sum(item["quantity"] for item in modified_items)
        if item_count > BusinessConstraints.MAX_ITEMS_PER_ORDER:
            raise DRFValidationError(
                {
                    "items": f"An order cannot contain more than {BusinessConstraints.MAX_ITEMS_PER_ORDER} dishes."
                }
            )
        total_amount = sum(
            item["quantity"] * item["item_id"].price for item in modified_items
        )
        try:
            validate_order_amount(total_amount)
        except DjangoValidationError as error:
            raise DRFValidationError(error.messages) from error

    with transaction.atomic():
        from loyalty.services import lock_wallet
        lock_wallet(request.user.pk)
        order = get_object_or_404(
            Order.objects.select_for_update().filter(customer=request.user),
            id=order_id,
        )
        if order.status != "pending":
            return Response(
                {"detail": "Orders can only be modified before confirmation."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if modified_items is not None:
            from payments.models import Payment, PaymentAttempt
            from loyalty.models import LoyaltyOrder
            loyalty_record = LoyaltyOrder.objects.filter(order=order).first()
            if order.promo_code or (loyalty_record and loyalty_record.reserved) or Payment.objects.filter(order=order, paid_at__isnull=False).exists() or PaymentAttempt.objects.filter(payment__order=order).exists():
                raise DRFValidationError({'items': 'Orders with a promotion, redeemed bonuses or an initiated payment cannot change items. Cancel an unpaid order after payment verification and place a new one.'})
            from .promotions import quote
            lines = [{'menu_item': i['item_id'], 'quantity': i['quantity']} for i in modified_items]
            totals, _ = quote(request.user, lines, consume=True)
            if loyalty_record:
                from loyalty.services import quote_bonus
                _, bonus_lines = quote_bonus(request.user, lines, totals, 0)
                loyalty_record.lines = bonus_lines
                loyalty_record.save(update_fields=['lines'])
            total_amount = totals['items_amount'] + order.delivery_fee
            for item, line in zip(modified_items, lines):
                item['item_id'] = line['menu_item']
            order.items_amount = totals['items_amount']
        if "delivery_address" in updates:
            order.delivery_address = updates["delivery_address"]
        if "delivery_notes" in updates:
            order.delivery_notes = updates["delivery_notes"]
        update_fields = ["delivery_address", "delivery_notes", "updated_at"]
        if modified_items is not None:
            order.total_amount = total_amount
            order.items.all().delete()
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        menu_item=item["item_id"],
                        item_name=item["item_id"].name,
                        quantity=item["quantity"],
                        price_per_item=item["item_id"].price,
                        subtotal=item["item_id"].price * item["quantity"],
                    )
                    for item in modified_items
                ]
            )
            update_fields.extend(['total_amount', 'items_amount'])
            from payments.models import Payment
            Payment.objects.filter(order=order, status='pending').update(amount=total_amount)
        order.save(update_fields=update_fields)

    order.refresh_from_db()
    return Response(OrderSerializer(order).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def assign_delivery_person(request, order_id):
    """Assign delivery person to order - Manager/Admin only"""
    user = request.user
    if user.role not in ["admin", "manager"]:
        return Response(
            {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
        )

    try:
        order = Order.objects.get(id=order_id)
        delivery_person_id = request.data.get("delivery_person_id")

        from users.models import User

        delivery_person = User.objects.get(id=delivery_person_id, role="delivery")

        order.delivery_person = delivery_person
        from payments.models import Payment

        payment = Payment.objects.filter(order=order, method="online").first()
        if not payment or payment.status == "paid":
            order.status = "confirmed"
        order.save()

        return Response(
            {"message": f"Delivery person {delivery_person.username} assigned"}
        )
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
    except User.DoesNotExist:
        return Response(
            {"error": "Delivery person not found"}, status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def order_summary(request):
    """Get order summary statistics"""
    user = request.user
    if user.role not in ["admin", "manager", "analyst"]:
        return Response(
            {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
        )

    queryset = Order.objects.all()

    queryset = filter_by_created_date(
        queryset,
        request.query_params.get("start_date"),
        request.query_params.get("end_date"),
    )

    total_orders = queryset.count()
    total_revenue = queryset.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
    status_breakdown = queryset.values("status").annotate(count=Count("id"))

    return Response(
        {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "status_breakdown": list(status_breakdown),
        }
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def preview_promotion(request):
    from decimal import Decimal
    from .promotions import quote
    from payments.freedompay import configured
    serializer = OrderSerializer(data={**request.data, 'delivery_address': 'preview'})
    serializer.is_valid(raise_exception=True)
    totals, _ = quote(request.user, serializer.validated_data['items'], serializer.validated_data.get('promo_code', ''))
    from loyalty.services import quote_bonus
    bonus, _ = quote_bonus(request.user, serializer.validated_data['items'], totals, serializer.validated_data.get('cashback_amount', 0))
    from django.conf import settings
    return Response({
        **{key: str(value) if isinstance(value, Decimal) else value for key, value in totals.items()},
        **bonus,
        'online_payment_configured': configured(),
        'payment_test_mode': settings.FREEDOMPAY_TEST_MODE,
    })
