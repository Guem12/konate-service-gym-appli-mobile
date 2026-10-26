from django.urls import path

from reports.views import DashboardView, ExportCSVView, ReportsView

urlpatterns = [
    path("admin/dashboard", DashboardView.as_view(), name="admin-dashboard"),
    path("admin/reports", ReportsView.as_view(), name="admin-reports"),
    path("admin/reports/export", ExportCSVView.as_view(), name="admin-reports-export"),
]
