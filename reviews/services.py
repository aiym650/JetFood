from decimal import Decimal
from django.db import transaction
from django.db.models import Avg, Count
from restaurants.models import Restaurant
from users.models import User


@transaction.atomic
def recalculate_rating(restaurant_id, courier_id=None):
    from .models import Review

    restaurant = Restaurant.objects.select_for_update().filter(pk=restaurant_id).first()
    if restaurant:
        qs = Review.objects.filter(restaurant_id=restaurant_id, status=Review.STATUS_PUBLISHED)
        aggregate = qs.aggregate(avg=Avg("overall_rating"), count=Count("id"))
        restaurant.avg_rating = aggregate["avg"] or Decimal("0")
        restaurant.reviews_count = aggregate["count"] or 0
        restaurant.save(update_fields=["avg_rating", "reviews_count"])

    if courier_id:
        courier = User.objects.select_for_update().filter(pk=courier_id).first()
        if courier:
            qs = Review.objects.filter(courier_id=courier_id, status=Review.STATUS_PUBLISHED)
            aggregate = qs.aggregate(avg=Avg("overall_rating"), count=Count("id"))
            courier.avg_rating = aggregate["avg"] or Decimal("0")
            courier.reviews_count = aggregate["count"] or 0
            courier.save(update_fields=["avg_rating", "reviews_count"])
