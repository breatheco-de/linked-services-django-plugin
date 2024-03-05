import base64
import os
import random
import urllib.parse
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from linked_services.core.settings import set_settings
from linked_services.rest_framework.views import authorize_view


async def fix_data(apps=[], scopes=[]):

    def fixer(s):
        for word in ["permissions", "required", "optional", "checked", "New", "new"]:
            s = s.replace(word, "x")

        return s

    for app in apps:
        app.name = fixer(app.name)
        app.slug = fixer(app.slug)
        app.description = fixer(app.description)
        await app.asave()

    for scope in scopes:
        scope.name = fixer(scope.name)
        scope.slug = fixer(scope.slug)
        scope.description = fixer(scope.description)
        await scope.asave()


@pytest.fixture(autouse=True)
def setup(db: None, database, set_env, fake, monkeypatch: pytest.MonkeyPatch):
    set_settings(app_name="breathecode")
    set_env(LOGIN_URL=fake.url(), APP_URL=fake.url())

    def get_scopes(n=0):
        for n in range(n):
            slug = fake.slug().replace("-", "_")[:7]

            if random.randint(0, 1):
                slug += ":" + fake.slug().replace("-", "_")[:7]

            yield {"slug": slug}
        ...

    async def fn(
        user=0, app=0, optional_scope_set=0, app_user_agreement=0, scopes=0, optional_scopes=0, required_scopes=0
    ):
        # app = {'require_an_agreement': True}
        # optional_scope_set = {"optional_scopes": []}
        # import timezone from django

        now = timezone.now()
        # app_user_agreement = {"agreed_at": now - timedelta(days=1)}

        scopes = [*get_scopes(scopes)]

        if app and isinstance(optional_scopes, list) and isinstance(required_scopes, list):
            app_required_scopes = required_scopes
            app_optional_scopes = optional_scopes

        elif app and len(scopes) >= optional_scopes + required_scopes:
            app_optional_scopes = [
                {
                    "app_id": 1,
                    "scope_id": n + 1,
                    "agreed_at": now,
                }
                for n in range(optional_scopes)
            ]

            app_required_scopes = [
                {
                    "app_id": 1,
                    "scope_id": optional_scopes + n + 1,
                    "agreed_at": now,
                }
                for n in range(required_scopes)
            ]

        elif app and optional_scopes + required_scopes != 0:
            raise Exception("Invalid number of scopes")

        else:
            app_required_scopes = []
            app_optional_scopes = []

        model = await database.acreate(
            user=user,
            app=app,
            scope=scopes,
            app_user_agreement=app_user_agreement,
            optional_scope_set=optional_scope_set,
            app_required_scope=app_required_scopes,
            app_optional_scope=app_optional_scopes,
        )

        apps = []
        scopes = []

        if "app" in model:
            if isinstance(model.app, list):
                apps = model.app
            else:
                apps = [model.app]

        if "scope" in model:
            if isinstance(model.scope, list):
                scopes = model.scope
            else:
                scopes = [model.scope]

        await fix_data(apps=apps, scopes=scopes)
        return model

    with patch("django.template.context_processors.get_token", MagicMock(return_value="predicabletoken")):
        yield fn


# class AnonymousUser:
#     def __init__(self):
#         self.is_authenticated = False


# class RequestMock:
#     def __init__(self, method="GET", user=AnonymousUser()):
#         self.method = method
#         self.user = user

#     async def auser(self):
#         return self.user


def encode(s):
    return str(base64.b64encode(s.encode("utf-8")), "utf-8")


def get_es_translations(request):
    return "es"


def get_en_translations(request):
    return "en"


