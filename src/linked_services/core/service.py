from __future__ import annotations

from types import TracebackType
from typing import Any, Coroutine, Optional, Type

import aiohttp
from asgiref.sync import sync_to_async
from django.http import HttpResponse, StreamingHttpResponse

from linked_services.core.settings import get_setting

__all__ = ["Service"]

LIBRARIES = {
    "requests": False,
    "aiohttp": False,  # no implemented yet
    "httpx": False,
}

try:
    import requests

    LIBRARIES["requests"] = True

except ImportError:
    pass

try:
    from aiohttp.client_reqrep import ClientResponse

    LIBRARIES["aiohttp"] = True

except ImportError:
    pass

try:
    import httpx  # noqa: F401

    LIBRARIES["httpx"] = True

except ImportError:
    pass


class Unknown:
    pass


if LIBRARIES["requests"]:

    class SyncService:

        def __enter__(self) -> "Service":

            self.sync = True

            if isinstance(self.app_pk, self._get_app_cls()):
                self.app = self.app_pk
                return self

            try:
                self.app = self._get_app(self.app_pk)

            except Exception:
                raise AppNotFound(f"App {self.app_pk} not found")

            return self

        def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_val: Optional[BaseException],
            exc_tb: Optional[TracebackType],
        ) -> None:
            pass

        def _sync_proxy(self, response: requests.Response, stream: bool) -> StreamingHttpResponse:
            header_keys = [x for x in response.headers.keys() if x not in self.banned_keys]

            if stream:
                resource = StreamingHttpResponse(
                    response.raw,
                    status=response.status_code,
                    reason=response.reason,
                )

                for header in header_keys:
                    resource[header] = response.headers[header]

                return resource

            headers = {}

            for header in header_keys:
                headers[header] = response.headers[header]

            return HttpResponse(response.content, status=response.status_code, headers=headers)

        def _sync_get(self, url, params=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)

            if self.sync is False:
                params = kwargs.pop("params", None)

            headers = self._authenticate("get", params=params, **kwargs)
            res = requests.get(url, params=params, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        def _sync_options(self, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("options", **kwargs)
            res = requests.options(url, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        def _sync_head(self, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("head", **kwargs)
            res = requests.head(url, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        def _sync_post(self, url, data=None, json=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("post", data=data, json=json, **kwargs)
            res = requests.post(url, data=data, json=json, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        def _sync_webhook(self, url, data=None, json=None, **kwargs):
            url = self.app.webhook_url
            headers = self._authenticate("post", data=data, json=json, **kwargs)
            res = requests.post(url, data=data, json=json, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        def _sync_put(self, url, data=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("put", data=data, **kwargs)
            res = requests.put(url, data=data, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        def _sync_patch(self, url, data=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("patch", data=data, **kwargs)
            res = requests.patch(url, data=data, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        def _sync_delete(self, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("delete", **kwargs)
            res = requests.delete(url, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        def _sync_request(self, method, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate(method, **kwargs)
            res = requests.request(method, url, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

else:

    class SyncService:
        pass


if LIBRARIES["aiohttp"]:

    class AsyncService:

        async def __aenter__(self) -> "Service":

            self.sync = False

            if isinstance(self.app_pk, self._get_app_cls()):
                self.app = self.app_pk

            else:
                self.app = await sync_to_async(self._get_app)(self.app_pk)

            self.session = aiohttp.ClientSession()

            # this should be extended
            await self.session.__aenter__()

            return self

        async def __aexit__(self, *args, **kwargs) -> None:
            for obj in self.to_close:
                await obj.__aexit__(*args, **kwargs)

            await self.session.__aexit__(*args, **kwargs)

        # django does not support StreamingHttpResponse with aiohttp due to django would have to close the response
        async def _async_proxy(self, response: Coroutine[Any, Any, ClientResponse]) -> HttpResponse:
            r = await response

            header_keys = [x for x in r.headers.keys() if x not in self.banned_keys]

            headers = {}
            for header in header_keys:
                headers[str(header)] = r.headers[header]

            return HttpResponse(await r.content.read(), status=r.status, headers=headers)

        def _async_get(self, url, params=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            params = kwargs.pop("params", None)
            headers = self._authenticate("get", params=params, **kwargs)

            obj = self.session.get(url, params=params, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._aproxy(res)

            return res

        def _async_options(self, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("options", **kwargs)

            obj = self.session.options(url, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._aproxy(res)

            return res

        def _async_head(self, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("head", **kwargs)

            obj = self.session.head(url, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._aproxy(res)

            return res

        def _async_post(self, url, data=None, json=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("post", data=data, json=json, **kwargs)

            obj = self.session.post(url, data=data, json=json, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._aproxy(res)

            return res

        def _async_webhook(self, url, data=None, json=None, **kwargs):
            url = self.app.webhook_url
            headers = self._authenticate("post", data=data, json=json, **kwargs)

            obj = self.session.post(url, data=data, json=json, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._aproxy(res)

            return res

        def _async_put(self, url, data=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("put", data=data, **kwargs)

            obj = self.session.put(url, data=data, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._aproxy(res)

            return res

        def _async_patch(self, url, data=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("patch", data=data, **kwargs)

            obj = self.session.patch(url, data=data, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._aproxy(res)

            return res

        def _async_delete(self, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("delete", **kwargs)

            obj = self.session.delete(url, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._aproxy(res)

            return res

        def _async_request(self, method, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate(method, **kwargs)

            obj = self.session.request(method, url, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._aproxy(res)

            return res

elif LIBRARIES["requests"]:

    class AsyncService:

        async def __aenter__(self) -> "Service":

            self.sync = True

            if isinstance(self.app_pk, self._get_app_cls()):
                self.app = self.app_pk
                return self

            self.app = await sync_to_async(self._get_app)(self.app_pk)

            return self

        async def __aexit__(self, *args, **kwargs) -> None:
            pass

        def _async_proxy(self, response: requests.Response, stream: bool) -> StreamingHttpResponse:
            header_keys = [x for x in response.headers.keys() if x not in self.banned_keys]

            if stream:
                resource = StreamingHttpResponse(
                    response.raw,
                    status=response.status_code,
                    reason=response.reason,
                )

                for header in header_keys:
                    resource[header] = response.headers[header]

                return resource

            headers = {}

            for header in header_keys:
                headers[header] = response.headers[header]

            return HttpResponse(response.content, status=response.status_code, headers=headers)

        async def _async_get(self, url, params=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)

            if self.sync is False:
                params = kwargs.pop("params", None)

            headers = self._authenticate("get", params=params, **kwargs)
            res = requests.get(url, params=params, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        async def _async_options(self, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("options", **kwargs)
            res = requests.options(url, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        async def _async_head(self, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("head", **kwargs)
            res = requests.head(url, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        async def _async_post(self, url, data=None, json=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("post", data=data, json=json, **kwargs)
            res = requests.post(url, data=data, json=json, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        async def _async_webhook(self, url, data=None, json=None, **kwargs):
            url = self.app.webhook_url
            headers = self._authenticate("post", data=data, json=json, **kwargs)
            res = requests.post(url, data=data, json=json, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        async def _async_put(self, url, data=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("put", data=data, **kwargs)
            res = requests.put(url, data=data, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        async def _async_patch(self, url, data=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("patch", data=data, **kwargs)
            res = requests.patch(url, data=data, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        async def _async_delete(self, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("delete", **kwargs)
            res = requests.delete(url, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

        async def _async_request(self, method, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate(method, **kwargs)
            res = requests.request(method, url, **kwargs, headers=headers)

            if self.proxy:
                return self._proxy(res, kwargs.get("stream", False))

            return res

else:

    class AsyncService:
        pass


class Service(SyncService, AsyncService):
    session: aiohttp.ClientSession

    def __init__(
        self,
        app_pk: str | int,
        user_pk: Optional[str | int] = None,
        *,
        mode: Optional[str] = None,
        proxy: bool = False,
    ):
        self.app_pk = app_pk
        self.user_pk = user_pk
        self.mode = mode
        self.to_close = []
        self.proxy = proxy
        self.banned_keys = [
            "Transfer-Encoding",
            "Content-Encoding",
            "Keep-Alive",
            "Connection",
            "Content-Length",
            "Upgrade",
        ]

    def _get_app_cls(self) -> Type[Unknown]:
        raise NotImplementedError("This method should be implemented")

    def _get_app(self, pk: str | int) -> Unknown:
        raise NotImplementedError("This method should be implemented")

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
        raise NotImplementedError("This method should be implemented")

    def _get_jwt(self, app: Any, user_id: Optional[int] = None, reverse: bool = False) -> str:
        raise NotImplementedError("This method should be implemented")

    def _sign(self, method, params=None, data=None, json=None, **kwargs) -> requests.Request:
        # from breathecode.authenticate.actions import get_signature

        headers = kwargs.pop("headers", {})
        headers.pop("Authorization", None)

        sign, now = self._get_signature(
            self.app,
            self.user_pk,
            method=method,
            params=params,
            body=data if data is not None else json,
            headers=headers,
        )

        whoamy = get_setting("name")
        headers["Authorization"] = (
            f"Signature App={whoamy}," f"Nonce={sign}," f'SignedHeaders={";".join(headers.keys())},' f"Date={now}"
        )

        return headers

    def _jwt(self, method, **kwargs) -> requests.Request:
        # from .actions import get_jwt

        headers = kwargs.pop("headers", {})

        token = self._get_jwt(self.app, self.user_pk)

        whoamy = get_setting("name")
        headers["Authorization"] = f"Link App={whoamy}," f"Token={token}"

        return headers

    def _authenticate(self, method, params=None, data=None, json=None, **kwargs) -> requests.Request:
        if self.mode == "signature" or self.app.strategy == "SIGNATURE":
            return self._sign(method, params=params, data=data, json=json, **kwargs)

        elif self.mode == "jwt" or self.app.strategy == "JWT":
            return self._jwt(method, **kwargs)

        raise Exception("Strategy not implemented")

    def _fix_url(self, url):
        if url[0] != "/":
            url = f"/{url}"

        return url

    def get(self, url, params=None, **kwargs):
        if self.sync:
            return self._sync_get(url, params=params, **kwargs)

        return self._async_get(url, params=params, **kwargs)

    def options(self, url, **kwargs):
        if self.sync:
            return self._sync_options(url, **kwargs)

        return self._async_options(url, **kwargs)

    def head(self, url, **kwargs):
        if self.sync:
            return self._sync_head(url, **kwargs)

        return self._async_head(url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        if self.sync:
            return self._sync_post(url, data=data, json=json, **kwargs)

        return self._async_post(url, data=data, json=json, **kwargs)

    def webhook(self, url, data=None, json=None, **kwargs):
        if self.sync:
            return self._sync_webhook(url, data=data, json=json, **kwargs)

        return self._async_webhook(url, data=data, json=json, **kwargs)

    def put(self, url, data=None, **kwargs):
        if self.sync:
            return self._sync_put(url, data=data, **kwargs)

        return self._async_put(url, data=data, **kwargs)

    def patch(self, url, data=None, **kwargs):
        if self.sync:
            return self._sync_patch(url, data=data, **kwargs)

        return self._async_patch(url, data=data, **kwargs)

    def delete(self, url, **kwargs):
        if self.sync:
            return self._sync_delete(url, **kwargs)

        return self._async_delete(url, **kwargs)

    def request(self, method, url, **kwargs):
        if self.sync:
            return self._sync_request(method, url, **kwargs)

        return self._async_request(method, url, **kwargs)


class AppNotFound(Exception):
    pass
