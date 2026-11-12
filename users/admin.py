from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # DjangoUserAdmin hashes passwords correctly, so users created here can log in
    list_display = ["username", "email", "role", "is_active", "created_at"]
    list_filter = ["role", "is_active", "created_at"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["-created_at"]
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Food Delivery", {"fields": ("role", "phone", "address")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Food Delivery", {"fields": ("email", "role", "phone")}),
    )
