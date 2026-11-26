from django.contrib import admin
from .models import MenuItem, Order, OrderItem, PromoCode, PromoRedemption
from restaurants.admin_permissions import RestaurantScopeAdmin


@admin.register(MenuItem)
class MenuItemAdmin(RestaurantScopeAdmin, admin.ModelAdmin):
    readonly_fields = ['category', 'rating']
    list_display = ['name', 'restaurant', 'menu_category', 'price', 'rating', 'is_active', 'cashback_promotional']
    list_filter = ['restaurant', 'menu_category', 'is_active']
    list_editable = ['price', 'is_active']
    search_fields = ['name', 'description']

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if request.user.role != 'admin' and not request.user.is_superuser:
            fields.append('cashback_promotional')
        return fields


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = [f.name for f in OrderItem._meta.fields]
    can_delete = False
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    readonly_fields = ['promo_code', 'items_amount', 'discount_amount', 'delivery_fee', 'delivery_discount', 'total_amount', 'idempotency_key', 'request_fingerprint']
    list_display = ['order_number', 'customer', 'status', 'priority', 'total_amount', 'created_at']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['order_number', 'customer__username']
    inlines = [OrderItemInline]
    ordering = ['-created_at']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    readonly_fields = [f.name for f in OrderItem._meta.fields]
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    list_display = ['order', 'item_name', 'quantity', 'price_per_item', 'subtotal']
    search_fields = ['item_name']


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'kind', 'value', 'is_active', 'restaurant', 'used_count', 'usage_limit', 'ends_at']
    list_filter = ['kind', 'is_active', 'restaurant']
    search_fields = ['code']
    readonly_fields = ['used_count']


@admin.register(PromoRedemption)
class PromoRedemptionAdmin(admin.ModelAdmin):
    list_display = ['promo', 'user', 'order', 'created_at']
    readonly_fields = ['promo', 'user', 'order', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
