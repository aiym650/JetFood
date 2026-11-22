from django.contrib import admin

from .models import SupportCase, SupportMessage, FAQ

admin.site.register(FAQ)


class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 0
    readonly_fields = ('sender', 'body', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SupportCase)
class SupportCaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_number', 'customer', 'language', 'operator_requested', 'status', 'updated_at')
    list_filter = ('status', 'operator_requested', 'language', 'created_at')
    search_fields = ('order_number', 'customer__username', 'issue_description')
    readonly_fields = (
        'customer', 'order', 'order_number', 'issue_description',
        'created_at', 'updated_at',
    )
    inlines = [SupportMessageInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
