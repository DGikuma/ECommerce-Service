from rest_framework import serializers
from django.db import transaction
from .models import Category, Product, Order, OrderItem

class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Category
        fields = ["id", "name", "parent"]

class CategoryPathSerializer(serializers.Serializer):
    """For bulk upload: specify categories by a path of names, e.g. ["All Products", "Bakery", "Bread"]."""
    path = serializers.ListField(child=serializers.CharField(), allow_empty=False)

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "category", "stock_quantity"]

class ProductWithCategoryPathSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = serializers.IntegerField(required=False, min_value=0, default=0)
    category_path = serializers.ListField(child=serializers.CharField(), allow_empty=False)

    def create(self, validated_data):
        path = validated_data.pop("category_path")
        category = get_or_create_category_by_path(path)
        return Product.objects.create(category=category, **validated_data)

class OrderItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product", "quantity"]

class OrderItemReadSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    price = serializers.DecimalField(source="product.price", max_digits=10, decimal_places=2, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "price", "quantity", "total_price"]

    def get_total_price(self, obj):
        return obj.product.price * obj.quantity

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemWriteSerializer(many=True)
    total_price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "customer", "created_at", "status", "items", "total_price"]
        read_only_fields = ["customer", "created_at", "status", "total_price"]

    def get_total_price(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.select_related("product"))

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items")
        customer = self.context["request"].user
        order = Order.objects.create(customer=customer)
        OrderItem.objects.bulk_create([
            OrderItem(order=order, **item) for item in items_data
        ])
        return order