"""
Dashboard metrics serializers — read-only output shapes.
"""

from rest_framework import serializers


class TrendPointSerializer(serializers.Serializer):
    """A single data point in a daily trend."""

    date = serializers.DateField()
    count = serializers.IntegerField(default=0)


class RevenueTrendPointSerializer(serializers.Serializer):
    """A single data point in a daily revenue trend."""

    date = serializers.DateField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)


class AppointmentsByStatusSerializer(serializers.Serializer):
    """Appointment counts grouped by status."""

    total = serializers.IntegerField()
    by_status = serializers.DictField(child=serializers.IntegerField())


class MonthlyAppointmentsSerializer(serializers.Serializer):
    """Monthly appointment summary."""

    total = serializers.IntegerField()
    completion_rate = serializers.FloatField(default=0.0)


class UpcomingAppointmentSerializer(serializers.Serializer):
    """Lightweight appointment for dashboard preview list."""

    id = serializers.UUIDField()
    patient_name = serializers.CharField()
    date = serializers.DateField()
    time = serializers.CharField()
    type_name = serializers.CharField()
    status = serializers.CharField()


class DashboardMetricsSerializer(serializers.Serializer):
    """
    Complete dashboard metrics snapshot.

    All fields are aggregated from appointment, invoice, patient, and inventory
    data filtered by the authenticated user's clinic.
    """

    appointments_today = serializers.IntegerField()
    appointments_this_week = AppointmentsByStatusSerializer()
    appointments_this_month = MonthlyAppointmentsSerializer()
    revenue_this_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    revenue_trend = RevenueTrendPointSerializer(many=True)
    appointments_trend = TrendPointSerializer(many=True)
    patients_total = serializers.IntegerField()
    patients_new_this_month = serializers.IntegerField()
    low_stock_count = serializers.IntegerField()
    expiring_soon_count = serializers.IntegerField()
    upcoming_appointments = UpcomingAppointmentSerializer(many=True)
