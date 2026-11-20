from django.conf import settings
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .clients import request_json


class ServiceUser:
    is_authenticated = True

    def __init__(self, user_id=None, username=None):
        self.id = user_id
        self.username = username or "authenticated-user"


class ReportServiceAuthentication(BaseAuthentication):
    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts:
            return None
        if parts[0].lower() != b"bearer" or len(parts) != 2:
            raise AuthenticationFailed("Authorization phải có dạng Bearer <token>.")
        token = parts[1].decode("utf-8")
        try:
            payload = request_json(settings.AUTH_SERVICE_URL, token, method="POST")
        except Exception as exc:
            raise AuthenticationFailed("Không xác thực được token với Auth Service bài 2.") from exc
        if payload.get("valid") is not True:
            raise AuthenticationFailed("Token không hợp lệ hoặc đã hết hạn.")
        return ServiceUser(payload.get("user_id"), payload.get("username")), token
