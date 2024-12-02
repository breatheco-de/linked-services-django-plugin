from django.contrib import admin

from .models import (
    App,
    AppOptionalScope,
    AppRequiredScope,
    AppUserAgreement,
    FirstPartyCredentials,
    FirstPartyWebhookLog,
    LegacyKey,
    OptionalScopeSet,
    Scope,
)


@admin.register(Scope)
class ScopeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ["name", "slug"]
    actions = []


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "algorithm", "strategy", "schema", "agreement_version", "require_an_agreement")
    search_fields = ["name", "slug"]
    list_filter = ["algorithm", "strategy", "schema", "require_an_agreement"]


@admin.register(AppRequiredScope)
class AppRequiredScopeAdmin(admin.ModelAdmin):
    list_display = ("app", "scope", "agreed_at")
    search_fields = ["app__name", "app__slug", "scope__name", "scope__slug"]
    list_filter = ["app", "scope"]


@admin.register(AppOptionalScope)
class AppOptionalScopeAdmin(admin.ModelAdmin):
    list_display = ("app", "scope", "agreed_at")
    search_fields = ["app__name", "app__slug", "scope__name", "scope__slug"]
    list_filter = ["app", "scope"]


@admin.register(LegacyKey)
class LegacyKeyAdmin(admin.ModelAdmin):
    list_display = ("app", "algorithm", "strategy", "schema")
    search_fields = ["app__name", "app__slug"]
    list_filter = ["algorithm", "strategy", "schema"]
    actions = []


@admin.register(OptionalScopeSet)
class OptionalScopeSetAdmin(admin.ModelAdmin):
    list_display = ("id",)
    search_fields = ["optional_scopes__name", "optional_scopes__slug"]
    actions = []


@admin.register(AppUserAgreement)
class AppUserAgreementAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "app", "optional_scope_set", "agreement_version")
    search_fields = ["user__username", "user__email", "user__first_name", "user__last_name", "app__name", "app__slug"]
    list_filter = ["app"]
    actions = []


@admin.register(FirstPartyWebhookLog)
class FirstPartyWebhookLogAdmin(admin.ModelAdmin):
    list_display = ("id", "app", "type", "user_id", "external_id", "url", "processed", "attempts", "status")
    search_fields = ["user_id", "external_id", "url", "app__name", "app__slug"]
    list_filter = ["app", "type", "processed", "status"]
    actions = []


@admin.register(FirstPartyCredentials)
class FirstPartyCredentialsAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "app")
    search_fields = ["user__username", "user__email", "user__first_name", "user__last_name", "app__name", "app__slug"]
    list_filter = ["app"]
    actions = []
