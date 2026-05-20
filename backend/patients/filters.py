"""
Patient Management filters.

PatientSearchFilter:
- ?q= — search by name, phone, or CURP
- ?phone= — search by exact phone number
- ?curp= — search by exact CURP
"""

from django.db.models import Q
from django_filters import rest_framework as filters

from patients.models import ClinicalNote, Patient, PatientConsent


class PatientSearchFilter(filters.FilterSet):
    """
    FilterSet for Patient search and filtering.

    Supports:
    - ?q= — fuzzy search across name, phone, CURP
    - ?phone= — exact phone match
    - ?curp= — exact CURP match
    - ?gender= — filter by gender
    - ?consent_signed= — filter by consent status
    - ?created_after= — filter by creation date
    """

    q = filters.CharFilter(method="filter_search", label="Search")
    phone = filters.CharFilter(lookup_expr="exact", label="Phone")
    curp = filters.CharFilter(lookup_expr="iexact", label="CURP")
    gender = filters.CharFilter(lookup_expr="exact", label="Gender")
    consent_signed = filters.BooleanFilter(label="Consent signed")
    created_after = filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Patient
        fields = ["phone", "curp", "gender", "consent_signed"]

    def filter_search(self, queryset, name, value):
        """
        Search across name fields, phone, and CURP.

        Supports partial matches for names and exact-ish matches for phone/CURP.
        """
        if not value:
            return queryset

        search_term = value.strip()

        return queryset.filter(
            Q(first_name__icontains=search_term)
            | Q(last_name__icontains=search_term)
            | Q(second_last_name__icontains=search_term)
            | Q(phone__icontains=search_term)
            | Q(curp__icontains=search_term)
            | Q(email__icontains=search_term)
        )


class ClinicalNoteFilter(filters.FilterSet):
    """FilterSet for ClinicalNote filtering."""

    note_type = filters.CharFilter(lookup_expr="exact", label="Note type")
    is_signed = filters.BooleanFilter(label="Is signed")
    created_after = filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = ClinicalNote
        fields = ["note_type", "is_signed"]


class PatientConsentFilter(filters.FilterSet):
    """FilterSet for PatientConsent filtering."""

    consent_type = filters.CharFilter(lookup_expr="exact", label="Consent type")
    signed = filters.BooleanFilter(label="Is signed")

    class Meta:
        model = PatientConsent
        fields = ["consent_type", "signed"]
