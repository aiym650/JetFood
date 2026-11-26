from django.contrib import admin
from .models import LedgerEntry, LoyaltyOrder, LoyaltyPolicy, SecondOrderReward, Wallet


@admin.register(LoyaltyPolicy)
class PolicyAdmin(admin.ModelAdmin):
    fields = ['base_percent', 'silver_orders', 'silver_percent', 'gold_orders', 'gold_percent', 'promotional_percent', 'spend_percent', 'second_order_bonus', 'second_order_days', 'jetpoints_started_at']
    readonly_fields = ['jetpoints_started_at']

    def has_add_permission(self, request):
        return not LoyaltyPolicy.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class AuditAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Wallet, AuditAdmin)
admin.site.register(LedgerEntry, AuditAdmin)
admin.site.register(LoyaltyOrder, AuditAdmin)

admin.site.register(SecondOrderReward, AuditAdmin)
