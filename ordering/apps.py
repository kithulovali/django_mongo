from django.apps import AppConfig
from django.conf import settings

class OrderingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ordering'

    def ready(self):
        # Connect MongoEngine
        from mongoengine import register_connection
        register_connection(
            alias=getattr(settings, 'MONGODB_ALIAS', 'default'),
            host=getattr(settings, 'MONGODB_HOST', 'mongodb://localhost:27017/kfc_db'),
            name=getattr(settings, 'MONGODB_NAME', 'kfc_db'),
        )
