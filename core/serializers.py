# core/serializers.py
from rest_framework import serializers
from .models import Category, Product, Order, OrderItem
from .signals import order_placed  # <-- import the signal

class CategorySerializer(serializers.ModelSerializer):
    parent_id = serializers.IntegerField(required=False, allow_null=True)
    class Meta:
        model = Category
        fields = ["id", "name", "parent_id"]

class ProductSerializer(serializers.ModelSerializer):
    category_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "stock_quantity", "category_ids"]

    def create(self, validated_data):
        ids = validated_data.pop("category_ids", [])
        product = Product.objects.create(**validated_data)
        product.categories.set(Category.objects.filter(id__in=ids))
        return product

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product", "quantity"]

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ["id", "customer", "created_at", "status", "items"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        order = Order.objects.create(**validated_data)
        for it in items:
            OrderItem.objects.create(order=order, **it)
        # Now that items exist, fire order_placed
        order_placed.send(sender=Order, instance=order)
        return order
