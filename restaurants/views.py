from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied

from .models import Restaurant
from .serializers import RestaurantSerializer


def can_manage(user):
    return user.role in ['admin', 'manager']


class RestaurantListCreateView(generics.ListCreateAPIView):
    serializer_class = RestaurantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Restaurant.objects.all()
        if not can_manage(self.request.user):
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_create(self, serializer):
        if not can_manage(self.request.user):
            raise PermissionDenied('Only admins and managers can register restaurants.')
        serializer.save()


class RestaurantDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RestaurantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Restaurant.objects.all()
        if not can_manage(self.request.user):
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_update(self, serializer):
        if not can_manage(self.request.user):
            raise PermissionDenied('Only admins and managers can edit restaurants.')
        serializer.save()

    def perform_destroy(self, instance):
        if not can_manage(self.request.user):
            raise PermissionDenied('Only admins and managers can delete restaurants.')
        instance.delete()
