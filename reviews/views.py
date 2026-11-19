import html
import os
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from orders.models import Order
from restaurants.models import Restaurant
from users.models import User
from users.notifications import notify_review_reminder
from .models import Review, ReviewPhoto, ReviewReply, ReviewReport, ReviewReminder
from .serializers import ReviewSerializer, ReplySerializer
from .moderation import contains_profanity, analyze_sentiment_async
from .services import recalculate_rating


def _rating_fields(data):
    fields = ("restaurant_rating", "food_rating", "courier_rating", "delivery_speed_rating")
    missing = [field for field in fields if field not in data]
    if missing:
        raise ValidationError({field: "This field is required." for field in missing})
    values = []
    for field in fields:
        try:
            value = int(data[field])
        except (TypeError, ValueError):
            raise ValidationError({field: "Rating must be an integer from 1 to 5."})
        if value < 1 or value > 5:
            raise ValidationError({field: "Rating must be between 1 and 5."})
        values.append(value)
    return dict(zip(fields, values)), sum(values) / Decimal("4")


def _save_photos(request, review):
    files = request.FILES.getlist("photos")
    existing_count = review.photos.count()
    if existing_count + len(files) > 3:
        raise ValidationError({"photos": "A review may contain at most 3 photos."})
    allowed = {"image/jpeg", "image/png", "image/webp"}
    for uploaded in files:
        if uploaded.content_type not in allowed:
            raise ValidationError({"photos": "Only JPG, PNG and WebP files are allowed."})
        if uploaded.size > 5 * 1024 * 1024:
            raise ValidationError({"photos": "Each photo must be at most 5 MB."})

    from django.conf import settings
    media_root = settings.MEDIA_ROOT
    os.makedirs(os.path.join(media_root, "review_photos"), exist_ok=True)
    for uploaded in files:
        ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[uploaded.content_type]
        filename = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(media_root, "review_photos", filename)
        try:
            from PIL import Image
            image = Image.open(uploaded)
            image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGB")
            image.save(path, quality=82, optimize=True)
        except Exception:
            with open(path, "wb") as target:
                for chunk in uploaded.chunks():
                    target.write(chunk)
        relative_url = f"{settings.MEDIA_URL}review_photos/{filename}"
        absolute_url = request.build_absolute_uri(relative_url)
        ReviewPhoto.objects.create(review=review, url=absolute_url)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_review(request, order_id):
    order = Order.objects.select_related("customer", "delivery_person").filter(pk=order_id).first()
    if not order:
        return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    if order.customer_id != request.user.id:
        return Response({"detail": "You can only review your own order."}, status=status.HTTP_403_FORBIDDEN)
    if order.status != "delivered":
        return Response({"detail": "The order must be delivered before review."}, status=status.HTTP_409_CONFLICT)
    if hasattr(order, "review"):
        return Response({"detail": "A review already exists for this order."}, status=status.HTTP_409_CONFLICT)

    ratings, average = _rating_fields(request.data)
    comment = request.data.get("comment")
    if comment is not None:
        comment = html.escape(str(comment).strip())
        if len(comment) > 1000:
            raise ValidationError({"comment": "Comment must not exceed 1000 characters."})

    menu_item = order.items.select_related("menu_item__restaurant").exclude(menu_item=None).first()
    restaurant = menu_item.menu_item.restaurant if menu_item and menu_item.menu_item else None
    if not restaurant:
        return Response({"detail": "Order has no associated restaurant."}, status=status.HTTP_409_CONFLICT)

    average = Decimal(str(average)).quantize(Decimal("0.01"))
    review_status = Review.STATUS_PENDING if contains_profanity(comment) else Review.STATUS_PUBLISHED
    try:
        with transaction.atomic():
            review = Review.objects.create(
                order=order,
                user=request.user,
                restaurant=restaurant,
                courier=order.delivery_person,
                overall_rating=average,
                comment=comment,
                status=review_status,
                **ratings,
            )
            _save_photos(request, review)
            recalculate_rating(restaurant.id, order.delivery_person_id)
    except IntegrityError:
        return Response({"detail": "A review already exists for this order."}, status=status.HTTP_409_CONFLICT)

    from users.models import Notification, User
    recipients = list(User.objects.filter(role="admin"))
    if restaurant.owner_id:
        recipients.append(restaurant.owner)
    recipients = {recipient.id: recipient for recipient in recipients}
    for recipient in recipients.values():
        Notification.objects.create(
            user=recipient,
            notification_type="system",
            title="New restaurant review",
            message=f"A new review was submitted for {restaurant.name}.",
            link=f"/restaurants/{restaurant.id}",
        )

    transaction.on_commit(lambda: analyze_sentiment_async(review.id))
    return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


