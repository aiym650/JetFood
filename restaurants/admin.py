from django.contrib import admin

from .models import Restaurant, RestaurantBranch, MenuCategory
from .admin_permissions import RestaurantScopeAdmin


@admin.register(MenuCategory)
class MenuCategoryAdmin(RestaurantScopeAdmin, admin.ModelAdmin):
    list_display = ['name', 'restaurant', 'position']
    list_filter = ['restaurant']
    search_fields = ['name', 'restaurant__name']


class RestaurantBranchInline(admin.TabularInline):
    model = RestaurantBranch
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(RestaurantScopeAdmin, admin.ModelAdmin):
    restaurant_owner_lookup = 'owner'
    list_display = ['name', 'address', 'is_active', 'opening_time', 'closing_time']
    list_filter = ['is_active', 'cuisine']
    search_fields = ['name', 'address']
    inlines = [RestaurantBranchInline]
