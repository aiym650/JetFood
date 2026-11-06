from rest_framework import serializers

from .models import Restaurant


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'description', 'address', 'phone', 'image_url',
            'opening_time', 'closing_time', 'working_days', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

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
        if opening_time and closing_time and opening_time >= closing_time:
            raise serializers.ValidationError({
                'closing_time': 'Closing time must be later than opening time.'
            })
        return attrs
