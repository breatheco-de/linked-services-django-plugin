from typing import Type

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import AppOptionalScope, AppRequiredScope, AppUserAgreement
from .signals import app_scope_updated


@receiver(post_save, sender=AppRequiredScope)
def increment_on_update_required_scope(sender: Type[AppRequiredScope], instance: AppRequiredScope, **_):
    app_scope_updated.send(sender=sender, instance=instance)


@receiver(post_save, sender=AppOptionalScope)
def increment_on_update_optional_scope(sender: Type[AppOptionalScope], instance: AppOptionalScope, **_):
    app_scope_updated.send(sender=sender, instance=instance)


@receiver(pre_delete, sender=AppRequiredScope)
def increment_on_delete_required_scope(sender: Type[AppRequiredScope], instance: AppRequiredScope, **_):
    app_scope_updated.send(sender=sender, instance=instance)


@receiver(pre_delete, sender=AppOptionalScope)
def increment_on_delete_optional_scope(sender: Type[AppOptionalScope], instance: AppOptionalScope, **_):
    app_scope_updated.send(sender=sender, instance=instance)


@receiver(app_scope_updated)
def update_app_scope(
    sender: Type[AppOptionalScope | AppRequiredScope], instance: AppOptionalScope | AppRequiredScope, **_
):
    if AppUserAgreement.objects.filter(app=instance.app, agreement_version=instance.app.agreement_version).exists():
        instance.app.agreement_version += 1
        instance.app.save()
