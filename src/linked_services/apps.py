from django.apps import AppConfig


class LinkedServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "linked_services"

    def ready(self):
        from linked_services.django import receivers  # noqa
