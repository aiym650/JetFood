from django.contrib import admin

from .models import Restaurant


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'is_active', 'opening_time', 'closing_time']
    list_filter = ['is_active']
    search_fields = ['name', 'address']
