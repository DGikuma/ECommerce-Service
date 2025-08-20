import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from core.models import Customer, Category, Product, Order
from core.signals import order_placed

@pytest.fixture
def client_and_user(db):
    user = User.objects.create_user("alice", "alice@example.com", "pwd")
    cust = Customer.objects.create(
        user=user, name="Alice", email="alice@example.com", phone_number="+254700000000"
    )
    client = APIClient()
    client.force_authenticate(user=user)  # bypass OIDC in tests
    return client, user, cust

@pytest.mark.django_db
def test_order_notifications_sms_and_email(monkeypatch, client_and_user):
    client, user, cust = client_and_user

    # Build category tree
    root = Category.objects.create(name="All Products")
    bakery = Category.objects.create(name="Bakery", parent=root)

    # Create product
    p = Product.objects.create(name="Bread", price="120.00", stock_quantity=10)
    p.categories.set([bakery])

    # --- Mocks for SMS and email ---
    sms_calls = {}
    email_calls = {}

    class MockSMS:
        @staticmethod
        def send(message, recipients):
            sms_calls["message"] = message
            sms_calls["recipients"] = recipients
            return {"Message": "Sent"}

    def mock_initialize(user, key):
        return None

    def mock_send_mail(subject, body, from_email, recipient_list, fail_silently=True):
        email_calls["subject"] = subject
        email_calls["body"] = body
        email_calls["from_email"] = from_email
        email_calls["recipient_list"] = recipient_list
        return 1

    monkeypatch.setattr("core.signals.africastalking.initialize", mock_initialize)
    monkeypatch.setattr("core.signals.africastalking.SMS", MockSMS)
    monkeypatch.setattr("core.signals.send_mail", mock_send_mail)

    # Place order via API (ensures serializer fires signal after items)
    resp = client.post(
        "/api/orders/",
        {
            "items": [{"product": p.id, "quantity": 2}],
            # 'customer' field is set in perform_create; safe to omit
        },
        format="json",
    )
    assert resp.status_code == 201
    order_id = resp.data["id"]
    order = Order.objects.get(id=order_id)

    # Assertions
    assert "message" in sms_calls
    assert cust.phone_number in sms_calls["recipients"][0]
    assert f"order #{order.id}" in sms_calls["message"].lower()

    assert email_calls["recipient_list"]
    assert "New Order" in email_calls["subject"]
    assert "Items:" in email_calls["body"]
    assert "Bread x 2" in email_calls["body"]  # formatted from items
