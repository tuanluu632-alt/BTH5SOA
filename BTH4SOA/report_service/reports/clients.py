import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from rest_framework.exceptions import APIException


class UpstreamUnavailable(APIException):
    status_code = 503
    default_detail = "Không kết nối được dịch vụ dữ liệu báo cáo."


def request_json(url, token, method="GET"):
    request = Request(url, headers={"Authorization": f"Bearer {token}"}, method=method)
    try:
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise UpstreamUnavailable("Dịch vụ nguồn từ chối token; hãy đăng nhập lại.") from exc
        raise UpstreamUnavailable(f"Dịch vụ nguồn trả HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise UpstreamUnavailable("Không kết nối được hoặc nhận JSON không hợp lệ từ dịch vụ nguồn.") from exc


def get_orders(token):
    return request_json(f"{settings.ORDER_SERVICE_URL.rstrip('/')}/orders", token)


def get_products(token):
    return request_json(settings.PRODUCT_SERVICE_URL, token)
