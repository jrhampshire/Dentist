"""
Appointment Scheduling URL routes — /api/v1/appointments/*

Routes:
- /api/v1/appointments/              — AppointmentViewSet (CRUD + available-slots action)
- /api/v1/appointment-types/         — AppointmentTypeViewSet (CRUD)
- /api/v1/schedule-slots/            — ScheduleSlotViewSet (CRUD)
- /api/v1/availability/              — AvailabilityView (list available slots)
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from appointments.views import (
    AppointmentTypeViewSet,
    AppointmentViewSet,
    AvailabilityView,
    ScheduleSlotViewSet,
)

# Main appointments router
router = DefaultRouter()
router.register(r"", AppointmentViewSet, basename="appointments")

# Appointment types router
types_router = DefaultRouter()
types_router.register(r"", AppointmentTypeViewSet, basename="appointment-types")

# Schedule slots router
schedule_router = DefaultRouter()
schedule_router.register(r"", ScheduleSlotViewSet, basename="schedule-slots")

urlpatterns = [
    # Appointment CRUD + available-slots action
    path("", include(router.urls)),
    # Appointment types (admin-only create/update)
    path("appointment-types/", include(types_router.urls)),
    # Schedule slots (recurring weekly availability)
    path("schedule-slots/", include(schedule_router.urls)),
    # Availability endpoint (flat endpoint for calendar widgets)
    path("availability/", AvailabilityView.as_view(), name="availability"),
]
