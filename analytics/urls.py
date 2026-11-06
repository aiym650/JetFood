from django.urls import path
from . import views

urlpatterns = [
    path('events/', views.AnalyticsEventListCreateView.as_view(), name='analytics-events'),
    path('metrics/', views.SystemMetricListCreateView.as_view(), name='system-metrics'),
    path('reports/', views.PerformanceReportListView.as_view(), name='performance-reports'),
    path('analysis/', views.system_analysis, name='system-analysis'),
    path('apply-role-updates/', views.apply_role_updates, name='apply-role-updates'),
]
