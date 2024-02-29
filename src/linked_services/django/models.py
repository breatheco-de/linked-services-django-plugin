import re
import uuid
from datetime import datetime, timedelta

from django import forms
from django.contrib.auth.models import User
from django.db import models
from slugify import slugify

LEGACY_KEY_LIFETIME = timedelta(minutes=2)


class Scope(models.Model):
    name = models.CharField(
        max_length=25, unique=True, help_text="Descriptive and unique name that appears on the authorize UI"
    )
    slug = models.CharField(max_length=15, unique=True, help_text="{action}:{data} for example read:repo")
    description = models.CharField(max_length=255, help_text="Description of the scope")

    def clean(self) -> None:
        if not self.slug:
            self.slug = slugify(self.name)

        if not self.description:
            raise forms.ValidationError("Scope description is required")

        if (
            not self.slug
            or not re.findall(r"^[a-z_:]+$", self.slug)
            or (0 < self.slug.count(":") > 1)
            or self.slug.count("__") > 0
        ):
            raise forms.ValidationError(
                'Scope slug must be in the format "action_name:data_name" or "data_name" example '
                '"read:repo" or "repo"'
            )

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.slug})"


HMAC_SHA256 = "HMAC_SHA256"
HMAC_SHA512 = "HMAC_SHA512"
ED25519 = "ED25519"
AUTH_ALGORITHM = (
    (HMAC_SHA256, "HMAC-SHA256"),
    (HMAC_SHA512, "HMAC_SHA512"),
    (ED25519, "ED25519"),
)

JWT = "JWT"
SIGNATURE = "SIGNATURE"
AUTH_STRATEGY = (
    (JWT, "Json Web Token"),
    (SIGNATURE, "Signature"),
)

LINK = "LINK"
AUTH_SCHEMA = ((LINK, "Link"),)

SYMMETRIC_ALGORITHMS = [HMAC_SHA256, HMAC_SHA512]
ASYMMETRIC_ALGORITHMS = [ED25519]


class App(models.Model):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._algorithm = self.algorithm
        self._strategy = self.strategy
        self._schema = self.schema

        self._private_key = self.private_key
        self._public_key = self.public_key

        self._webhook_url = self.webhook_url
        self._redirect_url = self.redirect_url

    name = models.CharField(max_length=25, unique=True, help_text="Descriptive and unique name of the app")
    slug = models.SlugField(
        unique=True, help_text="Unique slug for the app, it must be url friendly and please avoid to change it"
    )
    description = models.CharField(
        max_length=255, help_text="Description of the app, it will appear on the authorize UI"
    )

    algorithm = models.CharField(max_length=11, choices=AUTH_ALGORITHM, default=HMAC_SHA512)
    strategy = models.CharField(max_length=9, choices=AUTH_STRATEGY, default=JWT)
    schema = models.CharField(
        max_length=4,
        choices=AUTH_SCHEMA,
        default=LINK,
        help_text="Schema to use for the auth process to r2epresent how the apps will communicate",
    )

    required_scopes = models.ManyToManyField(
        Scope,
        blank=True,
        through="AppRequiredScope",
        through_fields=("app", "scope"),
        related_name="app_required_scopes",
    )
    optional_scopes = models.ManyToManyField(
        Scope,
        blank=True,
        through="AppOptionalScope",
        through_fields=("app", "scope"),
        related_name="app_optional_scopes",
    )
    agreement_version = models.IntegerField(default=1, help_text="Version of the agreement, based in the scopes")

    private_key = models.CharField(max_length=255, blank=True, null=False)
    public_key = models.CharField(max_length=255, blank=True, null=True, default=None)
    require_an_agreement = models.BooleanField(
        default=True, help_text="If true, the user will be required to accept an agreement"
    )

    users_path = models.CharField(
        max_length=200, default="/v1/auth/app/user/", blank=True, help_text="URL path to consult the users"
    )
    webhook_url = models.URLField(help_text="URL to receive webhooks")
    redirect_url = models.URLField(help_text="URL to redirect the user after the authorization")
    app_url = models.URLField(help_text="URL to the app")

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def clean(self) -> None:
        from .actions import generate_auth_keys

        if not self.slug:
            self.slug = slugify(self.name)

        if self.public_key and self.algorithm in SYMMETRIC_ALGORITHMS:
            raise forms.ValidationError("Public key is not required for symmetric algorithms")

        if not self.public_key and not self.private_key:
            self.public_key, self.private_key = generate_auth_keys(self.algorithm)

        if self.app_url.endswith("/"):
            self.app_url = self.app_url[:-1]

        return super().clean()

    def save(self, *args, **kwargs):
        from .actions import reset_app_cache

        had_pk = self.pk

        self.full_clean()
        super().save(*args, **kwargs)

        if had_pk and (
            self.private_key != self._private_key
            or self.public_key != self._public_key
            or self.algorithm != self._algorithm
        ):
            key = LegacyKey()
            key.app = self

            key.algorithm = self._algorithm
            key.strategy = self._strategy
            key.schema = self._schema

            key.private_key = self._private_key
            key.public_key = self._public_key

            key.webhook_url = self._webhook_url
            key.redirect_url = self._redirect_url

            key.save()

        if had_pk:
            reset_app_cache()

        self._algorithm = self.algorithm
        self._strategy = self.strategy
        self._schema = self.schema

        self._private_key = self.private_key
        self._public_key = self.public_key

        self._webhook_url = self.webhook_url
        self._redirect_url = self.redirect_url


