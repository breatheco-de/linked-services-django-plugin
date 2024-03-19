from unittest.mock import AsyncMock, call

import pytest

from linked_services.core.settings import set_settings
from linked_services.django import actions


@pytest.fixture(autouse=True)
def patch(db, monkeypatch):
    from linked_services.django.actions import reset_app_cache

    m1 = AsyncMock()

    set_settings(app_name="breathecode")
    reset_app_cache()

    monkeypatch.setattr("linked_services.django.tasks.check_credentials.delay", AsyncMock())
    monkeypatch.setattr("linked_services.django.actions.acreate_user", m1)

    yield m1


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("user", [0, 1])
async def test_no_first_party_credentials(patch, fake, database, user):
    app_slug = fake.slug()
    await database.acreate(user=user, app={"slug": app_slug})
    v = fake.slug()
    create_use_mock = patch
    create_use_mock.return_value = v

    res = await actions.aget_user(app_slug, 1)

    assert res == v
    assert actions.acreate_user.call_args_list == [call(app_slug, 1)]
    assert await database.alist_of("linked_services.FirstPartyCredentials") == []


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test_with_first_party_credentials(patch, fake, database, get_json_obj):
    app_slug = fake.slug()
    model = await database.acreate(user=1, first_party_credentials={"app": {app_slug: 1}})

    v = fake.slug()
    create_use_mock = patch
    create_use_mock.return_value = v

    res = await actions.aget_user(app_slug, 1)

    assert res == model.user
    assert actions.acreate_user.call_args_list == []
    assert await database.alist_of("linked_services.FirstPartyCredentials") == [
        get_json_obj(model.first_party_credentials)
    ]
