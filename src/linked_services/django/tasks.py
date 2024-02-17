import os

from task_manager.django.decorators import task

settings = {}

if p := os.getenv("OAUTH_CREDENTIALS_PRIORITY"):
    settings["priority"] = int(p)

else:
    settings["priority"] = 5


@task(**settings)
def destroy_legacy_key(legacy_key_id, **_):
    from .models import LegacyKey

    LegacyKey.objects.filter(id=legacy_key_id).delete()
