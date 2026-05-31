"""
Enums and choices shared across dental_records models.

All TextChoices use bilingual (key, label) tuples following the existing
project convention established in patients/models.py and appointments/models.py.
"""

from django.db import models


# ─────────────────────────────────────────────────────────────────────────
# Tooth condition — clinical state of a tooth or tooth surface
# ─────────────────────────────────────────────────────────────────────────


class ToothCondition(models.TextChoices):
    HEALTHY = "healthy", "Sano"
    CARIES = "caries", "Caries"
    FILLING = "filling", "Obturado"
    CROWN = "crown", "Corona"
    BRIDGE = "bridge", "Puente"
    MISSING = "missing", "Ausente"
    IMPLANT = "implant", "Implante"
    ROOT_CANAL = "root_canal", "Endodoncia"
    EXTRACTION = "extraction", "Extracción"
    FRACTURE = "fracture", "Fractura"
    WEAR = "wear", "Desgaste"
    SEALANT = "sealant", "Sellador"
    PROSTHESIS = "prosthesis", "Prótesis"
    OTHER = "other", "Otro"


# ─────────────────────────────────────────────────────────────────────────
# Tooth surfaces — the side/face of a tooth being examined
# ─────────────────────────────────────────────────────────────────────────


class Surface(models.TextChoices):
    MESIAL = "mesial", "Mesial"
    DISTAL = "distal", "Distal"
    BUCCAL = "buccal", "Bucal"
    LINGUAL = "lingual", "Lingual"
    OCCLUSAL = "occlusal", "Oclusal"
    ROOT = "root", "Raíz"


# ─────────────────────────────────────────────────────────────────────────
# Image type — classification of patient images
# ─────────────────────────────────────────────────────────────────────────


class ImageType(models.TextChoices):
    PHOTO = "photo", "Foto Clínica"
    XRAY_PERIAPICAL = "xray_periapical", "Radiografía Periapical"
    XRAY_PANORAMIC = "xray_panoramic", "Radiografía Panorámica"
    XRAY_CEPHALOMETRIC = "xray_cephalometric", "Radiografía Cefalométrica"
    DOCUMENT = "document", "Documento"
    OTHER = "other", "Otro"
