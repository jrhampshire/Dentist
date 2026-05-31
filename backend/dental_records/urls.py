"""
URL configuration for dental_records app — /api/v1/dental-records/*

Routes all dental records endpoints nested under patients:

/api/v1/dental-records/patients/{patient_id}/teeth/entries/
/api/v1/dental-records/patients/{patient_id}/teeth/state/
/api/v1/dental-records/patients/{patient_id}/medical-history/
/api/v1/dental-records/patients/{patient_id}/vital-signs/
/api/v1/dental-records/patients/{patient_id}/images/
/api/v1/dental-records/patients/{patient_id}/plans/
/api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/
/api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{phase_id}/procedures/

Uses manual path() nesting following the pattern established in patients/urls.py.
"""

from django.urls import path

from dental_records.views import (
    DentalRecordEntryViewSet,
    MedicalHistoryViewSet,
    PatientImageViewSet,
    ToothStateViewSet,
    TreatmentPhaseViewSet,
    TreatmentPlanViewSet,
    TreatmentProcedureViewSet,
    VitalSignsViewSet,
)

app_name = "dental_records"

# ─────────────────────────────────────────────────────────────────────────
# URL Patterns
# ─────────────────────────────────────────────────────────────────────────

urlpatterns = [
    # ── Odontogram ──
    # GET  /api/v1/dental-records/patients/{patient_id}/teeth/entries/
    # POST /api/v1/dental-records/patients/{patient_id}/teeth/entries/
    # GET  /api/v1/dental-records/patients/{patient_id}/teeth/entries/{pk}/
    path(
        "patients/<uuid:patient_id>/teeth/entries/",
        DentalRecordEntryViewSet.as_view({"get": "list", "post": "create"}),
        name="patient-teeth-entries-list",
    ),
    path(
        "patients/<uuid:patient_id>/teeth/entries/<uuid:pk>/",
        DentalRecordEntryViewSet.as_view({"get": "retrieve"}),
        name="patient-teeth-entries-detail",
    ),
    # GET /api/v1/dental-records/patients/{patient_id}/teeth/state/
    path(
        "patients/<uuid:patient_id>/teeth/state/",
        ToothStateViewSet.as_view({"get": "list"}),
        name="patient-teeth-state",
    ),
    # ── Medical History ──
    # GET  /api/v1/dental-records/patients/{patient_id}/medical-history/
    # POST /api/v1/dental-records/patients/{patient_id}/medical-history/
    path(
        "patients/<uuid:patient_id>/medical-history/",
        MedicalHistoryViewSet.as_view({"get": "list", "post": "create"}),
        name="patient-medical-history-list",
    ),
    # GET  /api/v1/dental-records/patients/{patient_id}/medical-history/history/
    path(
        "patients/<uuid:patient_id>/medical-history/history/",
        MedicalHistoryViewSet.as_view({"get": "list_versions"}),
        name="patient-medical-history-versions",
    ),
    # GET /api/v1/dental-records/patients/{patient_id}/medical-history/{pk}/
    # PUT /api/v1/dental-records/patients/{patient_id}/medical-history/{pk}/
    path(
        "patients/<uuid:patient_id>/medical-history/<uuid:pk>/",
        MedicalHistoryViewSet.as_view({"get": "retrieve", "put": "update"}),
        name="patient-medical-history-detail",
    ),
    # ── Vital Signs ──
    # GET  /api/v1/dental-records/patients/{patient_id}/vital-signs/
    # POST /api/v1/dental-records/patients/{patient_id}/vital-signs/
    path(
        "patients/<uuid:patient_id>/vital-signs/",
        VitalSignsViewSet.as_view({"get": "list", "post": "create"}),
        name="patient-vital-signs-list",
    ),
    # GET /api/v1/dental-records/patients/{patient_id}/vital-signs/{pk}/
    path(
        "patients/<uuid:patient_id>/vital-signs/<uuid:pk>/",
        VitalSignsViewSet.as_view({"get": "retrieve"}),
        name="patient-vital-signs-detail",
    ),
    # ── Patient Images ──
    # GET  /api/v1/dental-records/patients/{patient_id}/images/
    # POST /api/v1/dental-records/patients/{patient_id}/images/
    path(
        "patients/<uuid:patient_id>/images/",
        PatientImageViewSet.as_view({"get": "list", "post": "create"}),
        name="patient-images-list",
    ),
    # GET    /api/v1/dental-records/patients/{patient_id}/images/{pk}/
    # DELETE /api/v1/dental-records/patients/{patient_id}/images/{pk}/
    path(
        "patients/<uuid:patient_id>/images/<uuid:pk>/",
        PatientImageViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="patient-images-detail",
    ),
    # GET /api/v1/dental-records/patients/{patient_id}/images/{pk}/file/
    path(
        "patients/<uuid:patient_id>/images/<uuid:pk>/file/",
        PatientImageViewSet.as_view({"get": "serve_file"}),
        name="patient-images-file",
    ),
    # GET /api/v1/dental-records/patients/{patient_id}/images/{pk}/thumbnail/
    path(
        "patients/<uuid:patient_id>/images/<uuid:pk>/thumbnail/",
        PatientImageViewSet.as_view({"get": "serve_thumbnail"}),
        name="patient-images-thumbnail",
    ),
    # ── Treatment Plans ──
    # GET  /api/v1/dental-records/patients/{patient_id}/plans/
    # POST /api/v1/dental-records/patients/{patient_id}/plans/
    path(
        "patients/<uuid:patient_id>/plans/",
        TreatmentPlanViewSet.as_view({"get": "list", "post": "create"}),
        name="patient-plans-list",
    ),
    # GET    /api/v1/dental-records/patients/{patient_id}/plans/{pk}/
    # PUT    /api/v1/dental-records/patients/{patient_id}/plans/{pk}/
    # PATCH  /api/v1/dental-records/patients/{patient_id}/plans/{pk}/
    # DELETE /api/v1/dental-records/patients/{patient_id}/plans/{pk}/
    path(
        "patients/<uuid:patient_id>/plans/<uuid:pk>/",
        TreatmentPlanViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="patient-plans-detail",
    ),
    # ── Treatment Phases (nested under plan) ──
    # GET  /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/
    # POST /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/
    path(
        "patients/<uuid:patient_id>/plans/<uuid:plan_id>/phases/",
        TreatmentPhaseViewSet.as_view({"get": "list", "post": "create"}),
        name="patient-plan-phases-list",
    ),
    # GET    /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{pk}/
    # PUT    /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{pk}/
    # PATCH  /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{pk}/
    # DELETE /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{pk}/
    path(
        "patients/<uuid:patient_id>/plans/<uuid:plan_id>/phases/<uuid:pk>/",
        TreatmentPhaseViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="patient-plan-phases-detail",
    ),
    # ── Treatment Procedures (nested under phase) ──
    # GET  /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{phase_id}/procedures/
    # POST /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{phase_id}/procedures/
    path(
        "patients/<uuid:patient_id>/plans/<uuid:plan_id>/phases/<uuid:phase_id>/procedures/",
        TreatmentProcedureViewSet.as_view({"get": "list", "post": "create"}),
        name="patient-plan-phase-procedures-list",
    ),
    # GET    /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{phase_id}/procedures/{pk}/
    # PUT    /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{phase_id}/procedures/{pk}/
    # PATCH  /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{phase_id}/procedures/{pk}/
    # DELETE /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{phase_id}/procedures/{pk}/
    path(
        "patients/<uuid:patient_id>/plans/<uuid:plan_id>/phases/<uuid:phase_id>/procedures/<uuid:pk>/",
        TreatmentProcedureViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="patient-plan-phase-procedures-detail",
    ),
]