class TestGet:

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    @pytest.mark.parametrize("value", [None, "https://www.google.com"])
    async def test_no_auth(self, fake, value):
        view = authorize_view(login_url=value)
        request = HttpRequest()
        request.method = "GET"
        request.path = fake.url()

        response = await view(request, app_slug=fake.slug())
        assert response.status_code == 302
        assert response.content == b""

        if value is None:
            value = os.getenv("LOGIN_URL")

        assert response.url == value + "?url=" + urllib.parse.quote(encode(request.get_full_path()))

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    @pytest.mark.parametrize(
        "value, get_language, translations",
        [
            (
                None,
                None,
                {
                    "title": "Not found",
                    "description": "The app was not found",
                    "btn": "Go back",
                },
            ),
            (
                "https://www.google.com",
                get_es_translations,
                {
                    "title": "No encontrado",
                    "description": "La app no fue encontrada",
                    "btn": "Volver",
                },
            ),
            (
                "https://manageyourpig.com",
                get_en_translations,
                {
                    "title": "Not found",
                    "description": "The app was not found",
                    "btn": "Go back",
                },
            ),
        ],
    )
    async def test_app_not_found(self, fake, setup, value, get_language, translations):

        view = authorize_view(app_url=value, get_language=get_language)
        request = HttpRequest()
        request.method = "GET"
        model = await setup(user=1)
        request.user = model.user
        request.path = fake.url()

        request_factory = APIRequestFactory()
        request = request_factory.get(fake.url())  # Specify the path you need

        force_authenticate(request, user=model.user)

        response = await view(request, app_slug=fake.slug())

        if value is None:
            value = os.getenv("APP_URL")

        expected = render(
            request,
            "app-not-found.html",
            {
                "app_url": value,
                **translations,
            },
            status=404,
        )

        assert response.content == expected.content
        assert response.status_code == expected.status_code

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test_agreement_message_without_any_scope(self, fake, database, setup):

        view = authorize_view()
        request = HttpRequest()
        request.method = "GET"
        model = await setup(user=1, app=1)
        request.user = model.user
        request.path = fake.url()

        request_factory = APIRequestFactory()
        request = request_factory.get(fake.url())  # Specify the path you need

        force_authenticate(request, user=model.user)

        response = await view(request, app_slug=model.app.slug)

        expected = render(
            request,
            "authorize.html",
            {
                "app": model.app,
                "required_scopes": [],
                "optional_scopes": [],
                "selected_scopes": [],
                "new_scopes": [],
                "reject_url": model.app.redirect_url + "?app=breathecode&status=rejected",
            },
        )

        assert response.content == expected.content
        assert response.status_code == expected.status_code

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    @pytest.mark.parametrize("agreement, optional_scopes, required_scopes", [(True, 3, 3), (False, 0, 3), (True, 3, 0)])
    async def test_agreement_message_with_some_scopes(self, fake, setup, agreement, optional_scopes, required_scopes):
        extra = {}

        if agreement:
            extra = {"app_user_agreement": {"agreed_at": timezone.now() + timedelta(days=1)}}

        view = authorize_view()
        scopes = optional_scopes + required_scopes
        model = await setup(
            user=1, app=1, scopes=scopes, optional_scopes=optional_scopes, required_scopes=required_scopes, **extra
        )

        request = HttpRequest()
        request.method = "GET"
        request.user = model.user
        request.path = fake.url()

        request_factory = APIRequestFactory()
        request = request_factory.get(fake.url())  # Specify the path you need

        force_authenticate(request, user=model.user)

        response = await view(request, app_slug=model.app.slug)

        if scopes:
            scopes = model.scope

        required_scopes_list = []
        optional_scopes_list = []

        if required_scopes:
            required_scopes_list = model.scope[optional_scopes : optional_scopes + required_scopes]

        if optional_scopes:
            optional_scopes_list = model.scope[:optional_scopes]

        expected = render(
            request,
            "authorize.html",
            {
                "app": model.app,
                "required_scopes": required_scopes_list,
                "optional_scopes": optional_scopes_list,
                "selected_scopes": [],
                "new_scopes": [],
                "reject_url": model.app.redirect_url + "?app=breathecode&status=rejected",
            },
        )

        if response.content != expected.content or True:
            with open("content.html", "w") as f:
                f.write(response.content.decode("utf-8"))

            with open("expected.html", "w") as f:
                f.write(expected.content.decode("utf-8"))

        assert response.content == expected.content
        assert response.status_code == expected.status_code

        content = response.content.decode("utf-8")

        if optional_scopes:
            assert content.count("Optional permissions") == 1
        else:
            assert content.count("Optional permissions") == 0

        if required_scopes:
            assert content.count("Required permissions") == 1
        else:
            assert content.count("Required permissions") == 0

        if optional_scopes and required_scopes:
            assert content.count("checked") == 6
        else:
            assert content.count("checked") == 3

        assert content.count("New</span>") == 0

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test_agreement_message_with_some_new_scopes(self, fake, setup, database):

        view = authorize_view()
        scopes = 4
        model = await setup(
            user=1,
            app=1,
            scopes=4,
            optional_scopes=2,
            required_scopes=2,
            app_user_agreement={"agreed_at": timezone.now() - timedelta(days=1)},
            optional_scope_set={"optional_scopes": [1]},
        )

        request = HttpRequest()
        request.method = "GET"
        request.user = model.user
        request.path = fake.url()

        request_factory = APIRequestFactory()
        request = request_factory.get(fake.url())

        force_authenticate(request, user=model.user)

        response = await view(request, app_slug=model.app.slug)

        if scopes:
            scopes = model.scope

        required_scopes_list = model.scope[2:4]
        optional_scopes_list = model.scope[:2]

        expected = render(
            request,
            "authorize.html",
            {
                "app": model.app,
                "required_scopes": required_scopes_list,
                "optional_scopes": optional_scopes_list,
                "selected_scopes": [model.scope[0].slug],
                "new_scopes": [x.slug for x in model.scope],
                "reject_url": model.app.redirect_url + "?app=breathecode&status=rejected",
            },
        )

        if response.content != expected.content or True:
            with open("content.html", "w") as f:
                f.write(response.content.decode("utf-8"))

            with open("expected.html", "w") as f:
                f.write(expected.content.decode("utf-8"))

        assert response.content == expected.content
        assert response.status_code == expected.status_code

        content = response.content.decode("utf-8")

        assert content.count("Optional permissions") == 1
        assert content.count("Required permissions") == 1
        assert content.count("checked") == 3
        assert content.count("New</span>") == 4


