# core/signals.py
from django.conf import settings
from django.core.mail import send_mail
from django.dispatch import Signal, receiver
import africastalking

# Custom signal fired after an order (and its items) are fully created
order_placed = Signal()  # args: instance

@receiver(order_placed)
def handle_order_placed(sender, instance, **kwargs):
    """
    Sends SMS to the customer and an email to the admin with order details.
    """
    customer = instance.customer
    phone = getattr(customer, "phone_number", None)
    total = instance.total_price
    item_lines = []
    for it in instance.items.select_related("product"):
        item_lines.append(f"- {it.product.name} x {it.quantity} = {it.total_price}")

    # --- SMS to customer (Africa's Talking sandbox) ---
    # NOTE: In sandbox, your recipient must be registered on the sandbox tester.
    try:
        africastalking.initialize(
            settings.AFRICASTALKING_USERNAME,
            settings.AFRICASTALKING_API_KEY
        )
        if phone:
            msg = f"Hi {customer.name}, your order #{instance.id} is confirmed. Total: {total}."
            africastalking.SMS.send(msg, [phone])
    except Exception:
        # In production, log this (don’t raise)
        pass

    # --- Email to admin ---
    try:
        subject = f"New Order #{instance.id}"
        body = (
            f"Customer: {customer.name} ({customer.email})\n"
            f"Phone: {customer.phone_number}\n"
            f"Order ID: {instance.id}\n"
            f"Status: {instance.status}\n"
            f"Total: {total}\n"
            f"Items:\n" + "\n".join(item_lines)
        )
        send_mail(
            subject,
            body,
            settings.EMAIL_HOST_USER,
            [settings.ADMIN_NOTIFICATION_EMAIL],
            fail_silently=True,
        )
    except Exception:
        pass