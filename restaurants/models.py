from django.db import models


def default_working_days():
    return list(range(7))


class Restaurant(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=500)
    phone = models.CharField(max_length=20, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    working_days = models.JSONField(default=default_working_days)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
