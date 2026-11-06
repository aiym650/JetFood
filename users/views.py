from django.db import transaction
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import BasePermission
from .models import User, Notification
from .serializers import (UserSerializer, UserRegistrationSerializer,
                          AdminUserCreateSerializer, LoginSerializer, ChangePasswordSerializer,
                          NotificationSerializer, AccountDeletionSerializer,
                          DeliveryAddressSerializer)
from .models import DeliveryAddress
from .constraints import validate_role_access
from django.contrib.auth import logout


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer


class LoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        })


class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
            logout(request)
            return Response({'message': 'Successfully logged out'})
        except:
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'old_password': ['Current password is incorrect.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'message': 'Password changed successfully'})


class DeliveryAddressListCreateView(generics.ListCreateAPIView):
    serializer_class = DeliveryAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DeliveryAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        with transaction.atomic():
            is_first_address = not DeliveryAddress.objects.filter(user=user).exists()
            make_default = serializer.validated_data.get('is_default', False) or is_first_address
            if make_default:
                DeliveryAddress.objects.filter(user=user, is_default=True).update(is_default=False)
            serializer.save(user=user, is_default=make_default)


class DeliveryAddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DeliveryAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DeliveryAddress.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        address = self.get_object()
        make_default = serializer.validated_data.get('is_default', address.is_default)
        with transaction.atomic():
            if make_default:
                DeliveryAddress.objects.filter(
                    user=self.request.user,
                    is_default=True,
                ).exclude(pk=address.pk).update(is_default=False)
            serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        was_default = instance.is_default
        with transaction.atomic():
            instance.delete()
            if was_default:
                replacement = DeliveryAddress.objects.filter(user=user).first()
                if replacement:
                    replacement.is_default = True
                    replacement.save(update_fields=['is_default', 'updated_at'])


class DeleteAccountView(generics.GenericAPIView):
    serializer_class = AccountDeletionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if user.role != 'customer':
            return Response(
                {'detail': 'Only customer accounts can be deleted here.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not user.check_password(serializer.validated_data['password']):
            return Response(
                {'password': ['Password is incorrect.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from orders.models import Order

        active_orders = Order.objects.filter(
            customer=user,
            status__in=['pending', 'confirmed', 'preparing', 'delivering'],
        )
        if active_orders.exists():
            return Response(
                {'detail': 'Cancel or complete active orders before deleting the account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            DeliveryAddress.objects.filter(user=user).delete()
            Notification.objects.filter(user=user).delete()
            Order.objects.filter(customer=user).update(
                delivery_address='',
                delivery_notes='',
            )
            user.username = f'deleted-user-{user.pk}'
            user.email = ''
            user.first_name = ''
            user.last_name = ''
            user.phone = ''
            user.address = ''
            user.is_active = False
            user.set_unusable_password()
            user.save()
            Token.objects.filter(user=user).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return User.objects.all()
        elif user.role == 'manager':
            return User.objects.filter(role__in=['delivery', 'customer'])
        else:
            return User.objects.filter(id=user.id)


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')


class AdminUserCreateView(generics.CreateAPIView):
    serializer_class = AdminUserCreateSerializer
    permission_classes = [IsAdminRole]


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return User.objects.all()
        if user.role == 'manager':
            return User.objects.filter(role__in=['delivery', 'customer'])
        return User.objects.filter(id=user.id)

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        validate_role_access(user, ['admin'])
        instance.delete()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_user_role(request, user_id):
    """Update user role - Admin only"""
    user = request.user
    try:
        validate_role_access(user, ['admin'])
    except Exception:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        target_user = User.objects.get(id=user_id)
        new_role = request.data.get('role')
        if new_role not in dict(User.ROLE_CHOICES):
            return Response({'error': 'Invalid role'}, status=status.HTTP_400_BAD_REQUEST)

        target_user.role = new_role
        target_user.save()
        return Response({'message': f'Role updated to {new_role}'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(is_read=True)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({'message': 'All notifications marked as read'})


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def clear_all_notifications(request):
    """Clear all notifications"""
    Notification.objects.filter(user=request.user).delete()
    return Response({'message': 'All notifications cleared'})
