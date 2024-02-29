"""
Test /academy/cohort
"""

from unittest.mock import MagicMock, call, patch

import pytest
from django.core.management.base import OutputWrapper

from linked_services.management.commands.sign_jwt import Command


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr("django.core.management.base.OutputWrapper.write", MagicMock())
    yield


# When: No app
# Then: Shouldn't do anything
def test_no_app(database, fake):
    command = Command()
    result = command.handle(app="1", user=None)

    assert result is None
    assert database.list_of("linked_services.App") == []
    assert OutputWrapper.write.call_args_list == [
        call("App 1 not found"),
    ]


# When: With app
# Then: Print the token
def test_sign_jwt(database, fake, get_json_obj, monkeypatch):
    private_key = fake.slug()
    model = database.create(app={"private_key": private_key.encode().hex()})

    command = Command()

    token = fake.slug()
    monkeypatch.setattr("jwt.encode", MagicMock(return_value=token))

    result = command.handle(app="1", user=None)

    assert result is None
    assert database.list_of("linked_services.App") == [get_json_obj(model.app)]
    assert OutputWrapper.write.call_args_list == [
        call(f"Authorization: Link App={model.app.slug}," f"Token={token}"),
    ]
