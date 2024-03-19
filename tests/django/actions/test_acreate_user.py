import random
import secrets
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from linked_services.core.exceptions import ValidationException
from linked_services.core.service import AppNotFound
from linked_services.core.settings import set_settings
from linked_services.django import actions


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    set_settings(app_name="breathecode")
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    monkeypatch.setattr("linked_services.django.tasks.check_credentials.delay", MagicMock())

    yield


class ResponseMock:

    def __init__(self, data, status):
        self.status_code = status
        self.data = data

    async def json(self):
        return self.data


@pytest.fixture
def patch_request(monkeypatch):

    def wrapper(data, status):
        monkeypatch.setattr(
            "linked_services.core.service.Service.get", AsyncMock(return_value=ResponseMock(data, status))
        )
        return MagicMock()

    yield wrapper


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test_app_not_found(fake, database):
    app_slug = fake.slug()

    with pytest.raises(AppNotFound):
        await actions.acreate_user(app_slug, 1)

    assert await database.alist_of("linked_services.FirstPartyCredentials") == []
    assert await database.alist_of("auth.User") == []


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test_required_fields_not_provided(fake, database, patch_request):
    patch_request({}, 200)
    app_slug = fake.slug()
    await database.acreate(
        app={
            "slug": app_slug,
            "private_key": secrets.token_hex(64),
        }
    )

    with pytest.raises(ValidationException, match="id not provided, username not provided, email not provided"):
        await actions.acreate_user(app_slug, 1)

    assert await database.alist_of("linked_services.FirstPartyCredentials") == []
    assert await database.alist_of("auth.User") == []


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("optional_fields", [{}, {"first_name": "John", "last_name": "Silla 🪑"}])
async def test_all_fine(fake, database, patch_request, optional_fields):
    data = {
        "id": random.randint(1, 100),
        "username": fake.slug(),
        "email": fake.email(),
    }
    if optional_fields:
        data.update(optional_fields)

    patch_request(data, 200)
    app_slug = fake.slug()
    await database.acreate(
        app={
            "slug": app_slug,
            "private_key": secrets.token_hex(64),
        }
    )

    await actions.acreate_user(app_slug, 1)

    assert await database.alist_of("linked_services.FirstPartyCredentials") == [
        {
            "app": {app_slug: data["id"]},
            "health_status": {},
            "id": 1,
            "user_id": 1,
        },
    ]
    users_db = [
        x
        for x in await database.alist_of("auth.User")
        if isinstance(x["date_joined"], datetime) and x.pop("date_joined")
    ]
    assert users_db == [
        {
            "email": data["email"],
            "first_name": data.get("first_name", ""),
            "id": 1,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "last_login": None,
            "last_name": data.get("last_name", ""),
            "password": "",
            "username": data["username"],
        }
    ]
