from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "email", "first_name", "last_name", "password", "is_staff")
        read_only_fields = ("id", "is_staff")
        extra_kwargs = {"password": {"write_only": True, "min_length": 8}}

    def validate_email(self, value):
        value = get_user_model().objects.normalize_email(value)
        users = get_user_model().objects.filter(email__iexact=value)
        if self.instance:
            users = users.exclude(pk=self.instance.pk)
        if users.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        password = attrs.get("password")
        if password:
            user = get_user_model()(
                email=attrs.get("email", getattr(self.instance, "email", "")),
                first_name=attrs.get("first_name", ""),
                last_name=attrs.get("last_name", ""),
            )
            try:
                validate_password(password, user=user)
            except DjangoValidationError as error:
                raise serializers.ValidationError({"password": error.messages})
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return get_user_model().objects.create_user(**validated_data)
        except IntegrityError:
            raise serializers.ValidationError({"email": "Email is already registered."})

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        try:
            with transaction.atomic():
                for name, value in validated_data.items():
                    setattr(instance, name, value)
                if password:
                    instance.set_password(password)
                instance.save()
        except IntegrityError:
            raise serializers.ValidationError({"email": "Email is already registered."})
        return instance


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        attrs["email"] = get_user_model().objects.normalize_email(attrs["email"])
        return super().validate(attrs)
