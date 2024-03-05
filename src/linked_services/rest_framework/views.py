import asyncio
import base64
import logging
import os
from typing import Callable, Optional

from adrf.decorators import api_view
from asgiref.sync import sync_to_async
from django.db.models import Q
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from linked_services.core.actions import set_query_parameter
from linked_services.core.i18n import translation
from linked_services.core.settings import get_setting
from linked_services.django.actions import aget_app
from linked_services.django.models import (
    AppUserAgreement,
    FirstPartyWebhookLog,
    OptionalScopeSet,
    Scope,
)
from linked_services.rest_framework.decorators import ascope

logger = logging.getLogger(__name__)


# app/webhook
@api_view(["POST"])
@permission_classes([AllowAny])
@ascope(["webhook"], mode="jwt")
async def app_webhook(request, app: dict, token: dict):

    async def process_webhook(data):
        nonlocal app, token

        app = await aget_app(app.id)
        external_id = data.get("id", None)
        kwargs = {
            "app": app,
            "user_id": token.sub,
            "external_id": external_id,
            "type": data.get("type", "unknown"),
        }
        if external_id:
            x, created = await FirstPartyWebhookLog.objects.aget_or_create(
                **kwargs, defaults={"data": data.get("data", None)}
            )
            if not created:
                x.data = data.get("data", None)
                await x.asave()

        else:
            kwargs["data"] = data.get("data", None)
            await FirstPartyWebhookLog.objects.acreate(**kwargs)

    data = request.data if isinstance(request.data, list) else [request.data]

    to_process = []

    for x in data:
        p = process_webhook(x)
        to_process.append(p)

    await asyncio.gather(*to_process)

    return Response(None, status=status.HTTP_204_NO_CONTENT)


def authorize_view(
    login_url: Optional[str] = None,
    app_url: Optional[str] = None,
    get_language: Optional[Callable[[HttpRequest], str]] = None,
):
    non_valid_envs = []
    if login_url is None:
        login_url = os.getenv("LOGIN_URL")

    if app_url is None:
        app_url = os.getenv("APP_URL")

    if login_url is None:
        non_valid_envs.append("LOGIN_URL")

    if app_url is None:
        non_valid_envs.append("APP_URL")

    if non_valid_envs:
        raise Exception(f"Missing environment variables: {', '.join(non_valid_envs)}")

    if get_language is None:

        def get_language(request: HttpRequest) -> str:
            return "en"

    @sync_to_async
    def aget_user(request: HttpRequest):
        return request.user

    @api_view(["GET", "POST"])
    @permission_classes([AllowAny])
    async def wrapper(request: HttpRequest, app_slug=None):
        user = await aget_user(request)

        if user.is_anonymous:

            # base64 encode
            forward = str(base64.b64encode(request.get_full_path().encode("utf-8")), "utf-8")
            url = set_query_parameter(login_url, url=forward)
            return redirect(url)

        lang = get_language(request)

        try:
            app = await aget_app(app_slug)

        except Exception:
            return render(
                request,
                "app-not-found.html",
                {
                    "app_url": app_url,
                    "title": translation(lang, en="Not found", es="No encontrado"),
                    "description": translation(lang, en="The app was not found", es="La app no fue encontrada"),
                    "btn": translation(lang, en="Go back", es="Volver"),
                },
                status=404,
            )

        if not app.require_an_agreement:
            return render(
                request,
                "app-not-found.html",
                {
                    "app_url": app_url,
                    "title": translation(lang, en="Not found", es="No encontrado"),
                    "description": translation(lang, en="The app was not found", es="La app no fue encontrada"),
                    "btn": translation(lang, en="Go back", es="Volver"),
                },
                status=404,
            )

        agreement = (
            await AppUserAgreement.objects.filter(app=app, user=request.user)
            .select_related("optional_scope_set")
            .afirst()
        )
        selected_scopes = (
            [x.slug async for x in agreement.optional_scope_set.optional_scopes.filter()] if agreement else []
        )

        required_scopes = [x async for x in Scope.objects.filter(m2m_required_scopes__app=app)]
        optional_scopes = [x async for x in Scope.objects.filter(m2m_optional_scopes__app=app)]

        new_scopes = (
            [
                x.slug
                async for x in Scope.objects.filter(
                    Q(m2m_required_scopes__app=app, m2m_required_scopes__agreed_at__gt=agreement.agreed_at)
                    | Q(m2m_optional_scopes__app=app, m2m_optional_scopes__agreed_at__gt=agreement.agreed_at),
                )
            ]
            if agreement
            else []
        )

        whoamy = get_setting("app_name")

        if request.method == "GET":
            whoamy = get_setting("app_name")
            return render(
                request,
                "authorize.html",
                {
                    "app": app,
                    "required_scopes": required_scopes,
                    "optional_scopes": optional_scopes,
                    "selected_scopes": selected_scopes,
                    "new_scopes": new_scopes,
                    "reject_url": app.redirect_url + f"?app={whoamy}&status=rejected",
                },
            )

        if request.method == "POST":
            items = set()
            for key in request.POST:
                if key == "csrfmiddlewaretoken":
                    continue

                items.add(key)

            items = sorted(list(items))
            query = Q()

            for item in items:
                query |= Q(optional_scopes__slug=item)

            created = False
            cache = await OptionalScopeSet.objects.filter(query).afirst()
            if cache is None or await cache.optional_scopes.acount() != len(items):
                cache = OptionalScopeSet()
                await cache.asave()

                created = True

                for s in items:
                    scope = await Scope.objects.filter(slug=s).afirst()
                    await cache.optional_scopes.aadd(scope)

            if agreement := await AppUserAgreement.objects.filter(app=app, user=request.user).afirst():
                if created:
                    agreement.agreed_at = timezone.now()

                agreement.optional_scope_set = cache
                agreement.agreement_version = app.agreement_version
                await agreement.asave()

            else:
                user = await aget_user(request)
                agreement = await AppUserAgreement.objects.acreate(
                    app=app,
                    user=user,
                    agreed_at=timezone.now(),
                    agreement_version=app.agreement_version,
                    optional_scope_set=cache,
                )

            whoamy = get_setting("app_name")
            return redirect(app.redirect_url + f"?app={whoamy}&status=authorized")

    return wrapper
