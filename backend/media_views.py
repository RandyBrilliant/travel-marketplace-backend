from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.files.storage import default_storage
from django.conf import settings
import os
import uuid
from PIL import Image
import io


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
        
        # Validate file type
        if not uploaded_file.content_type.startswith('image/'):
            return Response(
                {"error": "File must be an image"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (5MB limit)
        if uploaded_file.size > 5 * 1024 * 1024:
            return Response(
                {"error": "File size must be less than 5MB"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Generate unique filename
            file_extension = os.path.splitext(uploaded_file.name)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = f"media/richtext/{unique_filename}"
            
            # Save file
            saved_path = default_storage.save(file_path, uploaded_file)
            
            # Get full URL
            file_url = request.build_absolute_uri(default_storage.url(saved_path))
            
            return Response({
                "file_url": file_url,
                "filename": unique_filename,
                "size": uploaded_file.size,
                "content_type": uploaded_file.content_type
            })
            
        except Exception as e:
            return Response(
                {"error": f"Failed to upload file: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )