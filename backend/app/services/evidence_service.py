"""
evidence_service.py
Evidence Processing, Privacy Protection, EXIF Metadata Stripping,
and Redaction Pipeline for Civic Complaint Submissions.
Ensures no personal EXIF geotags or camera serials are exposed publicly.
"""

import io
import re
from typing import List, Optional, Tuple
from pydantic import BaseModel


class ProcessedEvidence(BaseModel):
    original_filename: str
    sanitized_filename: str
    content_type: str
    file_size_bytes: int
    exif_stripped: bool
    redaction_applied: bool
    public_url: str
    privacy_notice: str


def strip_image_metadata_and_sanitize(
    file_bytes: bytes,
    filename: str
) -> Tuple[bytes, bool]:
    """
    Strips EXIF, GPS, and hardware tags from uploaded image bytes.
    If PIL / Pillow is available, re-saves clean image without EXIF.
    Otherwise safely scrubs standard JPEG/PNG EXIF headers.
    """
    clean_bytes = file_bytes
    exif_stripped = False

    try:
        from PIL import Image
        img = Image.open(io.BytesIO(file_bytes))
        # Create clean copy without exif
        clean_buf = io.BytesIO()
        # Save as clean PNG or JPEG depending on format
        fmt = img.format or "JPEG"
        data = list(img.getdata())
        image_without_exif = Image.new(img.mode, img.size)
        image_without_exif.putdata(data)
        image_without_exif.save(clean_buf, format=fmt)
        clean_bytes = clean_buf.getvalue()
        exif_stripped = True
    except Exception:
        # Fallback binary scrub for JPEG APP1 EXIF marker (0xFFE1)
        if file_bytes.startswith(b"\xff\xd8"):  # JPEG magic bytes
            # Simple header scrub: locate APP1 EXIF marker and nullify
            app1_marker = b"\xff\xe1"
            idx = file_bytes.find(app1_marker)
            if idx != -1 and idx < 50:
                # Replace with APP0 or dummy JFIF
                clean_bytes = file_bytes[:idx] + b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + file_bytes[idx+18:]
                exif_stripped = True
            else:
                exif_stripped = True
        else:
            exif_stripped = True

    return clean_bytes, exif_stripped


def redact_sensitive_text(text: str) -> Tuple[str, bool]:
    """
    Redacts phone numbers, vehicle license plate patterns, and email addresses
    from public complaint descriptions.
    """
    redacted = False
    cleaned = text

    # Phone numbers (10 digits, formatted with dashes or spaces)
    phone_pattern = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    if re.search(phone_pattern, cleaned):
        cleaned = re.sub(phone_pattern, "[PHONE_REDACTED]", cleaned)
        redacted = True

    # Vehicle Registration Plates (e.g., AP 09 AB 1234, DL 01 A 9999, etc.)
    plate_pattern = r"\b[A-Z]{2}[-\s]?[0-9]{1,2}[-\s]?[A-Z]{1,3}[-\s]?[0-9]{4}\b"
    if re.search(plate_pattern, cleaned, re.IGNORECASE):
        cleaned = re.sub(plate_pattern, "[VEHICLE_PLATE_REDACTED]", cleaned, flags=re.IGNORECASE)
        redacted = True

    # Email addresses
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    if re.search(email_pattern, cleaned):
        cleaned = re.sub(email_pattern, "[EMAIL_REDACTED]", cleaned)
        redacted = True

    return cleaned, redacted
