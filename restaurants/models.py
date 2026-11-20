from django.db import models
from django.db.models import F
from django.conf import settings
from backend.image_references import validate_image_reference


def default_working_days():
    return list(range(7))


class Restaurant(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_restaurants",
    )
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    cuisine = models.CharField(max_length=100, blank=True)
    demo_key = models.CharField(max_length=80, unique=True, null=True, blank=True, editable=False)
    address = models.CharField(max_length=500)
    phone = models.CharField(max_length=20, blank=True)
    image_url = models.CharField(max_length=500, blank=True, validators=[validate_image_reference])
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    working_days = models.JSONField(default=default_working_days)
    is_active = models.BooleanField(default=True)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    reviews_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            # CHECK: opening and closing time cannot be the same moment
            models.CheckConstraint(
                condition=~models.Q(opening_time=F('closing_time')),
                name='restaurant_opening_differs_from_closing',
            ),
        ]

    def __str__(self):
        return self.name


class MenuCategory(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']
        constraints = [models.UniqueConstraint(fields=['restaurant', 'name'], name='category_name_per_restaurant')]

    def __str__(self):
        return f'{self.restaurant}: {self.name}'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.pk and self.items.exclude(restaurant_id=self.restaurant_id).exists():
            raise ValidationError({'restaurant': 'A category with dishes cannot move to another restaurant.'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        self.items.update(category=self.name)
