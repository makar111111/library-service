from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import ValidationError

from books.models import Book
from borrowings.models import Borrowing


@transaction.atomic
def create_borrowing(*, book, user, expected_return_date):
    # The condition and decrement execute as one SQL statement, including under
    # concurrent requests. Reading stock and then saving it would lose updates.
    updated = Book.objects.filter(pk=book.pk, inventory__gt=0).update(
        inventory=F("inventory") - 1
    )
    if not updated:
        raise ValidationError({"book": "No copies of this book are available."})
    borrowing = Borrowing.objects.create(
        book=book, user=user, expected_return_date=expected_return_date
    )
    book.refresh_from_db()
    return borrowing
