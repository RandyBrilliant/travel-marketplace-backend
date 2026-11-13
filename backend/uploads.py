"""
Upload validation and naming helpers.

Uploaded files are served publicly from /media/ on the API domain, so anything
that a browser could execute (HTML, SVG, XML, JS) must never be stored there,
and files with personal data must not have guessable names.
"""
import os
import uuid

from django.utils.deconstruct import deconstructible
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

# Pillow format name -> extension we store the file under.
IMAGE_FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "GIF": ".gif",
}

DOCUMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv",
}

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024


@deconstructible
class RandomFilename:
    """upload_to callable that stores files as <prefix>/<random hex><ext>."""

    def __init__(self, prefix):
        self.prefix = prefix.strip("/")

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[1].lower()[:10]
        return f"{self.prefix}/{uuid.uuid4().hex}{ext}"

    def __eq__(self, other):
        return isinstance(other, RandomFilename) and self.prefix == other.prefix


def detect_image_extension(uploaded_file):
    """
    Return the safe extension for an uploaded raster image, or raise
    ValidationError. The client's filename and Content-Type are ignored; the
    format is read from the file contents.
    """
    if uploaded_file.size > MAX_IMAGE_BYTES:
        raise serializers.ValidationError("Ukuran gambar maksimal 10MB.")
    try:
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as img:
            img_format = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise serializers.ValidationError("File harus berupa gambar JPG, PNG, WEBP, atau GIF.")
    finally:
        uploaded_file.seek(0)

    ext = IMAGE_FORMAT_EXTENSIONS.get(img_format)
    if not ext:
        raise serializers.ValidationError("File harus berupa gambar JPG, PNG, WEBP, atau GIF.")
    return ext


def validate_pdf(uploaded_file):
    """Require a real PDF: .pdf extension and %PDF- magic bytes."""
    if not uploaded_file:
        return uploaded_file
    if os.path.splitext(uploaded_file.name)[1].lower() != ".pdf":
        raise serializers.ValidationError("File itinerary harus berformat PDF.")
    if uploaded_file.size > MAX_DOCUMENT_BYTES:
        raise serializers.ValidationError("Ukuran PDF maksimal 20MB.")
    uploaded_file.seek(0)
    header = uploaded_file.read(5)
    uploaded_file.seek(0)
    if header != b"%PDF-":
        raise serializers.ValidationError("File itinerary harus berformat PDF.")
    return uploaded_file


def validate_attachment(uploaded_file):
    """Allow raster images (content-checked) and common document formats only."""
    if not uploaded_file:
        return uploaded_file
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        detect_image_extension(uploaded_file)
        return uploaded_file
    if ext == ".pdf":
        return validate_pdf(uploaded_file)
    if ext in DOCUMENT_EXTENSIONS:
        if uploaded_file.size > MAX_DOCUMENT_BYTES:
            raise serializers.ValidationError("Ukuran file maksimal 20MB.")
        return uploaded_file
    raise serializers.ValidationError(
        "Tipe file tidak diizinkan. Gunakan gambar (JPG, PNG, WEBP, GIF) atau dokumen "
        "(PDF, Word, Excel, PowerPoint, TXT, CSV)."
    )
