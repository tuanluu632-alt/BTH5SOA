from decimal import Decimal

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from .clients import get_orders, get_products
from .models import ReportSnapshot


ZERO = Decimal("0.00")


def _period(request):
    start_raw = request.query_params.get("start_date")
    end_raw = request.query_params.get("end_date")
    start = parse_date(start_raw) if start_raw else None
    end = parse_date(end_raw) if end_raw else None
    if start_raw and start is None:
        raise ValidationError({"start_date": "Dùng định dạng YYYY-MM-DD."})
    if end_raw and end is None:
        raise ValidationError({"end_date": "Dùng định dạng YYYY-MM-DD."})
    if start and end and start > end:
        raise ValidationError({"date_range": "start_date phải trước hoặc bằng end_date."})
    return start, end


def _created_date(order):
    value = parse_datetime(order.get("created_at", ""))
    if value is None:
        return None
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return timezone.localtime(value).date()


def _in_period(order, start, end):
    created = _created_date(order)
    return created is not None and (start is None or created >= start) and (end is None or created <= end)


def _decimal(value):
    try:
        return Decimal(str(value))
    except Exception:
        return ZERO


def _sources(token):
    orders = get_orders(token)
    products = get_products(token)
    if not isinstance(orders, list) or not isinstance(products, list):
        raise ValidationError("Dữ liệu nguồn cần trả về danh sách JSON.")
    return orders, products


def _completed_orders(orders, start, end):
    return [order for order in orders
            if order.get("status") == "completed" and _in_period(order, start, end)]


def _cost_for_orders(orders):
    total = ZERO
    complete = True
    for order in orders:
        for item in order.get("items", []):
            unit_cost = item.get("unit_cost")
            if unit_cost is None:
                complete = False
            else:
                total += _decimal(unit_cost) * int(item.get("quantity", 0))
    return (total if complete else None), complete


def _summary_data(orders, products, start, end):
    completed = _completed_orders(orders, start, end)
    revenue = sum((_decimal(order.get("total_amount")) for order in completed), ZERO)
    sold = sum(int(item.get("quantity", 0)) for order in completed for item in order.get("items", []))
    cost, cost_complete = _cost_for_orders(completed)
    inventory = sum(int(product.get("quantity", 0)) for product in products)
    return {
        "period": {"start_date": start, "end_date": end},
        "product_count": len(products),
        "inventory_quantity": inventory,
        "completed_order_count": len(completed),
        "sold_quantity": sold,
        "revenue": revenue,
        "cost": cost,
        "profit": revenue - cost if cost_complete else None,
        "cost_data_complete": cost_complete,
    }


class SummaryReportView(APIView):
    def get(self, request):
        start, end = _period(request)
        orders, products = _sources(request.auth)
        return Response(_summary_data(orders, products, start, end))


class ReportSnapshotListCreateView(APIView):
    def get(self, request):
        snapshots = ReportSnapshot.objects.all()[:100]
        return Response([{
            "id": row.id, "start_date": row.start_date, "end_date": row.end_date,
            "generated_at": row.generated_at, "report": row.payload,
        } for row in snapshots])

    def post(self, request):
        start, end = _period(request)
        orders, products = _sources(request.auth)
        payload = _summary_data(orders, products, start, end)
        snapshot = ReportSnapshot.objects.create(start_date=start, end_date=end, payload=payload)
        return Response({
            "id": snapshot.id, "generated_at": snapshot.generated_at, "report": payload,
        }, status=status.HTTP_201_CREATED)


class ProductReportView(APIView):
    def get(self, request):
        start, end = _period(request)
        orders, products = _sources(request.auth)
        product_rows = {int(product["id"]): {
            "product_id": int(product["id"]), "product_name": product.get("name"),
            "inventory_quantity": int(product.get("quantity", 0)), "sold_quantity": 0,
            "revenue": ZERO, "cost": ZERO, "cost_data_complete": True,
        } for product in products}
        for order in _completed_orders(orders, start, end):
            for item in order.get("items", []):
                product_id = int(item["product_id"])
                row = product_rows.setdefault(product_id, {
                    "product_id": product_id, "product_name": item.get("product_name"),
                    "inventory_quantity": None, "sold_quantity": 0, "revenue": ZERO,
                    "cost": ZERO, "cost_data_complete": True,
                })
                quantity = int(item.get("quantity", 0))
                row["sold_quantity"] += quantity
                row["revenue"] += _decimal(item.get("total_price"))
                if item.get("unit_cost") is None:
                    row["cost_data_complete"] = False
                else:
                    row["cost"] += _decimal(item["unit_cost"]) * quantity
        rows = []
        for row in product_rows.values():
            if not row["cost_data_complete"]:
                row["cost"] = None
                row["profit"] = None
            else:
                row["profit"] = row["revenue"] - row["cost"]
            del row["cost_data_complete"]
            rows.append(row)
        return Response({"period": {"start_date": start, "end_date": end}, "results": rows})


class OrderReportView(APIView):
    def get(self, request):
        start, end = _period(request)
        orders, _ = _sources(request.auth)
        rows = []
        for order in orders:
            if not _in_period(order, start, end):
                continue
            completed = order.get("status") == "completed"
            items = order.get("items", [])
            cost, cost_complete = _cost_for_orders([order]) if completed else (ZERO, True)
            revenue = _decimal(order.get("total_amount")) if completed else ZERO
            rows.append({
                "order_id": order.get("id"), "created_at": order.get("created_at"),
                "customer_name": order.get("customer_name"), "status": order.get("status"),
                "sold_quantity": sum(int(item.get("quantity", 0)) for item in items) if completed else 0,
                "revenue": revenue, "cost": cost,
                "profit": revenue - cost if cost_complete else None,
                "cost_data_complete": cost_complete,
            })
        return Response({"period": {"start_date": start, "end_date": end}, "results": rows})
