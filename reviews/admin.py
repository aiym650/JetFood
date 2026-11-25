from django.contrib import admin
from .models import Review, ReviewDecision
from .policy import decide


class DecisionInline(admin.TabularInline):
    model = ReviewDecision
    extra = 0
    can_delete = False
    readonly_fields = ['actor', 'previous_status', 'status', 'reason', 'comment_snapshot', 'created_at', 'review_reference']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'restaurant', 'overall_rating', 'status', 'updated_at']
    list_filter = ['status', 'restaurant']
    search_fields = ['comment', 'order__order_number']
    inlines = [DecisionInline]
    readonly_fields = [f.name for f in Review._meta.fields]
    actions = ['approve', 'reject']

    @admin.action(description='Approve selected reviews')
    def approve(self, request, queryset):
        for review in queryset:
            decide(review.pk, Review.STATUS_PUBLISHED, 'Approved after administrator review.', request.user)

    @admin.action(description='Reject: abusive content / personal information (author may edit)')
    def reject(self, request, queryset):
        for review in queryset:
            decide(review.pk, Review.STATUS_HIDDEN, 'Rejected after review: remove abusive content, spam and personal information, then resubmit.', request.user)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
