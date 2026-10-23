import logging
from functools import partial

from django.db import transaction
from kombu.exceptions import OperationalError

from notifications.models import BorrowingNotification
from notifications.tasks import deliver_notification
from notifications.telegram import is_configured

logger = logging.getLogger(__name__)


def enqueue_notification(notification_id):
    if not is_configured():
        return
    try:
        deliver_notification.delay(notification_id)
    except OperationalError:
        logger.warning("Queue unavailable; notification remains pending for retry.")


def notify_borrowing_created(borrowing):
    notification = BorrowingNotification.objects.create(borrowing=borrowing)
    transaction.on_commit(partial(enqueue_notification, notification.pk))
