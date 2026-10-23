from rest_framework import serializers
from django.utils import timezone

from books.models import Book
from books.serializers import BookSerializer
from borrowings.models import Borrowing
from borrowings.services import create_borrowing


class BorrowingReadSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
            "is_active",
        )
        read_only_fields = fields


class BorrowingCreateSerializer(serializers.ModelSerializer):
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())

    class Meta:
        model = Borrowing
        fields = ("id", "book", "expected_return_date")
        read_only_fields = ("id",)

    def validate_expected_return_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("Return date cannot be in the past.")
        return value

    def create(self, validated_data):
        return create_borrowing(**validated_data)
