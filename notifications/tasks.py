from celery import shared_task
from django.db import transaction
from django.utils import timezone

from notifications.models import BorrowingNotification
from notifications.telegram import TelegramDeliveryError, is_configured, send_message


@shared_task(
    bind=True,
    autoretry_for=(TelegramDeliveryError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def deliver_notification(self, notification_id):
    with transaction.atomic():
        notification = (
            BorrowingNotification.objects.select_for_update(of=("self",))
            .select_related("borrowing__book", "borrowing__user")
            .filter(pk=notification_id)
            .first()
        )
        if notification is None or notification.sent_at is not None:
            return False
        borrowing = notification.borrowing
        text = (
            f"New borrowing #{borrowing.pk}\n"
            f"Book: {borrowing.book.title} by {borrowing.book.author}\n"
            f"Reader: {borrowing.user.email}\n"
            f"Borrowed: {borrowing.borrow_date.isoformat()}\n"
            f"Expected return: {borrowing.expected_return_date.isoformat()}"
        )
        if not send_message(text):
            return False
        notification.sent_at = timezone.now()
        notification.save(update_fields=("sent_at",))
    return True


@shared_task
def retry_pending_notifications():
    if not is_configured():
        return 0
    ids = list(
        BorrowingNotification.objects.filter(sent_at__isnull=True).values_list(
            "id", flat=True
        )[:100]
    )
    for notification_id in ids:
        deliver_notification.delay(notification_id)
    return len(ids)
