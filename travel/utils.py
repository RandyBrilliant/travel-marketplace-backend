"""
Image optimization utilities for converting images to WebP format.
"""
import os
import logging
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from django.conf import settings

logger = logging.getLogger('travel')


def optimize_image_to_webp(image_field, max_width=1920, max_height=1920, quality=85):
    """
    Optimize an image and convert it to WebP format.
    
    Args:
        image_field: Django ImageField instance
        max_width: Maximum width in pixels (default: 1920)
        max_height: Maximum height in pixels (default: 1920)
        quality: WebP quality (1-100, default: 85)
    
    Returns:
        bool: True if optimization was successful, False otherwise
    """
    if not image_field or not image_field.name:
        return False
    
    # Skip if already WebP
    if image_field.name.lower().endswith('.webp'):
        return False
    
    try:
        # Get the file path
        if hasattr(image_field, 'path'):
            file_path = image_field.path
        else:
            # For newly uploaded files, they might not have a path yet
            file_path = None
        
        # Open the image
        if file_path and os.path.exists(file_path):
            img = Image.open(file_path)
        else:
            # For in-memory files
            image_field.seek(0)
            img = Image.open(image_field)
            image_field.seek(0)
        
        # Convert RGBA to RGB if necessary (WebP supports transparency, but we'll use RGB for better compatibility)
        if img.mode in ('RGBA', 'LA'):
            # Create a white background for transparency
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'LA':
                # Convert LA to RGBA first
                rgba_img = Image.new('RGBA', img.size)
                rgba_img.paste(img, mask=img.split()[1] if len(img.split()) > 1 else None)
                background.paste(rgba_img, mask=rgba_img.split()[-1])
            else:
                background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode == 'P':
            # Convert palette mode to RGB
            img = img.convert('RGBA')
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if image is too large
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Save to WebP format
        output = BytesIO()
        img.save(output, format='WebP', quality=quality, method=6)
        output.seek(0)
        
        # Get the original filename and change extension to .webp
        original_name = os.path.basename(image_field.name)
        base_name = os.path.splitext(original_name)[0]
        webp_filename = f"{base_name}.webp"
        
        # Delete the old file if it exists and is not WebP
        if file_path and os.path.exists(file_path) and not file_path.lower().endswith('.webp'):
            try:
                os.remove(file_path)
            except (OSError, ValueError):
                pass  # File might be locked or already deleted
        
        # Save the new WebP file
        image_field.save(
            webp_filename,
            ContentFile(output.read()),
            save=False
        )
        
        return True
        
    except Exception as e:
        # Log the error but don't break the save process
        logger.error(f"Error optimizing image {image_field.name}: {str(e)}", exc_info=True)
        return False

