
import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_confirmation_email(self, order_id, user_email):
    """
    Asynchronous task to send an order confirmation email.
    Triggered via core/signals.py when an order is created.
    """
    try:
        subject = f"Order Confirmation #{order_id}"
        message = (
            f"Thank you for your purchase!\n\n"
            f"Your order with ID {order_id} has been received and is being processed."
        )
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")

        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[user_email],
            fail_silently=False,
        )
        logger.info("✅ Sent order confirmation email for order_id=%s", order_id)
        return True

    except Exception as exc:
        logger.error("❌ Failed to send order confirmation email for order_id=%s: %s", order_id, exc)
        raise self.retry(exc=exc)
