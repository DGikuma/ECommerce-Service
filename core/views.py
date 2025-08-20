from django.db.models import Avg
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Product, Order, Customer
from .serializers import CategorySerializer, ProductSerializer, OrderSerializer

class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and hasattr(request.user, "customer_profile"))

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="avg-price")
    def avg_price(self, request):
        """
        ?category_id=<id>  -> average price for that category + ALL descendants
        """
        cid = request.query_params.get("category_id")
        if not cid:
            return Response({"detail": "category_id is required"}, status=400)
        try:
            cat = Category.objects.get(id=cid)
        except Category.DoesNotExist:
            return Response({"detail": "category not found"}, status=404)

        descendants = cat.get_descendants(include_self=True).values_list("id", flat=True)
        avg = Product.objects.filter(categories__in=descendants).aggregate(avg=Avg("price"))["avg"]
        return Response({"category": cat.name, "average_price": avg})

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().select_related("customer")
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def perform_create(self, serializer):
        # Always bind to the authenticated user's customer profile
        customer = Customer.objects.get(user=self.request.user)
        serializer.save(customer=customer)
