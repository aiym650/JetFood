from rest_framework import serializers
from .models import DeliveryAddress, User, Notification

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'phone', 'address', 'created_at', 'updated_at']
        read_only_fields = ['id', 'role', 'created_at', 'updated_at']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'phone', 'role']
        read_only_fields = ['role']

    def create(self, validated_data):
        validated_data.pop('role', None)
        user = User.objects.create_user(**validated_data)
        return user


class AdminUserCreateSerializer(UserRegistrationSerializer):
    class Meta(UserRegistrationSerializer.Meta):
        read_only_fields = []

    def create(self, validated_data):
        role = validated_data.pop('role', 'customer')
        return User.objects.create_user(**validated_data, role=role)

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        from django.contrib.auth import authenticate
        user = authenticate(username=attrs['username'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('Invalid credentials')
        attrs['user'] = user
        return attrs

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class AccountDeletionSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)


class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = [
            'id', 'label', 'recipient_name', 'phone', 'address_line', 'city',
            'postal_code', 'instructions', 'is_default', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 'is_read', 'link', 'created_at']
        read_only_fields = ['id', 'created_at']
