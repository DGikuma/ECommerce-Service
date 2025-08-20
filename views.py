from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Product, Category, Order
from .serializers import *
from .utils import send_sms, send_admin_email

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @action(detail=False, methods=['get'], url_path='avg-price/(?P<category_id>[^/.]+)')
    def average_price(self, request, category_id=None):
        products = Product.objects.filter(category_id=category_id)
        avg_price = products.aggregate(models.Avg('price'))['price__avg']
        return Response({'average_price': avg_price})

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def perform_create(self, serializer):
        order = serializer.save(customer=self.request.user)
        send_sms(order.customer.phone, f"Your order #{order.id} has been received!")
        send_admin_email(order)