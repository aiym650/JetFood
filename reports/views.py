from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from datetime import datetime, timedelta
from .models import Report, ReportSchedule
from .serializers import ReportSerializer, ReportScheduleSerializer
from users.constraints import validate_role_access
from orders.models import Order
from orders.date_filters import filter_by_created_date


class ReportListCreateView(generics.ListCreateAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'manager', 'analyst']:
            return Report.objects.all()
        else:
            return Report.objects.filter(generated_by=user)
    
    def perform_create(self, serializer):
        validate_role_access(self.request.user, ['admin', 'manager', 'analyst'])
        report = serializer.save(generated_by=self.request.user)
        
        # Generate report content based on type
        self.generate_report_content(report)
    
    def generate_report_content(self, report):
        """Generate report content based on report type"""
        report.status = 'generating'
        report.save()
        
        try:
            if report.report_type == 'sales':
                self.generate_sales_report(report)
            elif report.report_type == 'delivery':
                self.generate_delivery_report(report)
            elif report.report_type == 'customer':
                self.generate_customer_report(report)
            elif report.report_type == 'performance':
                self.generate_performance_report(report)
            
            report.status = 'completed'
            report.completed_at = timezone.now()
            report.file_path = f"/reports/{report.id}_{report.report_type}.{report.format}"
            report.save()
        except Exception as e:
            report.status = 'failed'
            report.save()
    
    def generate_sales_report(self, report):
        """Generate sales report"""
        start_date = report.parameters.get('start_date')
        end_date = report.parameters.get('end_date')
        
        queryset = Order.objects.filter(status='delivered')
        queryset = filter_by_created_date(queryset, start_date, end_date)
        
        total_revenue = queryset.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        total_orders = queryset.count()
        
        # In real implementation, generate PDF/Excel file
        report.parameters.update({
            'total_revenue': str(total_revenue),
            'total_orders': total_orders
        })
    
    def generate_delivery_report(self, report):
        """Generate delivery report"""
        queryset = Order.objects.filter(status='delivered')
        
        avg_delivery_time = queryset.aggregate(
            avg_time=Avg('actual_delivery_time') - Avg('created_at')
        )
        
        report.parameters.update({
            'average_delivery_time': str(avg_delivery_time.get('avg_time', 'N/A'))
        })
    
    def generate_customer_report(self, report):
        """Generate customer report"""
        from users.models import User
        total_customers = User.objects.filter(role='customer').count()
        
        report.parameters.update({
            'total_customers': total_customers
        })
    
    def generate_performance_report(self, report):
        """Generate performance report"""
        queryset = Order.objects.filter(status='delivered')
        
        report.parameters.update({
            'total_delivered': queryset.count()
        })


class ReportDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_destroy(self, instance):
        validate_role_access(self.request.user, ['admin'])
        instance.delete()


class ReportScheduleListCreateView(generics.ListCreateAPIView):
    serializer_class = ReportScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'manager']:
            return ReportSchedule.objects.all()
        else:
            return ReportSchedule.objects.filter(recipients=user)
    
    def perform_create(self, serializer):
        validate_role_access(self.request.user, ['admin', 'manager'])
        serializer.save()


class ReportScheduleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ReportSchedule.objects.all()
    serializer_class = ReportScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_update(self, serializer):
        validate_role_access(self.request.user, ['admin', 'manager'])
        serializer.save()
    
    def perform_destroy(self, instance):
        validate_role_access(self.request.user, ['admin'])
        instance.delete()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_report(request, report_id):
    """Download generated report"""
    try:
        report = Report.objects.get(id=report_id)
        user = request.user
        
        if user.role not in ['admin', 'manager', 'analyst'] and report.generated_by != user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if report.status != 'completed':
            return Response({'error': 'Report not ready'}, status=status.HTTP_400_BAD_REQUEST)
        
        # In real implementation, return file
        return Response({
            'message': 'Report download link',
            'file_path': report.file_path,
            'parameters': report.parameters
        })
    except Report.DoesNotExist:
        return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)
