"""
Dashboard URL routes — /api/v1/dashboard/*
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from dashboard.views import DashboardMetricsViewSet

router = DefaultRouter()
router.register(r"", DashboardMetricsViewSet, basename="dashboard-metrics")

urlpatterns = [
    path("", include(router.urls)),
]
