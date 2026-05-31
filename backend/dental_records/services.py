"""
Image processing services for dental_records app.

Provides thumbnail generation for PatientImage uploads and
metadata extraction for image file validation.
"""

from io import BytesIO
from typing import Optional

from django.core.files.uploadedfile import InMemoryUploadedFile


def generate_thumbnail(
    image_file, max_size=(300, 300)
) -> Optional[InMemoryUploadedFile]:
    """
    Generate a thumbnail for an uploaded image.

    Uses Pillow to resize the image preserving aspect ratio within max_size.
    Returns an InMemoryUploadedFile or None for PDFs / non-image files.

    Args:
        image_file: An opened file or InMemoryUploadedFile
        max_size: Maximum (width, height) for the thumbnail

    Returns:
        InMemoryUploadedFile with JPEG thumbnail, or None if not an image
    """
    from PIL import Image

    try:
        img = Image.open(image_file)
        img.verify()  # Verify it's a valid image
        image_file.seek(0)  # Reset to beginning after verify
        img = Image.open(image_file)
    except Exception:
        return None  # Not an image (e.g., PDF)

    # Convert to RGB if necessary (e.g., RGBA PNG)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Create thumbnail preserving aspect ratio
    img.thumbnail(max_size, Image.LANCZOS)

    # Save to BytesIO buffer
    thumb_io = BytesIO()
    img.save(thumb_io, format="JPEG", quality=85)
    thumb_io.seek(0)

    return InMemoryUploadedFile(
        file=thumb_io,
        field_name=None,
        name=f"thumb_{getattr(image_file, 'name', 'thumbnail')}.jpg",
        content_type="image/jpeg",
        size=thumb_io.getbuffer().nbytes,
        charset=None,
    )


def get_image_path(instance, filename: str) -> str:
    """
    Generate storage path for a patient image.

    Path format: patients/{patient_id}/images/{image_type}/{uuid}_{sanitized_filename}

    Args:
        instance: PatientImage instance
        filename: Original filename

    Returns:
        Storage path string
    """
    import os

    safe_name = os.path.basename(filename).replace(" ", "_")
    return (
        f"patients/{instance.patient_id}/images/"
        f"{instance.image_type}/{instance.id}_{safe_name}"
    )
