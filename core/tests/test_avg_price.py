import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from core.models import Customer, Category, Product

@pytest.mark.django_db
def test_avg_price_includes_descendants():
    user = User.objects.create_user("bob", "bob@example.com", "pwd")
    Customer.objects.create(user=user, name="Bob", email="bob@example.com", phone_number="+254700000001")
    client = APIClient()
    client.force_authenticate(user=user)

    root = Category.objects.create(name="All Products")
    fruits = Category.objects.create(name="Fruits", parent=root)
    apples = Category.objects.create(name="Apples", parent=fruits)

    p1 = Product.objects.create(name="Red Apple", price="100.00", stock_quantity=5)
    p1.categories.set([apples])
    p2 = Product.objects.create(name="Green Apple", price="200.00", stock_quantity=5)
    p2.categories.set([apples])

    resp = client.get(f"/api/products/avg-price/?category_id={root.id}")
    assert resp.status_code == 200
    # (100 + 200)/2 = 150
    assert float(resp.data["average_price"]) == 150.0
