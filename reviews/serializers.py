from rest_framework import serializers
from .models import Review, ReviewPhoto, ReviewReply


class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewPhoto
        fields = ["id", "url", "created_at"]


class ReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewReply
        fields = ["id", "text", "created_at"]
        read_only_fields = ["id", "created_at"]


class ReviewSerializer(serializers.ModelSerializer):
    photos = PhotoSerializer(many=True, read_only=True)
    reply = ReplySerializer(read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id", "order", "restaurant", "courier", "restaurant_rating", "food_rating",
            "courier_rating", "delivery_speed_rating", "overall_rating", "comment",
            "sentiment", "status", "photos", "reply", "user_name", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "order", "restaurant", "courier", "overall_rating", "sentiment",
            "status", "photos", "reply", "user_name", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        for field in ("restaurant_rating", "food_rating", "courier_rating", "delivery_speed_rating"):
            value = attrs.get(field, getattr(self.instance, field, None))
            if value is not None and (value < 1 or value > 5):
                raise serializers.ValidationError({field: "Rating must be between 1 and 5."})
        comment = attrs.get("comment", getattr(self.instance, "comment", None))
        if comment is not None and len(comment) > 1000:
            raise serializers.ValidationError({"comment": "Comment must not exceed 1000 characters."})
        return attrs
