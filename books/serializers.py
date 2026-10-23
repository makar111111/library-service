from rest_framework import serializers

from books.models import Book


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ("id", "title", "author", "cover", "inventory", "daily_fee")

    def update(self, instance, validated_data):
        for name, value in validated_data.items():
            setattr(instance, name, value)
        # A metadata edit must not overwrite stock changed by a borrowing or
        # return after this instance was loaded.
        instance.save(update_fields=validated_data.keys())
        instance.refresh_from_db()
        return instance
