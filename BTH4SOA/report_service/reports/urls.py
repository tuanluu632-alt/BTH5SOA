from django.urls import path

from .views import OrderReportView, ProductReportView, ReportSnapshotListCreateView, SummaryReportView

urlpatterns = [
    path("reports/summary", SummaryReportView.as_view(), name="report-summary"),
    path("reports/products", ProductReportView.as_view(), name="report-products"),
    path("reports/orders", OrderReportView.as_view(), name="report-orders"),
    path("reports/snapshots", ReportSnapshotListCreateView.as_view(), name="report-snapshots"),
]
