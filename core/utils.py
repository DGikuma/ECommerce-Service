import africastalking
from django.core.mail import send_mail
from django.conf import settings

africastalking.initialize(username='sandbox', api_key='your_api_key')
sms = africastalking.SMS

def send_sms(phone_number, message):
    sms.send(message, [phone_number])

def send_admin_email(order):
    body = f"New order placed:\nCustomer: {order.customer}\nItems:\n"
    for item in order.items.all():
        body += f"- {item.product.name} x {item.quantity}\n"
    send_mail("New Order Alert", body, settings.DEFAULT_FROM_EMAIL, ['admin@example.com'])