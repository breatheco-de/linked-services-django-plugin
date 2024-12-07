import os
from datetime import datetime, timedelta
from typing import Callable, Generator, Optional

import jwt
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from linked_services.rest_framework.types import LinkedApp

__all__ = ["Service", "service"]


class Service:
    def sign_jwt(
        self,
        client: APIClient,
        app: LinkedApp,
        user_id: Optional[int] = None,
        reverse: bool = False,
    ):
        """
        Set Json Web Token in the request.

        Usage:

        ```py
        # setup the database
        model = self.bc.database.create(app=1, user=1)

        # that setup the request to use the credential of user passed
        self.bc.request.authenticate(model.app, model.user.id)
        ```

        Keywords arguments:

        - user: a instance of user model `breathecode.authenticate.models.User`
        """

        now = timezone.now()

        # https://datatracker.ietf.org/doc/html/rfc7519#section-4
        payload = {
            "sub": str(user_id or ""),
            "iss": os.getenv("API_URL", "http://localhost:8000"),
            "app": app.slug,
            "aud": "breathecode",
            "exp": datetime.timestamp(now + timedelta(minutes=2)),
            "iat": datetime.timestamp(now) - 1,
            "typ": "JWT",
        }

        if reverse:
            payload["aud"] = app.slug
            payload["app"] = "breathecode"

        if app.algorithm == "HMAC_SHA256":

            token = jwt.encode(payload, bytes.fromhex(app.private_key), algorithm="HS256")

        elif app.algorithm == "HMAC_SHA512":
            token = jwt.encode(payload, bytes.fromhex(app.private_key), algorithm="HS512")

        elif app.algorithm == "ED25519":
            token = jwt.encode(payload, bytes.fromhex(app.private_key), algorithm="EdDSA")

        else:
            raise Exception("Algorithm not implemented")

        client.credentials(HTTP_AUTHORIZATION=f"Link App={app.slug},Token={token}")


@pytest.fixture
def service() -> Generator[Service, None, None]:
    yield Service()
