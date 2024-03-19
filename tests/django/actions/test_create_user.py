import random
import secrets
from datetime import datetime
from unittest.mock import MagicMock

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

    def json(self):
        return self.data


@pytest.fixture
def patch_request(monkeypatch):

    def wrapper(data, status):
        monkeypatch.setattr(
            "linked_services.core.service.Service.get", MagicMock(return_value=ResponseMock(data, status))
        )
        return MagicMock()

    yield wrapper


def test_app_not_found(fake, database):
    app_slug = fake.slug()

    with pytest.raises(AppNotFound):
        actions.create_user(app_slug, 1)

    assert database.list_of("linked_services.FirstPartyCredentials") == []
    assert database.list_of("auth.User") == []


def test_required_fields_not_provided(fake, database, patch_request):
    patch_request({}, 200)
    app_slug = fake.slug()
    database.create(
        app={
            "slug": app_slug,
            "private_key": secrets.token_hex(64),
        }
    )

    with pytest.raises(ValidationException, match="id not provided, username not provided, email not provided"):
        actions.create_user(app_slug, 1)

    assert database.list_of("linked_services.FirstPartyCredentials") == []
    assert database.list_of("auth.User") == []


@pytest.mark.parametrize("optional_fields", [{}, {"first_name": "John", "last_name": "Silla 🪑"}])
def test_all_fine(fake, database, patch_request, optional_fields):
    data = {
        "id": random.randint(1, 100),
        "username": fake.slug(),
        "email": fake.email(),
    }
    if optional_fields:
        data.update(optional_fields)

    patch_request(data, 200)
    app_slug = fake.slug()
    database.create(
        app={
            "slug": app_slug,
            "private_key": secrets.token_hex(64),
        }
    )

    actions.create_user(app_slug, 1)

    assert database.list_of("linked_services.FirstPartyCredentials") == [
        {
            "app": {app_slug: data["id"]},
            "health_status": {},
            "id": 1,
            "user_id": 1,
        },
    ]
    users_db = [
        x for x in database.list_of("auth.User") if isinstance(x["date_joined"], datetime) and x.pop("date_joined")
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