class AppRequiredScope(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="m2m_required_scopes")
    scope = models.ForeignKey(Scope, on_delete=models.CASCADE, related_name="m2m_required_scopes")
    agreed_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return f"{self.app.name} ({self.app.slug}) -> {self.scope.name} ({self.scope.slug})"


class AppOptionalScope(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="m2m_optional_scopes")
    scope = models.ForeignKey(Scope, on_delete=models.CASCADE, related_name="m2m_optional_scopes")
    agreed_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return f"{self.app.name} ({self.app.slug}) -> {self.scope.name} ({self.scope.slug})"


class OptionalScopeSet(models.Model):
    optional_scopes = models.ManyToManyField(Scope, blank=True)

    def save(self, *args, **kwargs):
        from .actions import reset_app_user_cache

        had_pk = self.pk

        self.full_clean()
        super().save(*args, **kwargs)

        self.__class__.objects.exclude(app_user_agreement__id__gte=1).exclude(id=self.id).delete()

        if had_pk:
            reset_app_user_cache()


class AppUserAgreement(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    app = models.ForeignKey(App, on_delete=models.CASCADE)
    optional_scope_set = models.ForeignKey(
        OptionalScopeSet, on_delete=models.CASCADE, related_name="app_user_agreement"
    )
    agreement_version = models.IntegerField(default=1, help_text="Version of the agreement that was accepted")
    agreed_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        from .actions import reset_app_user_cache

        had_pk = self.pk

        self.full_clean()
        super().save(*args, **kwargs)

        if had_pk:
            reset_app_user_cache()


class LegacyKey(models.Model):

    app = models.OneToOneField(App, on_delete=models.CASCADE, related_name="legacy_key")

    algorithm = models.CharField(max_length=11, choices=AUTH_ALGORITHM)
    strategy = models.CharField(max_length=9, choices=AUTH_STRATEGY)
    schema = models.CharField(max_length=4, choices=AUTH_SCHEMA)

    private_key = models.CharField(max_length=255, blank=True, null=False)
    public_key = models.CharField(max_length=255, blank=True, null=True, default=None)

    webhook_url = models.URLField()
    redirect_url = models.URLField()

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.app.name} ({self.app.slug})"

    def clean(self) -> None:
        if self.public_key and self.algorithm in SYMMETRIC_ALGORITHMS:
            raise forms.ValidationError("Public key is not required for symmetric algorithms")

        if not self.public_key and not self.private_key:
            raise forms.ValidationError("Public and private keys are required")

        return super().clean()

    def save(self, *args, **kwargs):
        from . import tasks

        self.full_clean()
        super().save(*args, **kwargs)

        tasks.destroy_legacy_key.apply_async(args=(self.id,), eta=datetime.utcnow() + LEGACY_KEY_LIFETIME)

    def delete(self, *args, **kwargs):
        from . import actions

        r = super().delete(*args, **kwargs)
        actions.reset_app_cache()
        return r


