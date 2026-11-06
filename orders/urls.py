from django.urls import path
from . import views

urlpatterns = [
    path('menu/', views.MenuItemListCreateView.as_view(), name='menu-list'),
    path('menu/<int:pk>/', views.MenuItemDetailView.as_view(), name='menu-detail'),
    path('', views.OrderListCreateView.as_view(), name='order-list'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('<int:order_id>/status/', views.update_order_status, name='update-status'),
    path('<int:order_id>/modify/', views.modify_order, name='modify-order'),
    path('<int:order_id>/confirm-delivery/', views.confirm_delivery, name='confirm-delivery'),
    path('<int:order_id>/route/', views.delivery_route, name='delivery-route'),
    path('<int:order_id>/assign/', views.assign_delivery_person, name='assign-delivery'),
    path('summary/', views.order_summary, name='order-summary'),
]
