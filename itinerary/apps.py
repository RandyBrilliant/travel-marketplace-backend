from django.apps import AppConfig


class ItineraryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'itinerary'
    verbose_name = 'Itinerary Boards'
    
    def ready(self):
        """Import signals when the app is ready."""
        import itinerary.signals  # noqa