import logging
import uuid

from django.core.files.storage import default_storage
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.uploads import detect_image_extension

logger = logging.getLogger(__name__)

MAX_RICHTEXT_IMAGE_BYTES = 5 * 1024 * 1024


class MediaUploadView(APIView):
    """Generic media upload endpoint for images used in rich text content."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        uploaded_file = request.FILES.get('file')

        if not uploaded_file:
            return Response(
                {"error": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if uploaded_file.size > MAX_RICHTEXT_IMAGE_BYTES:
            return Response(
                {"error": "File size must be less than 5MB"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # The client's filename and Content-Type are not trusted: the format is
        # read from the file itself and only JPEG/PNG/WEBP/GIF are accepted.
        # This keeps HTML/SVG and other browser-executable files off /media/.
        try:
            extension = detect_image_extension(uploaded_file)
        except serializers.ValidationError:
            return Response(
                {"error": "File must be a JPG, PNG, WEBP or GIF image"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            unique_filename = f"{uuid.uuid4().hex}{extension}"
            saved_path = default_storage.save(f"media/richtext/{unique_filename}", uploaded_file)
            file_url = request.build_absolute_uri(default_storage.url(saved_path))
        except Exception:
            logger.exception("Rich-text image upload failed")
            return Response(
                {"error": "Failed to upload file"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "file_url": file_url,
            "filename": unique_filename,
            "size": uploaded_file.size,
            "content_type": f"image/{extension.lstrip('.').replace('jpg', 'jpeg')}",
        })
