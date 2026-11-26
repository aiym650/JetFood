from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    readonly_fields = [f.name for f in Payment._meta.fields]
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

    list_display = ['id', 'order', 'method', 'status', 'amount', 'created_at']
    list_filter = ['method', 'status']
    search_fields = ['order__order_number', 'transaction_id']


from .models import PaymentAttempt, PaymentEvent, PaymentRefund
from loyalty.admin import AuditAdmin
admin.site.register(PaymentAttempt, AuditAdmin)
admin.site.register(PaymentEvent, AuditAdmin)
admin.site.register(PaymentRefund, AuditAdmin)
