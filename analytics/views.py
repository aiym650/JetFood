from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from .models import AnalyticsEvent, SystemMetric, PerformanceReport
from .serializers import AnalyticsEventSerializer, SystemMetricSerializer, PerformanceReportSerializer
from users.constraints import validate_role_access


class AnalyticsEventListCreateView(generics.ListCreateAPIView):
    serializer_class = AnalyticsEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'manager', 'analyst']:
            return AnalyticsEvent.objects.all()
        else:
            return AnalyticsEvent.objects.filter(user=user)
    
    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
            ip_address=self.get_client_ip(self.request)
        )
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SystemMetricListCreateView(generics.ListCreateAPIView):
    serializer_class = SystemMetricSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'manager', 'analyst']:
            return SystemMetric.objects.all()
        else:
            return SystemMetric.objects.none()
    
    def perform_create(self, serializer):
        validate_role_access(self.request.user, ['admin', 'manager'])
        serializer.save()


class PerformanceReportListView(generics.ListAPIView):
    serializer_class = PerformanceReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'manager', 'analyst']:
            return PerformanceReport.objects.all()
        else:
            return PerformanceReport.objects.none()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def system_analysis(request):
    """Perform system analysis and suggest role updates"""
    user = request.user
    try:
        validate_role_access(user, ['admin', 'manager', 'analyst'])
    except Exception:
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Admin, manager, or analyst access required")
    
    from orders.models import Order
    from users.models import User
    
    # Analysis 1: Order volume per user
    order_volume = Order.objects.values('customer').annotate(
        order_count=Count('id'),
        total_spent=Sum('total_amount')
    ).order_by('-order_count')[:10]
    
    # Analysis 2: Delivery performance
    delivered_orders = Order.objects.filter(
        status='delivered',
        actual_delivery_time__isnull=False
    )
    delivery_performance = []
    for order in delivered_orders[:5]:
        if order.actual_delivery_time and order.created_at:
            duration = order.actual_delivery_time - order.created_at
            delivery_performance.append({
                'order_number': order.order_number,
                'delivery_duration': str(duration)
            })
    
    # Analysis 3: Active users in last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    active_users = User.objects.filter(
        last_login__gte=thirty_days_ago
    ).count()
    
    # Analysis 4: Revenue trends
    last_7_days = timezone.now() - timedelta(days=7)
    revenue_trend = Order.objects.filter(
        created_at__gte=last_7_days,
        status='delivered'
    ).values('created_at__date').annotate(
        daily_revenue=Sum('total_amount'),
        daily_orders=Count('id')
    ).order_by('created_at__date')
    
    # Role update suggestions based on analysis
    role_suggestions = []
    
    # Suggest upgrade for high-volume customers
    for item in order_volume:
        if item['order_count'] > 20:
            customer = User.objects.get(id=item['customer'])
            if customer.role == 'customer':
                role_suggestions.append({
                    'user_id': customer.id,
                    'username': customer.username,
                    'current_role': customer.role,
                    'suggested_role': 'manager',
                    'reason': f"High order volume: {item['order_count']} orders"
                })
    
    return Response({
        'order_volume_analysis': list(order_volume),
        'delivery_performance': delivery_performance,
        'active_users_last_30_days': active_users,
        'revenue_trend_last_7_days': list(revenue_trend),
        'role_update_suggestions': role_suggestions,
        'generated_at': timezone.now()
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def apply_role_updates(request):
    """Apply suggested role updates - Admin only"""
    user = request.user
    validate_role_access(user, ['admin'])
    
    updates = request.data.get('updates', [])
    applied_updates = []
    
    for update in updates:
        try:
            target_user = User.objects.get(id=update['user_id'])
            new_role = update['new_role']
            
            if new_role in dict(User.ROLE_CHOICES):
                target_user.role = new_role
                target_user.save()
                applied_updates.append({
                    'user_id': target_user.id,
                    'username': target_user.username,
                    'new_role': new_role
                })
        except User.DoesNotExist:
            continue
    
    return Response({
        'message': f'Applied {len(applied_updates)} role updates',
        'updates': applied_updates
    })