@api_view(["PUT", "PATCH", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
def update_review(request, review_id):
    if request.method == "DELETE":
        return delete_review(request, review_id)
    review = Review.objects.filter(pk=review_id).first()
    if not review:
        return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)
    if review.user_id != request.user.id:
        return Response({"detail": "You can only edit your own review."}, status=status.HTTP_403_FORBIDDEN)
    if timezone.now() - review.created_at > timezone.timedelta(hours=24):
        return Response({"detail": "The 24-hour review editing period has expired."}, status=status.HTTP_403_FORBIDDEN)

    serializer = ReviewSerializer(review, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    comment = serializer.validated_data.get("comment", review.comment)
    if comment is not None:
        comment = html.escape(str(comment).strip())
        if len(comment) > 1000:
            raise ValidationError({"comment": "Comment must not exceed 1000 characters."})
    ratings = {field: serializer.validated_data.get(field, getattr(review, field)) for field in (
        "restaurant_rating", "food_rating", "courier_rating", "delivery_speed_rating"
    )}
    overall = Decimal(str(sum(ratings.values()) / 4)).quantize(Decimal("0.01"))
    status_value = Review.STATUS_PENDING if contains_profanity(comment) else (
        Review.STATUS_HIDDEN if review.status == Review.STATUS_HIDDEN else Review.STATUS_PUBLISHED
    )
    with transaction.atomic():
        for field, value in ratings.items():
            setattr(review, field, value)
        review.comment = comment
        review.overall_rating = overall
        review.status = status_value
        review.save()
        _save_photos(request, review)
        recalculate_rating(review.restaurant_id, review.courier_id)
    transaction.on_commit(lambda: analyze_sentiment_async(review.id))
    return Response(ReviewSerializer(review).data)


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def delete_review(request, review_id):
    review = Review.objects.filter(pk=review_id).first()
    if not review:
        return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)
    if review.user_id != request.user.id and request.user.role != "admin":
        return Response({"detail": "You can only delete your own review."}, status=status.HTTP_403_FORBIDDEN)
    restaurant_id, courier_id = review.restaurant_id, review.courier_id
    with transaction.atomic():
        review.delete()
        recalculate_rating(restaurant_id, courier_id)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def restaurant_reviews(request, restaurant_id):
    restaurant = Restaurant.objects.filter(pk=restaurant_id).first()
    if not restaurant:
        return Response({"detail": "Restaurant not found."}, status=status.HTTP_404_NOT_FOUND)
    queryset = Review.objects.filter(restaurant_id=restaurant_id, status=Review.STATUS_PUBLISHED).select_related("user").prefetch_related("photos", "reply")
    rating = request.query_params.get("rating")
    if rating:
        try:
            rating_value = int(rating)
            queryset = queryset.filter(overall_rating__gte=rating_value - 0.5, overall_rating__lte=rating_value + 0.5)
        except ValueError:
            raise ValidationError({"rating": "Rating must be an integer from 1 to 5."})
    if request.query_params.get("with_photos") in ("true", "1"):
        queryset = queryset.filter(photos__isnull=False).distinct()
    if request.query_params.get("negative") in ("true", "1"):
        queryset = queryset.filter(sentiment="negative")
    sort = request.query_params.get("sort", "date")
    if sort == "rating":
        queryset = queryset.order_by("-overall_rating", "-created_at")
    else:
        queryset = queryset.order_by("-created_at")
    page = request.query_params.get("page", 1)
    from rest_framework.pagination import PageNumberPagination
    paginator = PageNumberPagination()
    result = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response(ReviewSerializer(result, many=True).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def restaurant_rating(request, restaurant_id):
    restaurant = Restaurant.objects.filter(pk=restaurant_id).first()
    if not restaurant:
        return Response({"detail": "Restaurant not found."}, status=status.HTTP_404_NOT_FOUND)
    reviews = Review.objects.filter(restaurant_id=restaurant_id, status=Review.STATUS_PUBLISHED)
    aggregate = reviews.aggregate(avg=Avg("overall_rating"), count=Count("id"))
    distribution = {str(stars): reviews.filter(overall_rating__gte=stars, overall_rating__lt=stars + 1).count() for stars in range(1, 6)}
    return Response({
        "average": aggregate["avg"] or 0,
        "reviews_count": aggregate["count"] or 0,
        "distribution": distribution,
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def courier_rating(request, courier_id):
    courier = User.objects.filter(pk=courier_id).first()
    if not courier:
        return Response({"detail": "Courier not found."}, status=status.HTTP_404_NOT_FOUND)
    reviews = Review.objects.filter(courier_id=courier_id, status=Review.STATUS_PUBLISHED)
    aggregate = reviews.aggregate(avg=Avg("courier_rating"), count=Count("id"))
    distribution = {str(stars): reviews.filter(courier_rating=stars).count() for stars in range(1, 6)}
    return Response({
        "average": aggregate["avg"] or 0,
        "reviews_count": aggregate["count"] or 0,
        "distribution": distribution,
    })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def reply_to_review(request, review_id):
    review = Review.objects.select_related("restaurant").filter(pk=review_id).first()
    if not review:
        return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)
    restaurant = review.restaurant
    if request.user.role == "admin":
        allowed = True
    elif request.user.role == "manager":
        allowed = restaurant.owner_id in (None, request.user.id)
    else:
        allowed = False
    if not allowed:
        raise PermissionDenied("Only the restaurant or an administrator can reply.")
    if hasattr(review, "reply"):
        return Response({"detail": "A reply already exists for this review."}, status=status.HTTP_409_CONFLICT)
    text = str(request.data.get("text", "")).strip()
    if not text:
        raise ValidationError({"text": "Reply text is required."})
    if len(text) > 1000:
        raise ValidationError({"text": "Reply text must not exceed 1000 characters."})
    reply = ReviewReply.objects.create(review=review, restaurant=restaurant, text=html.escape(text))
    if review.user_id:
        from users.models import Notification
        Notification.objects.create(
            user=review.user,
            notification_type="system",
            title="Restaurant replied",
            message="The restaurant replied to your review.",
            link=f"/restaurants/{restaurant.id}",
        )
    return Response(ReplySerializer(reply).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def report_review(request, review_id):
    review = Review.objects.filter(pk=review_id).first()
    if not review:
        return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)
    reason = str(request.data.get("reason", "")).strip()
    if not reason:
        raise ValidationError({"reason": "A report reason is required."})
    if len(reason) > 500:
        raise ValidationError({"reason": "Reason must not exceed 500 characters."})
    try:
        with transaction.atomic():
            report = ReviewReport.objects.create(review=review, reporter=request.user, reason=html.escape(reason))
            if review.reports.filter(status=ReviewReport.STATUS_OPEN).count() >= 3:
                review.status = Review.STATUS_PENDING
                review.save(update_fields=["status", "updated_at"])
                recalculate_rating(review.restaurant_id, review.courier_id)
    except IntegrityError:
        return Response({"detail": "You have already reported this review."}, status=status.HTTP_409_CONFLICT)
    return Response({"id": report.id, "status": report.status}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def admin_reviews(request):
    if request.user.role != "admin":
        raise PermissionDenied("Administrator role required.")
    queryset = Review.objects.select_related("user", "restaurant", "courier").prefetch_related("photos", "reply")
    review_status = request.query_params.get("status")
    if review_status:
        if review_status not in dict(Review.STATUS_CHOICES):
            raise ValidationError({"status": "Invalid review status."})
        queryset = queryset.filter(status=review_status)
    if request.query_params.get("negative") in ("true", "1"):
        queryset = queryset.filter(sentiment="negative")
    queryset = queryset.order_by("-created_at")
    from rest_framework.pagination import PageNumberPagination
    paginator = PageNumberPagination()
    result = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response(ReviewSerializer(result, many=True).data)


@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated])
def admin_review_status(request, review_id):
    if request.user.role != "admin":
        raise PermissionDenied("Administrator role required.")
    review = Review.objects.filter(pk=review_id).first()
    if not review:
        return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)
    review_status = request.data.get("status")
    if review_status not in (Review.STATUS_PUBLISHED, Review.STATUS_HIDDEN):
        raise ValidationError({"status": "Status must be published or hidden."})
    with transaction.atomic():
        review.status = review_status
        review.save(update_fields=["status", "updated_at"])
        recalculate_rating(review.restaurant_id, review.courier_id)
    return Response(ReviewSerializer(review).data)
