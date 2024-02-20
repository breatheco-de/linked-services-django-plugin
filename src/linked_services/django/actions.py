import hashlib
import hmac
import os
import secrets
import urllib.parse
from datetime import datetime
from functools import lru_cache
from typing import Optional

import jwt
from asgiref.sync import sync_to_async
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from django.contrib.auth.models import User

from linked_services.core.exceptions import ValidationException
from linked_services.core.settings import get_setting
from linked_services.django.models import App, FirstPartyWebhookLog

JWT_LIFETIME = 10


def get_jwt(app: App, user_id: Optional[int] = None, reverse: bool = False):
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    whoamy = get_setting("name")

    # https://datatracker.ietf.org/doc/html/rfc7519#section-4
    payload = {
        "sub": user_id,
        "iss": os.getenv("API_URL", "http://localhost:8000"),
        "app": whoamy,
        "aud": app.slug,
        "exp": datetime.timestamp(now + timedelta(minutes=JWT_LIFETIME)),
        "iat": datetime.timestamp(now) - 1,
        "typ": "JWT",
    }

    if reverse:
        payload["app"] = app.slug
        payload["aud"] = whoamy

    if app.algorithm == "HMAC_SHA256":

        token = jwt.encode(payload, bytes.fromhex(app.private_key), algorithm="HS256")

    elif app.algorithm == "HMAC_SHA512":
        token = jwt.encode(payload, bytes.fromhex(app.private_key), algorithm="HS512")

    elif app.algorithm == "ED25519":
        token = jwt.encode(payload, bytes.fromhex(app.private_key), algorithm="EdDSA")

    else:
        raise Exception("Algorithm not implemented")

    return token


def get_signature(
    app: App,
    user_id: Optional[int] = None,
    *,
    method: str = "get",
    params: Optional[dict] = None,
    body: Optional[dict] = None,
    headers: Optional[dict] = None,
    reverse: bool = False,
):
    now = datetime.utcnow().isoformat()
    whoamy = get_setting("name")

    if headers is None:
        headers = {}

    if params is None:
        params = {}

    payload = {
        "timestamp": now,
        "app": whoamy,
        "method": method.upper(),
        "params": params or {},
        "body": body,
        "headers": headers or {},
    }

    if reverse:
        payload["app"] = app.slug

    paybytes = urllib.parse.urlencode(payload).encode("utf8")

    if app.algorithm == "HMAC_SHA256":
        sign = hmac.new(bytes.fromhex(app.private_key), paybytes, hashlib.sha256).hexdigest()

    elif app.algorithm == "HMAC_SHA512":
        sign = hmac.new(bytes.fromhex(app.private_key), paybytes, hashlib.sha512).hexdigest()

    else:
        raise Exception("Algorithm not implemented")

    return sign, now


def generate_auth_keys(algorithm) -> tuple[bytes, bytes]:
    public_key = None
    key = Ed25519PrivateKey.generate()

    if algorithm == "HMAC_SHA256" or algorithm == "HMAC_SHA512":
        private_key = secrets.token_hex(64)

    elif algorithm == "ED25519":
        private_key = key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        ).hex()

        public_key = (
            key.public_key().public_bytes(encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo).hex()
        )

    return public_key, private_key


@lru_cache(maxsize=100)
def get_optional_scopes_set(scope_set_id):
    from .models import OptionalScopeSet

    scope_set = OptionalScopeSet.objects.filter(id=scope_set_id).first()
    if scope_set is None:
        raise Exception(f"Invalid scope set id: {scope_set_id}")

    # use structure that use lower memory
    return tuple(sorted(x for x in scope_set.optional_scopes.all()))


