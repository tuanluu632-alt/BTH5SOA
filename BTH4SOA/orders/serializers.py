from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from .models import Order, OrderItem
from .product_client import validate_stock

class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = OrderItem
        fields = ["id", "order", "product_id", "product_name", "quantity", "unit_price", "unit_cost", "total_price"]
        read_only_fields = ["id", "order", "product_name", "unit_price", "unit_cost", "total_price"]

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, required=False)
    class Meta:
        model = Order
        fields = ["id", "customer_name", "customer_email", "total_amount", "status", "created_at", "updated_at", "items"]
        read_only_fields = ["id", "total_amount", "status", "created_at", "updated_at"]

    @transaction.atomic
    def create(self, validated_data):
        lines = validated_data.pop("items", [])
        if not lines:
            raise serializers.ValidationError({"items": "Đơn hàng phải có ít nhất một mặt hàng."})
        token = self.context["request"].auth
        requested = {}
        for line in lines:
            requested[line["product_id"]] = requested.get(line["product_id"], 0) + line["quantity"]
        products_by_id = {product_id: validate_stock(product_id, quantity, token)
                          for product_id, quantity in requested.items()}
        order = Order.objects.create(**validated_data)
        total = Decimal("0.00")
        for line in lines:
            product = products_by_id[line["product_id"]]
            line_total = product["price"] * line["quantity"]
            OrderItem.objects.create(order=order, product_id=product["id"], product_name=product["name"],
                                     quantity=line["quantity"], unit_price=product["price"],
                                     unit_cost=product["cost_price"], total_price=line_total)
            total += line_total
        order.total_amount = total
        order.save(update_fields=["total_amount", "updated_at"])
        return order

class OrderItemCreateSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = OrderItem
        fields = ["id", "order", "product_id", "product_name", "quantity", "unit_price", "unit_cost", "total_price"]
        read_only_fields = ["id", "product_name", "unit_price", "unit_cost", "total_price"]

    def create(self, validated_data):
        product = validate_stock(validated_data["product_id"], validated_data["quantity"], self.context["request"].auth)
        validated_data["product_name"] = product["name"]
        validated_data["unit_price"] = product["price"]
        validated_data["unit_cost"] = product["cost_price"]
        validated_data["total_price"] = product["price"] * validated_data["quantity"]
        item = super().create(validated_data)
        recalculate(item.order)
        return item

    def update(self, instance, validated_data):
        product_id = validated_data.get("product_id", instance.product_id)
        quantity = validated_data.get("quantity", instance.quantity)
        product = validate_stock(product_id, quantity, self.context["request"].auth)
        instance.product_id = product["id"]
        instance.product_name = product["name"]
        instance.quantity = quantity
        instance.unit_price = product["price"]
        instance.unit_cost = product["cost_price"]
        instance.total_price = product["price"] * quantity
        instance.save()
        recalculate(instance.order)
        return instance

def recalculate(order):
    from django.db.models import Sum
    order.total_amount = order.items.aggregate(value=Sum("total_price"))["value"] or Decimal("0.00")
    order.save(update_fields=["total_amount", "updated_at"])
