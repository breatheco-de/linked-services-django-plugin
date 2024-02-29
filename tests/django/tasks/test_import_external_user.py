import logging
import random
from datetime import datetime
from unittest.mock import MagicMock, call

import pytest

from linked_services.core.settings import set_settings
from linked_services.django.tasks import check_credentials, import_external_user


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    set_settings(app_name="breathecode")

    monkeypatch.setattr("logging.Logger.error", MagicMock())
    monkeypatch.setattr("linked_services.django.tasks.check_credentials.delay", MagicMock())
    yield


def test_no_invites(database, get_json_obj):
    import_external_user.delay(1)

    assert database.list_of("linked_services.FirstPartyCredentials") == []
    assert database.list_of("auth.User") == []

    assert logging.Logger.error.call_args_list == [
        call("Webhook not found", exc_info=True),
    ]
    assert check_credentials.delay.call_args_list == []


def test_bad_fields(database, get_json_obj):
    model = database.create(first_party_webhook_log=1)

    import_external_user.delay(1)

    assert database.list_of("linked_services.FirstPartyCredentials") == []
    assert database.list_of("auth.User") == []

    assert logging.Logger.error.call_args_list == [
        call(
            "Webhook unknown requires a data field as json with the following "
            "fields: data.id, data.email, data.first_name, data.last_name"
        ),
    ]
    assert check_credentials.delay.call_args_list == []


def test_user_created(database, get_json_obj, fake):
    id = random.randint(1, 100)
    email = fake.email()
    first_name = fake.first_name()
    last_name = fake.last_name()
    model = database.create(
        app=1,
        first_party_webhook_log={
            "data": {
                "id": id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            },
            "user_id": 1,
        },
    )

    import_external_user.delay(1)

    assert database.list_of("linked_services.FirstPartyCredentials") == [
        {
            "health_status": {},
            "id": 1,
            "app": {
                model.app.slug: id,
            },
            "user_id": 1,
        },
    ]
    db = [x for x in database.list_of("auth.User") if isinstance(x.pop("date_joined"), datetime)]
    assert db == [
        {
            "email": email,
            "first_name": first_name,
            "id": 1,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "last_login": None,
            "last_name": last_name,
            "password": "",
            "username": email,
        },
    ]

    assert logging.Logger.error.call_args_list == []
    assert check_credentials.delay.call_args_list == [call(1, [model.app.slug])]
