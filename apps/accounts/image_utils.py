"""
Image compression utilities for MyRecoveryPal.

Provides automatic image optimization for uploads, supporting both
Cloudinary (cloud) and local storage backends.
"""

import os
import logging
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings

logger = logging.getLogger(__name__)

# Configuration
MAX_IMAGE_DIMENSION = 1920  # Max width/height for general uploads
MAX_AVATAR_DIMENSION = 800  # Max width/height for avatars
JPEG_QUALITY = 85  # JPEG compression quality (1-100)
WEBP_QUALITY = 85  # WebP compression quality
MAX_FILE_SIZE_MB = 5  # Maximum allowed file size in MB

# Allowed image MIME types
ALLOWED_IMAGE_TYPES = {
    'image/jpeg': '.jpg',
    'image/jpg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
}


def is_cloudinary_enabled():
    """Check if Cloudinary storage is configured and enabled."""
    return all([
        getattr(settings, 'CLOUDINARY_STORAGE', {}).get('CLOUD_NAME'),
        getattr(settings, 'CLOUDINARY_STORAGE', {}).get('API_KEY'),
        getattr(settings, 'CLOUDINARY_STORAGE', {}).get('API_SECRET'),
    ])


def validate_image(image_file):
    """
    Validate an uploaded image file.

    Args:
        image_file: Django UploadedFile object

    Returns:
        tuple: (is_valid, error_message)
    """
    if not image_file:
        return False, "No image file provided"

    # Check file size
    max_size = MAX_FILE_SIZE_MB * 1024 * 1024
    if image_file.size > max_size:
        return False, f"Image size exceeds {MAX_FILE_SIZE_MB}MB limit"

    # Check MIME type
    content_type = getattr(image_file, 'content_type', None)
    if content_type not in ALLOWED_IMAGE_TYPES:
        return False, "Invalid image format. Allowed: JPEG, PNG, GIF, WebP"

    return True, None


def compress_image(image_file, max_dimension=MAX_IMAGE_DIMENSION, output_format='JPEG'):
    """
    Compress and resize an image for local storage.

    Args:
        image_file: Django UploadedFile object
        max_dimension: Maximum width/height (maintains aspect ratio)
        output_format: Output format ('JPEG', 'PNG', 'WEBP')

    Returns:
        InMemoryUploadedFile: Compressed image ready for storage
    """
    try:
        # Open image with Pillow
        img = Image.open(image_file)

        # Handle animated GIFs - don't process, return as-is
        if getattr(img, 'is_animated', False):
            image_file.seek(0)
            return image_file

        # Convert RGBA/LA/P modes to RGB for JPEG output
        if output_format == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
            # Create white background for transparency
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')

        # Resize if larger than max dimension (maintain aspect ratio)
        if img.width > max_dimension or img.height > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

        # Compress to buffer
        buffer = BytesIO()

        if output_format == 'JPEG':
            img.save(buffer, format='JPEG', quality=JPEG_QUALITY, optimize=True)
            content_type = 'image/jpeg'
            ext = '.jpg'
        elif output_format == 'WEBP':
            img.save(buffer, format='WEBP', quality=WEBP_QUALITY, optimize=True)
            content_type = 'image/webp'
            ext = '.webp'
        else:  # PNG
            img.save(buffer, format='PNG', optimize=True)
            content_type = 'image/png'
            ext = '.png'

        buffer.seek(0)

        # Generate filename
        original_name = getattr(image_file, 'name', 'image.jpg')
        base_name = os.path.splitext(original_name)[0]
        new_filename = f"{base_name}{ext}"

        # Create InMemoryUploadedFile
        compressed_file = InMemoryUploadedFile(
            file=buffer,
            field_name='image',
            name=new_filename,
            content_type=content_type,
            size=buffer.getbuffer().nbytes,
            charset=None
        )

        logger.info(
            f"Compressed image: {original_name} -> {new_filename} "
            f"({image_file.size} -> {compressed_file.size} bytes, "
            f"{img.width}x{img.height}px)"
        )

        return compressed_file

    except Exception as e:
        logger.error(f"Error compressing image: {e}")
        # Return original file if compression fails
        image_file.seek(0)
        return image_file


def upload_to_cloudinary(image_file, folder='uploads', transformation=None):
    """
    Upload an image to Cloudinary with automatic optimization.

    Args:
        image_file: Django UploadedFile object
        folder: Cloudinary folder path
        transformation: Optional list of transformations

    Returns:
        tuple: (success, result_or_error)
            On success: (True, {'url': secure_url, 'public_id': public_id})
            On failure: (False, error_message)
    """
    if not is_cloudinary_enabled():
        return False, "Cloudinary is not configured"

    try:
        import cloudinary.uploader

        # Default transformation for optimization
        if transformation is None:
            transformation = [
                {
                    'width': MAX_IMAGE_DIMENSION,
                    'height': MAX_IMAGE_DIMENSION,
                    'crop': 'limit',  # Only resize if larger
                    'quality': 'auto:good',
                    'fetch_format': 'auto',  # Auto-select best format
                }
            ]

        # Upload with transformations
        result = cloudinary.uploader.upload(
            image_file,
            folder=f"myrecoverypal/{folder}",
            transformation=transformation,
            resource_type='image',
        )

        logger.info(
            f"Uploaded to Cloudinary: {result.get('public_id')} "
            f"({result.get('bytes', 0)} bytes)"
        )

        return True, {
            'url': result.get('secure_url'),
            'public_id': result.get('public_id'),
            'width': result.get('width'),
            'height': result.get('height'),
            'format': result.get('format'),
            'bytes': result.get('bytes'),
        }

    except Exception as e:
        logger.error(f"Cloudinary upload error: {e}")
        return False, str(e)


def delete_from_cloudinary(public_id):
    """
    Delete an image from Cloudinary.

    Args:
        public_id: Cloudinary public ID of the image

    Returns:
        bool: True if deleted successfully
    """
    if not is_cloudinary_enabled() or not public_id:
        return False

    try:
        import cloudinary.uploader
        result = cloudinary.uploader.destroy(public_id)
        return result.get('result') == 'ok'
    except Exception as e:
        logger.error(f"Cloudinary delete error: {e}")
        return False


def process_uploaded_image(image_file, folder='uploads', max_dimension=MAX_IMAGE_DIMENSION):
    """
    Process an uploaded image - handles both Cloudinary and local storage.

    This is the main entry point for image processing. It:
    - Validates the image
    - Compresses/optimizes based on storage backend
    - Returns the processed file or Cloudinary URL

    Args:
        image_file: Django UploadedFile object
        folder: Folder/path for storage organization
        max_dimension: Maximum width/height

    Returns:
        tuple: (success, result_or_error)
            For Cloudinary: (True, {'url': url, 'public_id': id, ...})
            For local: (True, InMemoryUploadedFile)
            On failure: (False, error_message)
    """
    # Validate first
    is_valid, error = validate_image(image_file)
    if not is_valid:
        return False, error

    # Use Cloudinary if available (handles optimization automatically)
    if is_cloudinary_enabled():
        transformation = [
            {
                'width': max_dimension,
                'height': max_dimension,
                'crop': 'limit',
                'quality': 'auto:good',
                'fetch_format': 'auto',
            }
        ]
        return upload_to_cloudinary(image_file, folder=folder, transformation=transformation)

    # Fall back to local compression
    compressed = compress_image(image_file, max_dimension=max_dimension)
    return True, compressed
