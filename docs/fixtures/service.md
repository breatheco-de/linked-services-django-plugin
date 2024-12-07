# service

Set of utilities for formatting values.

## `sign_jwt`

Set Json Web Token in the request.

### Arguments

- `client`: a `capy.Client` instance.
- `app`: a `linked_services.django.models.App` instance.
- `user_id`: an `user.id` as `int` or `None`.
- `reverse`: if `True`, mark the tested app as the emitter of the request, otherwise mark it as the receiver.

### Example

```py
import capyc.pytest as capy
import linked_services.pytest as linked_services
from linked_services.django.models import App


def test_sign_request(client: capy.Client, service: linked_services.Service):
    app = App.objects.first()
    res = service.sign_jwt(client, app)
    assert res is None


def test_sign_request_as_user(client: capy.Client, service: linked_services.Service):
    app = App.objects.first()
    res = service.sign_jwt(client, app, user_id=1)
    assert res is None


def test_reverse_sign_request(client: capy.Client, service: linked_services.Service):
    app = App.objects.first()
    res = service.sign_jwt(client, app, reverse=True)
    assert res is None


def test_reverse_sign_request_as_user(client: capy.Client, service: linked_services.Service):
    app = App.objects.first()
    res = service.sign_jwt(client, app, user_id=1, reverse=True)
    assert res is None

```
