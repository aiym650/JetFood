from django.urls import path
from . import views

urlpatterns = [
    path('', views.ExternalIntegrationListCreateView.as_view(), name='integration-list'),
    path('<int:pk>/', views.ExternalIntegrationDetailView.as_view(), name='integration-detail'),
    path('logs/', views.IntegrationLogListView.as_view(), name='integration-logs'),
    path('<int:integration_id>/test/', views.test_integration, name='test-integration'),
    path('<int:integration_id>/sync/', views.sync_integration, name='sync-integration'),
]
