"""
Patient Management URL routes — /api/v1/patients/*

Routes:
- /api/v1/patients/              — PatientViewSet (CRUD + search)
- /api/v1/patients/{id}/notes/   — ClinicalNoteViewSet (CRUD + sign)
- /api/v1/patients/{id}/consents/ — PatientConsentViewSet (CRUD + sign)
- /api/v1/patients/audit-trail/  — AuditTrailViewSet (NOM-024 read-only)
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from patients.views import (
    AuditTrailViewSet,
    ClinicalNoteViewSet,
    PatientConsentViewSet,
    PatientViewSet,
)

# Main patient router
router = DefaultRouter()
router.register(r"", PatientViewSet, basename="patients")

# Nested routes for notes and consents are handled via URL patterns
# because DRF doesn't support true nested routers out of the box.

urlpatterns = [
    # Patient CRUD + search
    path("", include(router.urls)),
    # Clinical notes (nested under patient)
    path(
        "<uuid:patient_id>/notes/",
        ClinicalNoteViewSet.as_view({"get": "list", "post": "create"}),
        name="patient-notes-list",
    ),
    path(
        "<uuid:patient_id>/notes/<uuid:pk>/",
        ClinicalNoteViewSet.as_view({"get": "retrieve"}),
        name="patient-notes-detail",
    ),
    path(
        "<uuid:patient_id>/notes/<uuid:pk>/sign/",
        ClinicalNoteViewSet.as_view({"post": "sign"}),
        name="patient-notes-sign",
    ),
    # Consents (nested under patient)
    path(
        "<uuid:patient_id>/consents/",
        PatientConsentViewSet.as_view({"get": "list", "post": "create"}),
        name="patient-consents-list",
    ),
    path(
        "<uuid:patient_id>/consents/<uuid:pk>/",
        PatientConsentViewSet.as_view({"get": "retrieve"}),
        name="patient-consents-detail",
    ),
    path(
        "<uuid:patient_id>/consents/<uuid:pk>/sign/",
        PatientConsentViewSet.as_view({"post": "sign"}),
        name="patient-consents-sign",
    ),
    # Audit trail (NOM-024 compliance)
    path(
        "audit-trail/",
        AuditTrailViewSet.as_view({"get": "list"}),
        name="audit-trail-list",
    ),
    path(
        "audit-trail/<uuid:pk>/",
        AuditTrailViewSet.as_view({"get": "retrieve"}),
        name="audit-trail-detail",
    ),
]
