"""
Django signals for automatically optimizing itinerary card cover images to WebP format.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ItineraryCard
from travel.utils import optimize_image_to_webp


# Flag to prevent infinite recursion
_optimizing = set()


def _optimize_image_field(instance, field_name):
    """Helper function to optimize an image field without causing recursion."""
    # Skip if instance doesn't have a primary key yet (new instance)
    if not instance.pk:
        return
    
    # Create a unique identifier for this instance and field
    instance_id = f"{instance.__class__.__name__}_{instance.pk}_{field_name}"
    
    # Skip if already optimizing this instance
    if instance_id in _optimizing:
        return
    
    image_field = getattr(instance, field_name, None)
    if image_field and image_field.name:
        # Check if already WebP to avoid unnecessary processing
        if not image_field.name.lower().endswith('.webp'):
            _optimizing.add(instance_id)
            try:
                if optimize_image_to_webp(image_field):
                    # Save the instance with the optimized image
                    # Using update_fields to only save this field
                    instance.save(update_fields=[field_name])
            finally:
                _optimizing.discard(instance_id)


@receiver(post_save, sender=ItineraryCard)
def optimize_card_cover_image(sender, instance, created, **kwargs):
    """Optimize cover image when ItineraryCard is saved."""
    _optimize_image_field(instance, 'cover_image')

