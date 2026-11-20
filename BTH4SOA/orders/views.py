from django.db import transaction
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderItemSerializer, OrderItemCreateSerializer, recalculate

class OrderListCreateView(generics.ListCreateAPIView):
    queryset = Order.objects.prefetch_related("items").all().order_by("-created_at")
    serializer_class = OrderSerializer

class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.prefetch_related("items").all()
    serializer_class = OrderSerializer
    http_method_names = ["get", "put", "patch", "delete", "head", "options"]

    def update(self, request, *args, **kwargs):
        order = self.get_object()
        if set(request.data.keys()) - {"status"}:
            raise ValidationError("Chỉ cho phép cập nhật trạng thái đơn hàng tại endpoint này.")
        if request.data.get("status") not in Order.Status.values:
            raise ValidationError({"status": f"Trạng thái hợp lệ: {', '.join(Order.Status.values)}."})
        order.status = request.data["status"]
        order.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(order).data)

class OrderItemListCreateView(generics.ListCreateAPIView):
    queryset = OrderItem.objects.select_related("order").all().order_by("id")
    def get_serializer_class(self):
        return OrderItemCreateSerializer if self.request.method == "POST" else OrderItemSerializer
    def perform_create(self, serializer):
        order = serializer.validated_data["order"]
        if order.status != Order.Status.PENDING:
            raise ValidationError({"order": "Chỉ thêm mặt hàng vào đơn hàng pending."})
        serializer.save()

class OrderItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OrderItem.objects.select_related("order").all()
    serializer_class = OrderItemCreateSerializer
    def update(self, request, *args, **kwargs):
        item = self.get_object()
        if item.order.status != Order.Status.PENDING:
            raise ValidationError("Chỉ cập nhật mặt hàng trong đơn hàng pending.")
        if set(request.data.keys()) - {"product_id", "quantity"}:
            raise ValidationError("Chỉ cho phép cập nhật product_id và quantity.")
        serializer = self.get_serializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    def perform_destroy(self, instance):
        if instance.order.status != Order.Status.PENDING:
            raise ValidationError("Chỉ xóa mặt hàng trong đơn hàng pending.")
        order = instance.order
        with transaction.atomic():
            instance.delete()
            recalculate(order)