def get_user_scopes(app_slug, user_id=None):
    from .models import AppUserAgreement

    info, _, _ = get_app_keys(app_slug)
    (_, _, _, _, require_an_agreement, required_scopes, optional_scopes, _, _, _) = info

    if user_id and require_an_agreement:
        agreement = AppUserAgreement.objects.filter(app__slug=app_slug, user__id=user_id).first()
        if not agreement:
            raise ValidationException(
                "User has not accepted the agreement",
                slug="agreement-not-accepted",
                silent=True,
                data={"app_slug": app_slug, "user_id": user_id},
            )

        optional_scopes = get_optional_scopes_set(agreement.optional_scope_set.id)

    # use structure that use lower memory
    return required_scopes, optional_scopes


@lru_cache(maxsize=100)
def get_app_keys(app_slug):
    from .models import App, Scope

    app = App.objects.filter(slug=app_slug).first()

    if app is None:
        raise ValidationException("Unauthorized", code=401, slug="app-not-found")

    if app.algorithm == "HMAC_SHA256":
        alg = "HS256"

    elif app.algorithm == "HMAC_SHA512":
        alg = "HS512"

    elif app.algorithm == "ED25519":
        alg = "EdDSA"

    else:
        raise ValidationException("Algorithm not implemented", code=401, slug="algorithm-not-implemented")

    legacy_public_key = None
    legacy_private_key = None
    legacy_key = None
    if hasattr(app, "legacy_key"):
        legacy_public_key = bytes.fromhex(app.legacy_key.public_key) if app.legacy_key.public_key else None
        legacy_private_key = bytes.fromhex(app.legacy_key.private_key)
        legacy_key = (
            legacy_public_key,
            legacy_private_key,
        )

    info = (
        app.id,
        alg,
        app.strategy,
        app.schema,
        app.require_an_agreement,
        tuple(sorted(x.slug for x in Scope.objects.filter(m2m_required_scopes__app=app))),
        tuple(sorted(x.slug for x in Scope.objects.filter(m2m_optional_scopes__app=app))),
        app.webhook_url,
        app.redirect_url,
        app.app_url,
    )
    key = (
        bytes.fromhex(app.public_key) if app.public_key else None,
        bytes.fromhex(app.private_key),
    )

    # use structure that use lower memory
    return info, key, legacy_key


def reset_app_cache():
    get_app.cache_clear()
    get_app_keys.cache_clear()
    get_optional_scopes_set.cache_clear()


def reset_app_user_cache():
    get_optional_scopes_set.cache_clear()


@lru_cache(maxsize=100)
def get_app(pk: str | int) -> App:
    kwargs = {}

    if isinstance(pk, int):
        kwargs["id"] = pk

    elif isinstance(pk, str):
        kwargs["slug"] = pk

    else:
        raise Exception("Invalid pk type")

    if not (app := App.objects.filter(**kwargs).first()):
        raise Exception("App not found")

    return app


async def aget_app(pk: str | int) -> App:
    return await sync_to_async(get_app)(pk)


class WebhookException(Exception):
    pass


async def send_webhook(
    app: str | int | App,
    type: str,
    data: Optional[dict | list] = None,
    user: Optional[str | int | User] = None,
):
    from .service import Service

    if not isinstance(app, App):
        app = await aget_app(app)

    if user and not isinstance(user, User):
        user = await User.objects.filter(id=user).afirst()
        if user is None:
            raise Exception("User not found")

    x = await FirstPartyWebhookLog.objects.acreate(app=app, type=type, data=data)
    payload = {
        "type": type,
        "external_id": x.id,
        "data": data,
    }

    user_id = None
    if user:
        user_id = user.id

    try:
        async with Service(app, user_id, proxy=True) as s:
            response = await s.webhook(payload)
            if response.status != 200:
                msg = f"Error calling webhook {app.webhook_url} with status {response.status}"

                # this has relation with a reveived signal not implemented yet
                x.processed = True
                x.status = "ERROR"
                x.status_text = msg
                x.save()

                raise WebhookException(msg)

    except WebhookException as e:
        raise e

    except Exception as e:
        x.delete()
        raise e

    # this has relation with a reveived signal not implemented yet
    x.processed = True
    # this will keep PENDING in the future
    x.status = "DONE"
    x.save()
