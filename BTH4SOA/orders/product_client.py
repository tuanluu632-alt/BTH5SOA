from decimal import Decimal, InvalidOperation
from django.conf import settings
from rest_framework.exceptions import APIException, ValidationError
from .http_client import request_json

class ProductServiceUnavailable(APIException):
    status_code = 503
    default_detail = "Không kết nối được dịch vụ quản lý sản phẩm."
    default_code = "product_service_unavailable"

def get_product(product_id, token):
    url = settings.PRODUCT_SERVICE_URL.format(id=product_id)
    try:
        status, data = request_json(url, headers={"Authorization": f"Bearer {token}"}, timeout=4)
    except ConnectionError as exc:
        raise ProductServiceUnavailable() from exc
    if status == 404:
        raise ValidationError({"product_id": f"Không tìm thấy sản phẩm {product_id}."})
    if status in (401, 403):
        raise ProductServiceUnavailable("Product service từ chối token; kiểm tra cấu hình xác thực.")
    if status < 200 or status >= 300:
        raise ProductServiceUnavailable(f"Product service trả về HTTP {status}.")
    try:
        product = data.get("product", data)
        name = product["name"]
        price = Decimal(str(product["price"]))
        cost_price = Decimal(str(product["cost_price"])) if product.get("cost_price") is not None else None
        stock = int(product["quantity"])
    except (ValueError, TypeError, KeyError, InvalidOperation) as exc:
        raise ProductServiceUnavailable("Dữ liệu sản phẩm cần có name, price và quantity.") from exc
    return {"id": product_id, "name": str(name), "price": price, "cost_price": cost_price, "quantity": stock}

def validate_stock(product_id, quantity, token):
    product = get_product(product_id, token)
    if product["quantity"] < quantity:
        raise ValidationError({"quantity": f"Sản phẩm {product['name']} chỉ còn {product['quantity']} sản phẩm."})
    return product
