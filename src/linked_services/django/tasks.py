import logging
import os

from django.contrib.auth.models import User
from task_manager.core.exceptions import AbortTask, RetryTask
from task_manager.django.decorators import task

from linked_services.django.actions import get_app
from linked_services.django.models import FirstPartyCredentials, FirstPartyWebhookLog
from linked_services.django.service import Service

logger = logging.getLogger(__name__)
settings = {}

if p := os.getenv("OAUTH_CREDENTIALS_PRIORITY"):
    settings["priority"] = int(p)

else:
    settings["priority"] = 5


@task(**settings)
def destroy_legacy_key(legacy_key_id, **_):
    from .models import LegacyKey

    LegacyKey.objects.filter(id=legacy_key_id).delete()


@task(**settings)
def check_credentials(user_id: int, check=None, **_):

    def error(app_name: str, credentials: FirstPartyCredentials, status="NOT_FOUND"):
        credentials.health_status[app_name] = {"id": credentials.app[app_name], "status": status}
        del credentials.app[app_name]
        credentials.save()

    logger.info("Running check_credentials task")

    if check is None:
        raise AbortTask("Nothing to check")

    if not (
        credentials := FirstPartyCredentials.objects.filter(user__id=user_id)
        .only("health_status", "app", "user__email")
        .first()
    ):
        raise RetryTask("FirstPartyCredentials not found")

    for app_name in check:
        if credentials.app.get(app_name, None) is None:
            save = False
            if app_name in credentials.health_status:
                del credentials.health_status[app_name]
                save = True

            if app_name in credentials.app:
                del credentials.app[app_name]
                save = True

            if save:
                credentials.save()

            return

        else:
            try:
                app = get_app(app_name)

            except Exception:
                # logger.error(f"App {app_name} not found")
                error(app_name, credentials, status="APP_NOT_FOUND")
                continue

            with Service(app) as s:
                response = s.get(f"{s.app.users_path}?email={credentials.user.email}&id={credentials.app[app_name]}")

                if response.status_code != 200:
                    return error(app_name, credentials)

                json = response.json()
                if not isinstance(json, list) or len(json) == 0:
                    return error(app_name, credentials)

                else:
                    credentials.health_status[app_name] = {"id": credentials.app[app_name], "status": "HEALTHY"}
                    credentials.save()


@task(**settings)
def import_external_user(webhook_id: int, **_):
    logger.info("Running check_credentials task")

    webhook = FirstPartyWebhookLog.objects.filter(id=webhook_id).first()
    if webhook is None:
        raise AbortTask("Webhook not found")

    if webhook.data is None or not isinstance(webhook.data, dict):
        logger.error(f"Webhook {webhook.type} requires a data field as json")
        return

    errors = []
    for field in ["id", "email", "first_name", "last_name"]:
        if field not in webhook.data:
            errors.append(field)

    if len(errors) > 0:
        format = ", ".join(["data." + x for x in errors])
        logger.error(f"Webhook {webhook.type} requires a data field as json with the following fields: {format}")
        return

    app = webhook.app

    if User.objects.filter(**{f"credentials__app__{app.slug}": webhook.data["id"]}).exists():
        return

    user = User.objects.filter(email=webhook.data["email"]).first()
    if user is None:
        user = User.objects.create(
            email=webhook.data["email"],
            username=webhook.data["email"],
            first_name=webhook.data["first_name"],
            last_name=webhook.data["last_name"],
            is_active=True,
        )

        instance, created = FirstPartyCredentials.objects.get_or_create(
            user=user,
            defaults={
                "app": {
                    app.slug: webhook.data["id"],
                },
            },
        )

        if not created:
            instance.app[app.slug] = webhook.data["id"]
            instance.save()
