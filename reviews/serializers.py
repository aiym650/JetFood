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
    user_id = serializers.IntegerField(read_only=True)
    moderation_reason = serializers.SerializerMethodField()

    def get_moderation_reason(self, obj):
        request = self.context.get("request")
        if request and (request.user.pk == obj.user_id or request.user.role == "admin"):
            return obj.moderation_reason
        return ""

    photos = PhotoSerializer(many=True, read_only=True)
    reply = ReplySerializer(read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id", "user_id", "moderation_reason", "order", "restaurant", "courier", "restaurant_rating", "food_rating",
            "courier_rating", "delivery_speed_rating", "overall_rating", "comment",
            "sentiment", "status", "photos", "reply", "user_name", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user_id", "moderation_reason", "order", "restaurant", "courier", "overall_rating", "sentiment",
            "status", "photos", "reply", "user_name", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        for field in ("restaurant_rating", "food_rating", "courier_rating", "delivery_speed_rating"):
            value = attrs.get(field, getattr(self.instance, field, None))
            if value is not None and (value < 1 or value > 5):
                raise serializers.ValidationError({field: "Rating must be between 1 and 5."})
        comment = attrs.get("comment", getattr(self.instance, "comment", None))
        comment = (comment or "").strip()
        if not 10 <= len(comment) <= 1000:
            raise serializers.ValidationError({"comment": "Comment must contain 10 to 1000 characters."})
        attrs["comment"] = comment
        return attrs
