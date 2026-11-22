from rest_framework import serializers

from .models import Restaurant, RestaurantBranch


class RestaurantBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantBranch
        fields = [
            'id', 'catalog_key', 'address', 'phone', 'opening_time', 'closing_time',
            'working_days', 'is_active', 'delivery_available', 'delivery_info', 'source_url',
        ]
        read_only_fields = fields


class RestaurantSerializer(serializers.ModelSerializer):
    branches = RestaurantBranchSerializer(many=True, read_only=True)

    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'catalog_key', 'description', 'cuisine', 'demo_key', 'address', 'phone', 'image_url',
            'source_url', 'menu_source_url', 'branches',
            'opening_time', 'closing_time', 'working_days', 'is_active',
            'owner', 'avg_rating', 'reviews_count', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'catalog_key', 'demo_key', 'source_url', 'menu_source_url', 'branches',
            'owner', 'avg_rating', 'reviews_count', 'created_at', 'updated_at',
        ]

    def validate_working_days(self, value):
        if not isinstance(value, list) or any(
            not isinstance(day, int) or day < 0 or day > 6 for day in value
        ):
            raise serializers.ValidationError('Use weekday numbers from 0 (Monday) to 6 (Sunday).')
        if len(set(value)) != len(value):
            raise serializers.ValidationError('Weekdays cannot be repeated.')
        return value

    def validate(self, attrs):
        opening_time = attrs.get('opening_time', getattr(self.instance, 'opening_time', None))
        closing_time = attrs.get('closing_time', getattr(self.instance, 'closing_time', None))
        if (opening_time is None) != (closing_time is None):
            raise serializers.ValidationError({
                'closing_time': 'Provide both opening and closing times, or leave both unknown.'
            })
        if opening_time and closing_time and opening_time >= closing_time:
            raise serializers.ValidationError({
                'closing_time': 'Closing time must be later than opening time.'
            })
        return attrs
