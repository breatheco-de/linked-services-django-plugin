# Rest frameworks

You could implement a new REST framework extending `linked_services.core.service.Service`.

## Methods

- `__enter__`: called when it gets entered into an sync context.
- `__aenter__`: called when it gets entered into an async context.
- `_get_app_cls`: called when it needs to retrieve the application model class.
- `_get_app`: called when it needs to retrieve an application instance.
- `_get_signature`: called when it needs to retrieve a signature.
- `_get_jwt`: called when it needs to retrieve a JWT.

## Example

Implementing `djangorestframework`.

```py
from typing import Any, Optional, Type

from django.core.exceptions import SynchronousOnlyOperation

from linked_services.core.exceptions import ValidationException
from linked_services.core.service import AppNotFound
from linked_services.core.service import Service as BaseService
from linked_services.django.actions import get_app
from linked_services.django.models import App

has_sync = hasattr(BaseService, "__enter__")
has_async = hasattr(BaseService, "__aenter__")


class Service(BaseService):
    if has_sync:

        def __enter__(self) -> "Service":
            try:
                return super().__enter__()

            except Exception:
                if self.proxy:
                    raise ValidationException(f"App {self.app_pk} not found", code=404, slug="app-not-found")

                raise AppNotFound(f"App {self.app_pk} not found")

    if has_async:

        async def __aenter__(self) -> "Service":

            try:
                return await super().__aenter__()

            except SynchronousOnlyOperation:
                raise ValidationException(
                    "Async is not supported by the worker",
                    code=500,
                    slug="no-async-support",
                )

            except Exception:
                if self.proxy:
                    raise ValidationException(f"App {self.app_pk} not found", code=404, slug="app-not-found")

                raise AppNotFound(f"App {self.app_pk} not found")

    def _get_app_cls(self) -> Type[App]:
        return App

    def _get_app(self, pk: str | int) -> App:
        return get_app(pk)

    def _get_signature(
        self,
        app: Any,
        user_id: Optional[int] = None,
        *,
        method: str = "get",
        params: Optional[dict] = None,
        body: Optional[dict] = None,
        headers: Optional[dict] = None,
        reverse: bool = False,
    ) -> tuple[str, str]:
        from .actions import get_signature

        return get_signature(app, user_id, method=method, params=params, body=body, headers=headers, reverse=reverse)

    def _get_jwt(self, app: Any, user_id: Optional[int] = None, reverse: bool = False) -> str:
        from .actions import get_jwt

        return get_jwt(app, user_id, reverse=reverse)

```
