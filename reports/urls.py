from django.urls import path
from . import views

urlpatterns = [
    path('', views.ReportListCreateView.as_view(), name='report-list'),
    path('<int:pk>/', views.ReportDetailView.as_view(), name='report-detail'),
    path('schedules/', views.ReportScheduleListCreateView.as_view(), name='report-schedules'),
    path('schedules/<int:pk>/', views.ReportScheduleDetailView.as_view(), name='report-schedule-detail'),
    path('<int:report_id>/download/', views.download_report, name='download-report'),
]
