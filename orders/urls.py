from django.urls import path
from . import views

urlpatterns = [
    path('quote/', views.preview_promotion, name='order-quote'),
    path('menu/', views.MenuItemListCreateView.as_view(), name='menu-list'),
    path('menu/<int:pk>/', views.MenuItemDetailView.as_view(), name='menu-detail'),
    path('', views.OrderListCreateView.as_view(), name='order-list'),
    path('requests/', views.refund_request_list, name='refund-request-list'),
    path('requests/<int:request_id>/approve/', views.approve_refund_request, name='approve-refund-request'),
    path('requests/<int:request_id>/reject/', views.reject_refund_request, name='reject-refund-request'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('<int:order_id>/cancel/', views.cancel_order, name='cancel-order'),
    path('<int:order_id>/requests/', views.create_refund_request, name='create-refund-request'),
    path('<int:order_id>/status/', views.update_order_status, name='update-status'),
    path('<int:order_id>/modify/', views.modify_order, name='modify-order'),
    path('<int:order_id>/confirm-delivery/', views.confirm_delivery, name='confirm-delivery'),
    path('<int:order_id>/route/', views.delivery_route, name='delivery-route'),
    path('<int:order_id>/assign/', views.assign_delivery_person, name='assign-delivery'),
    path('summary/', views.order_summary, name='order-summary'),
]
