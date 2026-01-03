from django.apps import AppConfig


class TravelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'travel'
    
    def ready(self):
        """Import signals when the app is ready."""
        import travel.signals  # noqa