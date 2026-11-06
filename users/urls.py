from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('addresses/', views.DeliveryAddressListCreateView.as_view(), name='address-list'),
    path('addresses/<int:pk>/', views.DeliveryAddressDetailView.as_view(), name='address-detail'),
    path('account/', views.DeleteAccountView.as_view(), name='delete-account'),
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/create/', views.AdminUserCreateView.as_view(), name='user-create'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('users/<int:user_id>/role/', views.update_user_role, name='update-role'),
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark-all-read'),
    path('notifications/clear-all/', views.clear_all_notifications, name='clear-all'),
]
