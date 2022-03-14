from django.apps import AppConfig


class Ichange40Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ichange40'

    def ready(self):
        from . import schedulers
        schedulers.setup()

        super().ready()
