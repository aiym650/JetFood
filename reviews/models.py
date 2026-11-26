from django.conf import settings
from django.db import models
from django.db.models import Q


class Review(models.Model):
    STATUS_PUBLISHED = "published"
    STATUS_PENDING = "pending_moderation"
    STATUS_HIDDEN = "hidden"
    STATUS_CHOICES = [
        (STATUS_PUBLISHED, "Published"),
        (STATUS_PENDING, "Pending moderation"),
        (STATUS_HIDDEN, "Hidden"),
    ]
    SENTIMENT_CHOICES = [
        ("positive", "Positive"),
        ("neutral", "Neutral"),
        ("negative", "Negative"),
    ]

    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="review")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    restaurant = models.ForeignKey("restaurants.Restaurant", on_delete=models.CASCADE, related_name="reviews")
    courier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courier_reviews",
    )
    restaurant_rating = models.PositiveSmallIntegerField()
    food_rating = models.PositiveSmallIntegerField()
    courier_rating = models.PositiveSmallIntegerField()
    delivery_speed_rating = models.PositiveSmallIntegerField()
    overall_rating = models.DecimalField(max_digits=3, decimal_places=2)
    comment = models.TextField(max_length=1000, null=True, blank=True)
    moderation_reason = models.CharField(max_length=500, blank=True)
    sentiment = models.CharField(max_length=8, choices=SENTIMENT_CHOICES, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "-created_at"], name="review_rest_created_idx"),
            models.Index(fields=["courier", "-created_at"], name="review_cour_created_idx"),
            models.Index(fields=["order"], name="review_order_idx"),
            models.Index(fields=["-created_at"], name="review_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(restaurant_rating__gte=1, restaurant_rating__lte=5),
                name="review_restaurant_rating_1_5",
            ),
            models.CheckConstraint(condition=Q(food_rating__gte=1, food_rating__lte=5), name="review_food_rating_1_5"),
            models.CheckConstraint(condition=Q(courier_rating__gte=1, courier_rating__lte=5), name="review_courier_rating_1_5"),
            models.CheckConstraint(condition=Q(delivery_speed_rating__gte=1, delivery_speed_rating__lte=5), name="review_speed_rating_1_5"),
            models.CheckConstraint(condition=Q(overall_rating__gte=1, overall_rating__lte=5), name="review_overall_rating_1_5"),
        ]


class ReviewPhoto(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="photos")
    url = models.URLField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)


class ReviewReply(models.Model):
    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name="reply")
    restaurant = models.ForeignKey("restaurants.Restaurant", on_delete=models.CASCADE, related_name="review_replies")
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)


class ReviewReport(models.Model):
    STATUS_OPEN = "open"
    STATUS_RESOLVED = "resolved"
    STATUS_CHOICES = [(STATUS_OPEN, "Open"), (STATUS_RESOLVED, "Resolved")]

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_reports")
    reason = models.CharField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["review", "reporter"], name="review_one_report_per_user"),
        ]
        indexes = [models.Index(fields=["review", "status"], name="report_review_status_idx")]


class ReviewReminder(models.Model):
    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="review_reminder")
    due_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["due_at", "sent_at"], name="review_reminder_due_idx")]


class ReviewDecision(models.Model):
    review = models.ForeignKey(Review, null=True, blank=True, on_delete=models.SET_NULL, related_name='decisions')
    review_reference = models.PositiveBigIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    previous_status = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20)
    reason = models.CharField(max_length=500)
    comment_snapshot = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
