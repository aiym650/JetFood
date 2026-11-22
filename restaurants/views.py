from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied

from .models import Restaurant
from django.db.models import Q
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
        search = self.request.query_params.get('search', '').strip()
        cuisine = self.request.query_params.get('cuisine', '').strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search) | Q(cuisine__icontains=search))
        if cuisine:
            queryset = queryset.filter(cuisine__iexact=cuisine)
        return queryset

    def perform_create(self, serializer):
        if not can_manage(self.request.user):
            raise PermissionDenied('Only admins and managers can register restaurants.')
        owner = self.request.user if self.request.user.role == 'manager' else None
        serializer.save(owner=owner)


class RestaurantDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RestaurantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Restaurant.objects.all()
        if not can_manage(self.request.user):
            queryset = queryset.filter(is_active=True)
        search = self.request.query_params.get('search', '').strip()
        cuisine = self.request.query_params.get('cuisine', '').strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search) | Q(cuisine__icontains=search))
        if cuisine:
            queryset = queryset.filter(cuisine__iexact=cuisine)
        return queryset

    def perform_update(self, serializer):
        if not can_manage(self.request.user):
            raise PermissionDenied('Only admins and managers can edit restaurants.')
        if self.request.user.role != 'admin' and serializer.instance.owner_id != self.request.user.pk:
            raise PermissionDenied('Only the restaurant owner can edit this restaurant.')
        serializer.save()

    def perform_destroy(self, instance):
        if not can_manage(self.request.user):
            raise PermissionDenied('Only admins and managers can delete restaurants.')
        if self.request.user.role != 'admin' and instance.owner_id != self.request.user.pk:
            raise PermissionDenied('Only the restaurant owner can edit this restaurant.')
        instance.is_active = False
        instance.save(update_fields=['is_active'])
