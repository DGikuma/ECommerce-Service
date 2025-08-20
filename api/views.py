from django.db.models import Avg
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import Category, Product, Order
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    ProductWithCategoryPathSerializer,
    OrderSerializer,
    OrderItemReadSerializer,
)
from .permissions import IsAuthenticatedOrReadOnly
from .utils_hierarchy import get_or_create_category_by_path, get_descendant_ids
from .utils import send_sms, send_admin_email

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    def descendants(self, request, pk=None):
        ids = get_descendant_ids(int(pk))
        data = CategorySerializer(Category.objects.filter(id__in=ids), many=True).data
        return Response({"category": pk, "descendants": data})

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=["post"], url_path="bulk-upload")
    def bulk_upload(self, request):
        """Upload a JSON array of products with category_path.
        Example body:
        [
          {"name": "Baguette", "price": 2.50, "stock_quantity": 50, "category_path": ["All Products","Bakery","Bread"]},
          {"name": "Apple", "price": 0.80, "category_path": ["All Products","Produce","Fruits"]}
        ]
        """
        many = isinstance(request.data, list)
        if not many:
            return Response({"detail": "Expected a JSON array."}, status=400)
        created = []
        errors = []
        for idx, item in enumerate(request.data):
            ser = ProductWithCategoryPathSerializer(data=item)
            if ser.is_valid():
                product = ser.save()
                created.append(product.id)
            else:
                errors.append({"index": idx, "errors": ser.errors})
        status_code = status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST
        return Response({"created_ids": created, "errors": errors}, status=status_code)

    @action(detail=False, methods=["get"], url_path="avg-price/(?P<category_id>[^/.]+)")
    def average_price(self, request, category_id=None):
        """Average price for a category INCLUDING all descendants."""
        try:
            root_id = int(category_id)
        except (TypeError, ValueError):
            return Response({"detail": "Invalid category_id"}, status=400)
        ids = get_descendant_ids(root_id)
        avg_price = Product.objects.filter(category_id__in=ids).aggregate(avg=Avg("price"))["avg"]
        return Response({"category_id": root_id, "average_price": avg_price})

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related("items__product").all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        order = serializer.save()
        # notify customer and admin
        try:
            send_sms(order.customer.customer.phone if hasattr(order.customer, "customer") else order.customer.username, f"Your order #{order.id} has been received!")
        except Exception:
            pass
        try:
            send_admin_email(order)
        except Exception:
            pass

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def summary(self, request, pk=None):
        order = self.get_object()
        items = OrderItemReadSerializer(order.items.select_related("product"), many=True).data
        return Response({
            "order_id": order.id,
            "customer": getattr(order.customer, "username", str(order.customer)),
            "created_at": order.created_at,
            "status": order.status,
            "items": items,
            "total_price": sum([i["price"] * i["quantity"] for i in [
                {"price": item.product.price, "quantity": item.quantity} for item in order.items.all()
            ]])
        })

    class ProductViewSet(viewsets.ModelViewSet):
        queryset = Product.objects.select_related("category").all()
        serializer_class = ProductSerializer
        permission_classes = [IsAuthenticatedOrReadOnly]
        parser_classes = [JSONParser, MultiPartParser]

        @action(detail=False, methods=["post"], url_path="bulk-upload")
        def bulk_upload(self, request):
            # (existing JSON bulk upload action remains unchanged)
            many = isinstance(request.data, list)
            if not many:
                return Response({"detail": "Expected a JSON array."}, status=400)
            created = []
            errors = []
            for idx, item in enumerate(request.data):
                ser = ProductWithCategoryPathSerializer(data=item)
                if ser.is_valid():
                    product = ser.save()
                    created.append(product.id)
                else:
                    errors.append({"index": idx, "errors": ser.errors})
            status_code = status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST
            return Response({"created_ids": created, "errors": errors}, status=status_code)

        @action(detail=False, methods=["post"], url_path="upload-csv", parser_classes=[MultiPartParser])
        def upload_csv(self, request):
            """Upload CSV file with columns: name, price, category_path[, description, stock_quantity].
            Accepts multipart/form-data with `file` field.
            """
            file_obj = request.data.get("file")
            if not file_obj:
                return Response({"detail": "Missing 'file' field."}, status=400)
            result = import_products_csv(file_obj)
            http_status = status.HTTP_201_CREATED if result.get("created_ids") else status.HTTP_400_BAD_REQUEST
            return Response(result, status=http_status)
