from io import BytesIO
import csv
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from api.models import Category, Product, Order


class BaseAuthMixin:
    def login_staff(self):
        self.staff = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.client.login(username="staff", password="pass")

    def login_user(self):
        self.user = User.objects.create_user(username="alice", password="password123")
        self.client.login(username="alice", password="password123")


class ProductCSVUploadTests(APITestCase, BaseAuthMixin):
    def setUp(self):
        self.client = APIClient()

    def _csv_buffer(self, rows):
        buf = BytesIO()
        writer = csv.DictWriter(buf, fieldnames=["name","price","category_path","description","stock_quantity"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        buf.seek(0)
        return buf

    def test_csv_template_requires_staff(self):
        self.login_user()
        url = reverse("product-csv-template")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_csv_requires_staff(self):
        self.login_user()
        url = reverse("product-upload-csv")
        res = self.client.post(url, {"file": self._csv_buffer([])}, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_csv_template_download_by_staff(self):
        self.login_staff()
        url = reverse("product-csv-template")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"name,price,category_path,description,stock_quantity", res.content)

    def test_upload_csv_creates_products_by_staff(self):
        self.login_staff()
        url = reverse("product-upload-csv")
        data = [
            {"name":"Baguette","price":"2.50","category_path":"All Products>Bakery>Bread","description":"Fresh","stock_quantity":"10"},
            {"name":"Apple","price":"0.80","category_path":"All Products/Produce/Fruits","description":"Gala","stock_quantity":"100"},
        ]
        buf = self._csv_buffer(data)
        res = self.client.post(url, {"file": buf}, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)
        self.assertTrue(Category.objects.filter(name="Bread").exists())
        self.assertTrue(Category.objects.filter(name="Fruits").exists())


class ProductAveragePriceTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        root = Category.objects.create(name="All Products")
        bakery = Category.objects.create(name="Bakery", parent=root)
        bread = Category.objects.create(name="Bread", parent=bakery)
        Product.objects.create(name="Baguette", price=Decimal("2.00"), category=bread)
        Product.objects.create(name="Sourdough", price=Decimal("4.00"), category=bread)
        self.category_id = bakery.id

    def test_average_includes_descendants(self):
        url = reverse("product-average-price", kwargs={"category_id": self.category_id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertAlmostEqual(Decimal(str(res.data["average_price"])), Decimal("3.00"))


class OrderFlowTests(APITestCase, BaseAuthMixin):
    def setUp(self):
        self.client = APIClient()
        root = Category.objects.create(name="All Products")
        produce = Category.objects.create(name="Produce", parent=root)
        fruits = Category.objects.create(name="Fruits", parent=produce)
        self.apple = Product.objects.create(name="Apple", price=Decimal("1.50"), category=fruits)

    def test_create_order_requires_auth(self):
        res = self.client.post(reverse("order-list"), {"items": [{"product": self.apple.id, "quantity": 2}]}, format='json')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("api.utils.send_sms", return_value=True)
    @patch("api.utils.django_send_mail", return_value=1)
    def test_create_order_as_user_sends_notifications(self, mock_email, mock_sms):
        self.login_user()
        res = self.client.post(reverse("order-list"), {"items": [{"product": self.apple.id, "quantity": 2}]}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        # ensure notification helpers were called
        self.assertTrue(mock_sms.called)
        self.assertTrue(mock_email.called)