PENDING = "PENDING"
# SENT = 'SENT'
DONE = "DONE"
ERROR = "ERROR"
WEBHOOK_STATUSES = (
    (PENDING, "Pending"),
    # (SENT, 'Sent'),
    (DONE, "Done"),
    (ERROR, "Error"),
)


class FirstPartyWebhookLog(models.Model):
    """First party credentials."""

    app = models.ForeignKey(App, on_delete=models.CASCADE, help_text="App that triggered or will receive the webhook")

    type = models.CharField(max_length=50, blank=True, default="unknown", help_text="Type of the webhook")

    user_id = models.IntegerField(default=None, null=True, blank=True, help_text="User ID who triggered the webhook")
    external_id = models.IntegerField(
        default=None, null=True, blank=True, help_text="External ID where the webhook was triggered"
    )

    url = models.URLField(default=None, null=True, blank=True, help_text="URL to consult the content")
    data = models.JSONField(default=dict, blank=True, null=True, help_text="Data received")

    processed = models.BooleanField(default=False, blank=True, help_text="If true, the webhook has been processed")
    attempts = models.IntegerField(default=0, blank=True, help_text="Number of attempts to process the webhook")

    status = models.CharField(max_length=9, choices=WEBHOOK_STATUSES, default=PENDING, blank=True)
    status_text = models.CharField(max_length=255, default=None, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def clean(self) -> None:
        from linked_services.core.settings import get_setting

        if self.data and not isinstance(self.data, dict) and not isinstance(self.data, list):
            raise forms.ValidationError("Data must be a dictionary or a list")

        app_name = get_setting("app_name")

        if self.app and self.app.slug == app_name:
            raise forms.ValidationError(f"You can't use {app_name} as app")

        if self.attempts < 0:
            raise forms.ValidationError("Attempts must be a positive integer")

        if self.user_id and self.user_id < 1:
            raise forms.ValidationError("User ID must be a positive integer")

        if self.type is None:
            self.type = "unknown"

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs)


class FirstPartyCredentials(models.Model):
    """First party credentials for 4geeks, like Rigobot."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="credentials")
    app = models.JSONField(default=dict, blank=True, help_text="Credentials in each app")
    health_status = models.JSONField(default=dict, blank=True, help_text="Health status of each credentials")

    def clean(self) -> None:
        from linked_services.core.settings import get_setting

        if not isinstance(self.app, dict):
            raise forms.ValidationError("App must be a dictionary")

        apps = self.app.keys()
        app_name = get_setting("app_name")
        for app in apps:
            t = type(self.app[app])
            if app == app_name:
                raise forms.ValidationError(f"You can't use {app_name} as app, app names must be unique")

            if t not in [int, str, uuid.UUID]:
                raise forms.ValidationError(
                    f"app['{app}'] credential must be an integer, string or UUID, but got {t.__name__}"
                )

            if t is int and self.app[app] < 1:
                raise forms.ValidationError(f"app['{app}'] credential must be a positive integer")

        self._apps = apps

        return super().clean()

    def save(self, *args, **kwargs):
        from linked_services.django import tasks

        if not self.health_status:
            self.health_status = {}

        self.full_clean()

        super().save(*args, **kwargs)

        to_check = []

        for app in self._apps:
            if (
                app not in self.health_status
                or self.health_status[app]["id"] != self.app[app]
                or self.health_status[app]["status"] != "HEALTHY"
            ):
                to_check.append(app)

        if to_check:
            tasks.check_credentials.delay(self.user.id, to_check)
