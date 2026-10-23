from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from books.models import Book
from borrowings.models import Borrowing
from notifications.services import notify_borrowing_created


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
    notify_borrowing_created(borrowing)
    book.refresh_from_db()
    return borrowing


@transaction.atomic
def return_borrowing(borrowing):
    updated = Borrowing.objects.filter(
        pk=borrowing.pk, actual_return_date__isnull=True
    ).update(actual_return_date=timezone.localdate())
    if not updated:
        raise ValidationError("This borrowing has already been returned.")
    Book.objects.filter(pk=borrowing.book_id).update(inventory=F("inventory") + 1)
    borrowing.refresh_from_db()
    borrowing.book.refresh_from_db()
    return borrowing
