"""
Test /academy/cohort
"""

from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest
from django.core.management.base import OutputWrapper

from linked_services.management.commands.sign_request import Command


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr("django.core.management.base.OutputWrapper.write", MagicMock())
    yield


"""
🔽🔽🔽 With zero Profile
"""


# When: No app
# Then: Shouldn't do anything
def test_no_app(database):
    command = Command()
    result = command.handle(app="1", user=None, method=None, params=None, body=None, headers=None)

    assert result is None
    assert database.list_of("linked_services.App") == []
    assert OutputWrapper.write.call_args_list == [
        call("App 1 not found"),
    ]


# When: With app
# Then: Print the signature
def test_sign_jwt(database, fake, monkeypatch, get_json_obj):
    headers = {
        fake.slug(): fake.slug(),
        fake.slug(): fake.slug(),
        fake.slug(): fake.slug(),
    }
    private_key = fake.slug()
    model = database.create(app={"private_key": private_key.encode().hex()})

    command = Command()

    token = fake.slug()
    d = datetime(2023, 8, 3, 4, 2, 58, 992939)

    monkeypatch.setattr("hmac.HMAC.hexdigest", MagicMock(return_value=token))
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=d))

    result = command.handle(
        app="1",
        user=None,
        method=f"{headers}",
        params=f"{headers}",
        body=f"{headers}",
        headers=f"{headers}",
    )

    assert result is None
    assert database.list_of("linked_services.App") == [get_json_obj(model.app)]
    assert OutputWrapper.write.call_args_list == [
        call(
            f"Authorization: Signature App={model.app.slug},"
            f"Nonce={token},"
            f'SignedHeaders={";".join(headers.keys())},'
            f"Date={d.isoformat()}"
        ),
    ]