class TestPost:

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    @pytest.mark.parametrize("value", [None, "https://www.google.com"])
    async def test_no_auth(self, fake, value):
        view = authorize_view(login_url=value)
        request = HttpRequest()
        request.method = "POST"
        request.path = fake.url()

        response = await view(request, app_slug=fake.slug())
        assert response.status_code == 302
        assert response.content == b""

        if value is None:
            value = os.getenv("LOGIN_URL")

        assert response.url == value + "?url=" + urllib.parse.quote(encode(request.get_full_path()))

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    @pytest.mark.parametrize(
        "value, get_language, translations",
        [
            (
                None,
                None,
                {
                    "title": "Not found",
                    "description": "The app was not found",
                    "btn": "Go back",
                },
            ),
            (
                "https://www.google.com",
                get_es_translations,
                {
                    "title": "No encontrado",
                    "description": "La app no fue encontrada",
                    "btn": "Volver",
                },
            ),
            (
                "https://manageyourpig.com",
                get_en_translations,
                {
                    "title": "Not found",
                    "description": "The app was not found",
                    "btn": "Go back",
                },
            ),
        ],
    )
    async def test_app_not_found(self, fake, setup, value, get_language, translations):

        view = authorize_view(app_url=value, get_language=get_language)
        request = HttpRequest()
        request.method = "POST"
        model = await setup(user=1)
        request.user = model.user
        request.path = fake.url()

        request_factory = APIRequestFactory()
        request = request_factory.post(fake.url())  # Specify the path you need

        force_authenticate(request, user=model.user)

        response = await view(request, app_slug=fake.slug())

        if value is None:
            value = os.getenv("APP_URL")

        expected = render(
            request,
            "app-not-found.html",
            {
                "app_url": value,
                **translations,
            },
            status=404,
        )

        assert response.content == expected.content
        assert response.status_code == expected.status_code

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test_agreement_message_without_any_scope(self, fake, database, setup):

        view = authorize_view()
        request = HttpRequest()
        request.method = "POST"
        model = await setup(user=1, app=1)
        request.user = model.user
        request.path = fake.url()

        request_factory = APIRequestFactory()
        request = request_factory.post(fake.url())  # Specify the path you need

        force_authenticate(request, user=model.user)

        response = await view(request, app_slug=model.app.slug)
        expected = b""

        if response.content != expected or True:
            with open("content.html", "w") as f:
                f.write(response.content.decode("utf-8"))

            with open("expected.html", "w") as f:
                f.write(expected.decode("utf-8"))

        assert response.content == expected
        assert response.status_code == 302
        assert response.url == model.app.redirect_url + "?app=breathecode&status=authorized"

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    @pytest.mark.parametrize("agreement, optional_scopes, required_scopes", [(True, 3, 3), (False, 0, 3), (True, 3, 0)])
    async def test_agreement_message_with_some_scopes(self, fake, setup, agreement, optional_scopes, required_scopes):
        extra = {}

        if agreement:
            extra = {"app_user_agreement": {"agreed_at": timezone.now() + timedelta(days=1)}}

        view = authorize_view()
        scopes = optional_scopes + required_scopes
        model = await setup(
            user=1, app=1, scopes=scopes, optional_scopes=optional_scopes, required_scopes=required_scopes, **extra
        )

        request = HttpRequest()
        request.method = "POST"
        request.user = model.user
        request.path = fake.url()

        request_factory = APIRequestFactory()
        request = request_factory.post(fake.url())  # Specify the path you need

        force_authenticate(request, user=model.user)

        response = await view(request, app_slug=model.app.slug)
        expected = b""

        if response.content != expected or True:
            with open("content.html", "w") as f:
                f.write(response.content.decode("utf-8"))

            with open("expected.html", "w") as f:
                f.write(expected.decode("utf-8"))

        assert response.content == expected
        assert response.status_code == 302
        assert response.url == model.app.redirect_url + "?app=breathecode&status=authorized"

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test_agreement_message_with_some_new_scopes(self, fake, setup, database):

        view = authorize_view()
        model = await setup(
            user=1,
            app=1,
            scopes=4,
            optional_scopes=2,
            required_scopes=2,
            app_user_agreement={"agreed_at": timezone.now() - timedelta(days=1)},
            optional_scope_set={"optional_scopes": [1]},
        )

        request = HttpRequest()
        request.method = "POST"
        request.user = model.user
        request.path = fake.url()

        request_factory = APIRequestFactory()
        request = request_factory.post(fake.url())

        force_authenticate(request, user=model.user)

        response = await view(request, app_slug=model.app.slug)
        expected = b""

        if response.content != expected or True:
            with open("content.html", "w") as f:
                f.write(response.content.decode("utf-8"))

            with open("expected.html", "w") as f:
                f.write(expected.decode("utf-8"))

        assert response.content == expected
        assert response.status_code == 302
        assert response.url == model.app.redirect_url + "?app=breathecode&status=authorized"
