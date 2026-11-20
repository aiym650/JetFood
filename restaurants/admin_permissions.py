from django.core.exceptions import PermissionDenied


class RestaurantScopeAdmin:
    """Limit staff with a manager role to objects owned by their restaurant."""
    restaurant_owner_lookup = 'restaurant__owner'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser or request.user.role == 'admin':
            return queryset
        return queryset.filter(**{self.restaurant_owner_lookup: request.user})

    def save_model(self, request, obj, form, change):
        restaurant = obj if self.restaurant_owner_lookup == 'owner' else obj.restaurant
        if not request.user.is_superuser and request.user.role != 'admin':
            if self.restaurant_owner_lookup == 'owner' and not change:
                obj.owner = request.user
            elif restaurant.owner_id != request.user.pk:
                raise PermissionDenied('Only the restaurant owner can manage this object.')
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and request.user.role != 'admin':
            if db_field.name == 'restaurant':
                from .models import Restaurant
                kwargs['queryset'] = Restaurant.objects.filter(owner=request.user)
            elif db_field.name == 'menu_category':
                from .models import MenuCategory
                kwargs['queryset'] = MenuCategory.objects.filter(restaurant__owner=request.user)
            elif db_field.name == 'owner':
                from django.contrib.auth import get_user_model
                kwargs['queryset'] = get_user_model().objects.filter(pk=request.user.pk)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
