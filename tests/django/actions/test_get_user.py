import secrets
from unittest.mock import MagicMock, call

import pytest

from linked_services.core.settings import set_settings
from linked_services.django import actions


@pytest.fixture(autouse=True)
def patch(db, monkeypatch):
    from linked_services.django.actions import reset_app_cache

    m1 = MagicMock()

    set_settings(app_name="breathecode")
    reset_app_cache()

    monkeypatch.setattr("linked_services.django.tasks.check_credentials.delay", MagicMock())
    monkeypatch.setattr("linked_services.django.actions.create_user", m1)

    yield m1


@pytest.mark.parametrize("user", [0, 1])
async def test_no_first_party_credentials(patch, fake, database, user):
    database.create(user=user)
    v = fake.slug()
    create_use_mock = patch
    create_use_mock.return_value = v

    res = actions.get_user("breathecode", 1)

    assert res == v
    assert actions.create_user.call_args_list == [call("breathecode", 1)]
    assert database.list_of("linked_services.FirstPartyCredentials") == []


async def test_with_first_party_credentials(patch, fake, database, get_json_obj):
    app_slug = fake.slug()
    model = database.acreate(
        user=1,
        first_party_credentials={
            "app": {app_slug: 1},
        },
    )

    v = fake.slug()
    create_use_mock = patch
    create_use_mock.return_value = v

    res = actions.get_user(app_slug, 1)

    assert res == model.user
    assert actions.create_user.call_args_list == []
    assert database.list_of("linked_services.FirstPartyCredentials") == [get_json_obj(model.first_party_credentials)]
