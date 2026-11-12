from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import DeliveryRoute, MenuItem, Order, OrderItem
from .serializers import (
    MenuItemSerializer,
    OrderSerializer,
    OrderItemSerializer,
    OrderStatusUpdateSerializer,
    OrderModificationSerializer,
    DeliveryRouteSerializer,
    DeliveryRouteInputSerializer,
)
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
        if user.role == 'admin':
            return Order.objects.all()
        elif user.role == 'manager':
            return Order.objects.all()
        elif user.role == 'delivery':
            return Order.objects.filter(delivery_person=user)
        else:
            return Order.objects.filter(customer=user)
    
    def perform_create(self, serializer):
        user = self.request.user
        try:
            validate_user_pending_orders(user)

            total_amount = sum(
                item['quantity'] * item['menu_item'].price
                for item in serializer.validated_data['items']
            )
            item_count = sum(item['quantity'] for item in serializer.validated_data['items'])
            if item_count > BusinessConstraints.MAX_ITEMS_PER_ORDER:
                raise DRFValidationError({
                    'items': f'В одном заказе можно заказать не более {BusinessConstraints.MAX_ITEMS_PER_ORDER} блюд.'
                })
            validate_order_amount(total_amount)

            estimated_time = serializer.validated_data.get('estimated_delivery_time')
            if estimated_time:
                validate_delivery_time(estimated_time)
        except DjangoValidationError as error:
            raise DRFValidationError(error.messages) from error

        order_number = 'ORD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        payment_method = serializer.validated_data.get('payment_method', 'cash')
        from payments.services import create_order_payment

        with transaction.atomic():
            order = serializer.save(
                customer=user,
                order_number=order_number,
                total_amount=total_amount,
                status='pending',
                priority='normal',
                delivery_person=None,
            )
            create_order_payment(order, payment_method)


class MenuItemListCreateView(generics.ListCreateAPIView):
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        queryset = MenuItem.objects.select_related('restaurant')
        if user.role not in ['admin', 'manager']:
            queryset = queryset.filter(is_active=True, restaurant__is_active=True)
        restaurant_id = self.request.query_params.get('restaurant')
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        return queryset

    def perform_create(self, serializer):
        if self.request.user.role not in ['admin', 'manager']:
            raise PermissionDenied("Only admins and managers can manage menu items")
        serializer.save()


class MenuItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = MenuItem.objects.select_related('restaurant')
        if user.role not in ['admin', 'manager']:
            queryset = queryset.filter(is_active=True, restaurant__is_active=True)
        return queryset

    def perform_update(self, serializer):
        if self.request.user.role not in ['admin', 'manager']:
            raise PermissionDenied("Only admins and managers can manage menu items")
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.role not in ['admin', 'manager']:
            raise PermissionDenied("Only admins and managers can manage menu items")
        instance.delete()


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Order.objects.all()
        elif user.role == 'manager':
            return Order.objects.all()
        elif user.role == 'delivery':
            return Order.objects.filter(delivery_person=user)
        else:
            return Order.objects.filter(customer=user)

    def perform_update(self, serializer):
        if self.request.user.role not in ['admin', 'manager']:
            raise PermissionDenied("Only admins and managers can edit orders")
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.role not in ['admin', 'manager']:
            raise PermissionDenied("Only admins and managers can delete orders")
        instance.delete()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_order_status(request, order_id):
    """Update order status"""
    serializer = OrderStatusUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    user = request.user
    if user.role not in ['customer', 'delivery', 'admin', 'manager']:
        raise PermissionDenied("Permission denied")

    if user.role in ['admin', 'manager']:
        queryset = Order.objects.all()
    elif user.role == 'delivery':
        queryset = Order.objects.filter(delivery_person=user)
    else:
        queryset = Order.objects.filter(customer=user)

    order = get_object_or_404(queryset, id=order_id)

    if user.role == 'customer':
        if order.status not in ['pending'] or serializer.validated_data['status'] != 'cancelled':
            return Response({'error': 'You can only cancel pending orders'}, 
                          status=status.HTTP_403_FORBIDDEN)
    elif user.role == 'delivery':
        allowed_transition = (
            (order.status == 'preparing' and serializer.validated_data['status'] == 'delivering')
            or (order.status == 'delivering' and serializer.validated_data['status'] == 'delivered')
        )
        if not allowed_transition:
            return Response(
                {'error': 'Delivery persons must move orders from preparing to delivering, then delivered'},
                status=status.HTTP_403_FORBIDDEN,
            )

    order.status = serializer.validated_data['status']

    if order.status == 'delivered':
        order.actual_delivery_time = timezone.now()

    order.save()
    if order.status == 'cancelled':
        from payments.models import Payment

        payment = Payment.objects.filter(order=order).first()
        if payment:
            if payment.status == 'paid':
                payment.status = 'refund_requested'
            elif payment.status == 'pending':
                payment.status = 'cancelled'
            payment.save(update_fields=['status', 'updated_at'])
    return Response({'message': f'Order status updated to {order.status}'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def confirm_delivery(request, order_id):
    if request.user.role != 'customer':
        raise PermissionDenied('Only the customer can confirm receipt.')
    order = get_object_or_404(Order.objects.filter(customer=request.user), id=order_id)
    if order.status != 'delivered':
        return Response(
            {'detail': 'The courier must mark the order delivered before receipt can be confirmed.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if order.delivery_confirmed_at:
        return Response(
            {'detail': 'Delivery has already been confirmed.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    order.delivery_confirmed_at = timezone.now()
    order.save(update_fields=['delivery_confirmed_at', 'updated_at'])
    return Response({
        'message': 'Delivery confirmed.',
        'delivery_confirmed_at': order.delivery_confirmed_at,
    })


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def delivery_route(request, order_id):
    user = request.user
    if user.role in ['admin', 'manager']:
        order_queryset = Order.objects.all()
    elif user.role == 'delivery':
        order_queryset = Order.objects.filter(delivery_person=user)
    else:
        order_queryset = Order.objects.filter(customer=user)
    order = get_object_or_404(order_queryset, id=order_id)

    if request.method == 'GET':
        route = DeliveryRoute.objects.filter(order=order).select_related('updated_by', 'order').first()
        if route is None:
            return Response({'detail': 'A delivery route has not been planned.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(DeliveryRouteSerializer(route).data)

    if user.role not in ['admin', 'manager'] and not (
        user.role == 'delivery' and order.delivery_person_id == user.id
    ):
        raise PermissionDenied('Only the assigned courier, a manager, or an admin can manage the route.')

    serializer = DeliveryRouteInputSerializer(data=request.data, partial=request.method == 'PATCH')
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        route = DeliveryRoute.objects.select_for_update().filter(order=order).first()
        if route is None:
            if not serializer.validated_data.get('origin_address'):
                raise DRFValidationError({'origin_address': 'This field is required to plan a route.'})
            route = DeliveryRoute.objects.create(
                order=order,
                origin_address=serializer.validated_data['origin_address'],
                notes=serializer.validated_data.get('notes', ''),
                updated_by=user,
            )
        else:
            for field in ['origin_address', 'notes']:
                if field in serializer.validated_data:
                    setattr(route, field, serializer.validated_data[field])
            route.updated_by = user
            route.save()

    return Response(DeliveryRouteSerializer(route).data, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def modify_order(request, order_id):
    if request.user.role != 'customer':
        raise PermissionDenied("Only customers can modify their orders.")

    serializer = OrderModificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    updates = serializer.validated_data
    modified_items = updates.get('items')
    total_amount = None

    if modified_items is not None:
        item_count = sum(item['quantity'] for item in modified_items)
        if item_count > BusinessConstraints.MAX_ITEMS_PER_ORDER:
            raise DRFValidationError({
                'items': f'An order cannot contain more than {BusinessConstraints.MAX_ITEMS_PER_ORDER} dishes.'
            })
        total_amount = sum(
            item['quantity'] * item['item_id'].price
            for item in modified_items
        )
        try:
            validate_order_amount(total_amount)
        except DjangoValidationError as error:
            raise DRFValidationError(error.messages) from error

    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update().filter(customer=request.user),
            id=order_id,
        )
        if order.status != 'pending':
            return Response(
                {'detail': 'Orders can only be modified before confirmation.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if 'delivery_address' in updates:
            order.delivery_address = updates['delivery_address']
        if 'delivery_notes' in updates:
            order.delivery_notes = updates['delivery_notes']
        update_fields = ['delivery_address', 'delivery_notes', 'updated_at']
        if modified_items is not None:
            order.total_amount = total_amount
            order.items.all().delete()
            OrderItem.objects.bulk_create([
                OrderItem(
                    order=order,
                    menu_item=item['item_id'],
                    item_name=item['item_id'].name,
                    quantity=item['quantity'],
                    price_per_item=item['item_id'].price,
                    subtotal=item['item_id'].price * item['quantity'],
                )
                for item in modified_items
            ])
            update_fields.append('total_amount')
        order.save(update_fields=update_fields)

    order.refresh_from_db()
    return Response(OrderSerializer(order).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def assign_delivery_person(request, order_id):
    """Assign delivery person to order - Manager/Admin only"""
    user = request.user
    if user.role not in ['admin', 'manager']:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        order = Order.objects.get(id=order_id)
        delivery_person_id = request.data.get('delivery_person_id')
        
        from users.models import User
        delivery_person = User.objects.get(id=delivery_person_id, role='delivery')
        
        order.delivery_person = delivery_person
        order.status = 'confirmed'
        order.save()
        
        return Response({'message': f'Delivery person {delivery_person.username} assigned'})
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    except User.DoesNotExist:
        return Response({'error': 'Delivery person not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def order_summary(request):
    """Get order summary statistics"""
    user = request.user
    if user.role not in ['admin', 'manager', 'analyst']:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    queryset = Order.objects.all()
    
    queryset = filter_by_created_date(
        queryset,
        request.query_params.get('start_date'),
        request.query_params.get('end_date'),
    )
    
    total_orders = queryset.count()
    total_revenue = queryset.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    status_breakdown = queryset.values('status').annotate(count=Count('id'))
    
    return Response({
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'status_breakdown': list(status_breakdown),
    })
