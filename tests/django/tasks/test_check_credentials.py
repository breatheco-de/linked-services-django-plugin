import logging
import random
from unittest.mock import MagicMock, call, patch

import pytest

from linked_services.core.settings import set_settings
from linked_services.django.service import Service
from linked_services.django.tasks import check_credentials


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    set_settings(app_name="breathecode")
    monkeypatch.setattr("logging.Logger.error", MagicMock())

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


def test_nothing_to_check(database, get_json_obj):
    check_credentials.delay(1)

    assert database.list_of("linked_services.FirstPartyCredentials") == []

    assert logging.Logger.error.call_args_list == [
        call("Nothing to check", exc_info=True),
    ]


# you should parametrize these tests to check with another apps


def test_not_found(database, get_json_obj):
    check_credentials.delay(1, ["rigobot"])

    assert database.list_of("linked_services.FirstPartyCredentials") == []

    assert logging.Logger.error.call_args_list == [
        call("FirstPartyCredentials not found", exc_info=True),
    ]


def test_if_rigobot_id_is_null_remove_its_related_log(database, get_json_obj):
    with patch("linked_services.django.tasks.check_credentials.delay", MagicMock()):
        model = database.create(
            first_party_credentials={
                "app": {},
                "health_status": {
                    "rigobot": {
                        "random": "value",
                    },
                },
            }
        )
    check_credentials.delay(1, ["rigobot"])

    assert database.list_of("linked_services.FirstPartyCredentials") == [
        {
            **get_json_obj(model.first_party_credentials),
            "health_status": {},
        },
    ]

    assert logging.Logger.error.call_args_list == []


def test_app_not_found(database, get_json_obj):
    id = random.randint(1, 100)
    with patch("linked_services.django.tasks.check_credentials.delay", MagicMock()):
        model = database.create(
            first_party_credentials={
                "app": {
                    "rigobot": id,
                },
            },
        )

    check_credentials.delay(1, ["rigobot"])

    assert database.list_of("linked_services.FirstPartyCredentials") == [
        {
            **get_json_obj(model.first_party_credentials),
            "app": {},
            "health_status": {
                "rigobot": {
                    "id": id,
                    "status": "APP_NOT_FOUND",
                },
            },
        },
    ]

    assert logging.Logger.error.call_args_list == []


@pytest.mark.parametrize("status,data", [(404, []), (200, {}), (200, [])])
def test_not_found_on_rigobot(database, get_json_obj, patch_request, status, data):
    patch_request(data, status)
    id = random.randint(1, 100)

    with patch("linked_services.django.tasks.check_credentials.delay", MagicMock()):
        model = database.create(
            first_party_credentials={
                "app": {
                    "rigobot": id,
                },
            },
            app={"slug": "rigobot"},
        )

    check_credentials.delay(1, ["rigobot"])

    assert database.list_of("linked_services.FirstPartyCredentials") == [
        {
            **get_json_obj(model.first_party_credentials),
            "health_status": {
                "rigobot": {
                    "id": id,
                    "status": "NOT_FOUND",
                },
            },
            "app": {},
        },
    ]

    assert logging.Logger.error.call_args_list == []
    assert Service.get.call_args_list == [
        call(f"/v1/auth/app/user/?email={model.user.email}&id={id}"),
    ]


def test_found_on_rigobot(database, get_json_obj, patch_request):
    patch_request([1], 200)
    id = random.randint(1, 100)

    with patch("linked_services.django.tasks.check_credentials.delay", MagicMock()):
        model = database.create(
            first_party_credentials={
                "app": {
                    "rigobot": id,
                },
            },
            app={"slug": "rigobot"},
        )

    check_credentials.delay(1, ["rigobot"])

    assert database.list_of("linked_services.FirstPartyCredentials") == [
        {
            **get_json_obj(model.first_party_credentials),
            "health_status": {
                "rigobot": {
                    "id": id,
                    "status": "HEALTHY",
                },
            },
            "app": {"rigobot": id},
        },
    ]

    assert logging.Logger.error.call_args_list == []
    assert Service.get.call_args_list == [
        call(f"/v1/auth/app/user/?email={model.user.email}&id={id}"),
    ]
