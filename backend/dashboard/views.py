"""
Dashboard metrics ViewSet.

Single action `metrics` returns all KPIs filtered by the authenticated user's clinic.
No models owned — queries external apps (appointments, invoicing, patients, inventory).
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from appointments.models import Appointment
from inventory.services.stock_service import get_expiring_items, get_low_stock_items
from invoicing.models import Invoice
from patients.models import Patient


class DashboardMetricsViewSet(ViewSet):
    """Aggregated dashboard metrics with tenant isolation."""

    permission_classes = [IsAuthenticated]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _first_of_month(d: date) -> date:
        return d.replace(day=1)

    @staticmethod
    def _first_of_week(d: date) -> date:
        """Monday of the current week (ISO)."""
        return d - timedelta(days=d.weekday())  # Monday=0

    def _clinic_id(self, request):
        return getattr(request.user, "clinic_id", None)

    # ------------------------------------------------------------------
    # Metric builders
    # ------------------------------------------------------------------

    def _appointments_today(self, clinic_id):
        today = timezone.localdate()
        return Appointment.objects.filter(
            clinic_id=clinic_id,
            date=today,
        ).count()

    def _appointments_this_week(self, clinic_id):
        today = timezone.localdate()
        monday = self._first_of_week(today)
        sunday = monday + timedelta(days=6)

        qs = Appointment.objects.filter(
            clinic_id=clinic_id,
            date__gte=monday,
            date__lte=sunday,
        )
        total = qs.count()
        by_status = {}
        for status, count in (
            qs.values("status").annotate(c=Count("id")).values_list("status", "c")
        ):
            by_status[status] = count
        return {"total": total, "by_status": by_status}

    def _appointments_this_month(self, clinic_id):
        today = timezone.localdate()
        first = self._first_of_month(today)

        qs = Appointment.objects.filter(
            clinic_id=clinic_id,
            date__gte=first,
            date__lte=today,
        )
        total = qs.count()
        completed = qs.filter(status=Appointment.Status.COMPLETED).count()
        rate = round(completed / total, 4) if total > 0 else 0.0
        return {"total": total, "completion_rate": rate}

    def _revenue_this_month(self, clinic_id):
        today = timezone.localdate()
        first = self._first_of_month(today)

        result = Invoice.objects.filter(
            clinic_id=clinic_id,
            status__in=("stamped", "sent", "paid"),
            created_at__date__gte=first,
            created_at__date__lte=today,
        ).aggregate(total=Sum("total"))
        return Decimal(result["total"] or 0)

    def _revenue_trend(self, clinic_id, days=30):
        today = timezone.localdate()
        start = today - timedelta(days=days - 1)

        daily = (
            Invoice.objects.filter(
                clinic_id=clinic_id,
                status__in=("stamped", "sent", "paid"),
                created_at__date__gte=start,
                created_at__date__lte=today,
            )
            .values("created_at__date")
            .annotate(total=Sum("total"))
            .order_by("created_at__date")
        )

        # Build full date range (fill gaps with 0)
        trend = []
        cursor = start
        i = 0
        while cursor <= today:
            if i < len(daily) and daily[i]["created_at__date"] == cursor:
                trend.append(
                    {
                        "date": cursor,
                        "total": Decimal(daily[i]["total"] or 0),
                    }
                )
                i += 1
            else:
                trend.append({"date": cursor, "total": Decimal(0)})
            cursor += timedelta(days=1)

        return trend

    def _appointments_trend(self, clinic_id, days=30):
        today = timezone.localdate()
        start = today - timedelta(days=days - 1)

        daily = (
            Appointment.objects.filter(
                clinic_id=clinic_id,
                date__gte=start,
                date__lte=today,
            )
            .exclude(status=Appointment.Status.CANCELLED)
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        # Build full date range (fill gaps with 0)
        trend = []
        cursor = start
        i = 0
        while cursor <= today:
            if i < len(daily) and daily[i]["date"] == cursor:
                trend.append({"date": cursor, "count": daily[i]["count"]})
                i += 1
            else:
                trend.append({"date": cursor, "count": 0})
            cursor += timedelta(days=1)

        return trend

    def _patients_total(self, clinic_id):
        return Patient.objects.filter(clinic_id=clinic_id).count()

    def _patients_new_this_month(self, clinic_id):
        today = timezone.localdate()
        first = self._first_of_month(today)
        return Patient.objects.filter(
            clinic_id=clinic_id,
            created_at__date__gte=first,
            created_at__date__lte=today,
        ).count()

    def _low_stock_count(self, clinic_id):
        return get_low_stock_items(str(clinic_id)).count()

    def _expiring_soon_count(self, clinic_id):
        return get_expiring_items(str(clinic_id)).count()

    def _upcoming_appointments(self, clinic_id):
        today = timezone.localdate()
        end = today + timedelta(days=7)

        qs = (
            Appointment.objects.filter(
                clinic_id=clinic_id,
                date__gte=today,
                date__lte=end,
                status__in=(
                    Appointment.Status.SCHEDULED,
                    Appointment.Status.CONFIRMED,
                ),
            )
            .select_related("patient", "appointment_type")
            .order_by("date", "start_time")[:10]
        )

        return [
            {
                "id": a.id,
                "patient_name": a.patient.full_name,
                "date": a.date,
                "time": a.start_time.strftime("%H:%M"),
                "type_name": a.appointment_type.name,
                "status": a.status,
            }
            for a in qs
        ]

    # ------------------------------------------------------------------
    # Endpoint
    # ------------------------------------------------------------------

    @action(detail=False, methods=["get"], url_path="metrics")
    def metrics(self, request):
        clinic_id = self._clinic_id(request)
        if clinic_id is None:
            return Response(
                {"error": "El usuario no está asociado a una clínica."},
                status=400,
            )

        return Response(
            {
                "appointments_today": self._appointments_today(clinic_id),
                "appointments_this_week": self._appointments_this_week(clinic_id),
                "appointments_this_month": self._appointments_this_month(clinic_id),
                "revenue_this_month": self._revenue_this_month(clinic_id),
                "revenue_trend": self._revenue_trend(clinic_id),
                "appointments_trend": self._appointments_trend(clinic_id),
                "patients_total": self._patients_total(clinic_id),
                "patients_new_this_month": self._patients_new_this_month(clinic_id),
                "low_stock_count": self._low_stock_count(clinic_id),
                "expiring_soon_count": self._expiring_soon_count(clinic_id),
                "upcoming_appointments": self._upcoming_appointments(clinic_id),
            }
        )
