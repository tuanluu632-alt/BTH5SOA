from django.urls import path
from .views import OrderListCreateView, OrderDetailView, OrderItemListCreateView, OrderItemDetailView

urlpatterns = [
    path("orders", OrderListCreateView.as_view(), name="order-list"),
    path("orders/<int:pk>", OrderDetailView.as_view(), name="order-detail"),
    path("order_items", OrderItemListCreateView.as_view(), name="order-item-list"),
    path("order_items/<int:pk>", OrderItemDetailView.as_view(), name="order-item-detail"),
]
