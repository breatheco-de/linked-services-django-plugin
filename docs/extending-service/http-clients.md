# HTTP clients

You could write a new implementation for a HTTP client here `src/linked_services/core/service.py`.

## HTTP client preference

### Async

1. `aiohttp`.
2. `httpx`.
3. `requests`.

### Sync

1. `httpx`.
2. `requests`.

### Which are supported right now

- `aiohttp`.
- `requests`.

### `SyncService` methods

- `__enter__`: called when it gets entered into an sync context.
- `__exit__`: called when it gets exited from an sync context.
- `_sync_proxy`: called when it requires that the response be a REST framework response.
- `_sync_get`: called when it tries to do a get request, it returns a HTTP response or a Rest response.
- `_sync_options`: called when it tries to do a options request, it returns a HTTP response or a Rest response.
- `_sync_head`: called when it tries to do a head request, it returns a HTTP response or a Rest response.
- `_sync_post`: called when it tries to do a post request, it returns a HTTP response or a Rest response.
- `_sync_webhook`: called when it tries to trigger an webhook, it returns a HTTP response or a Rest response.
- `_sync_put`: called when it tries to do a put request, it returns a HTTP response or a Rest response.
- `_sync_patch`: called when it tries to do a patch request, it returns a HTTP response or a Rest response.
- `_sync_delete`: called when it tries to do a delete request, it returns a HTTP response or a Rest response.
- `_sync_request`: called when it tries to do a generic request, it returns a HTTP response or a Rest response.

### `AsyncService` methods

- `__aenter__`: called when it gets entered into an async context.
- `__aexit__`: called when it gets exited from an async context.
- `_async_proxy`: called when it requires that the response be a REST framework response.
- `_async_get`: called when it tries to do a get request, it returns a HTTP response or a Rest response.
- `_async_options`: called when it tries to do a options request, it returns a HTTP response or a Rest response.
- `_async_head`: called when it tries to do a head request, it returns a HTTP response or a Rest response.
- `_async_post`: called when it tries to do a post request, it returns a HTTP response or a Rest response.
- `_async_webhook`: called when it tries to trigger an webhook, it returns a HTTP response or a Rest response.
- `_async_put`: called when it tries to do a put request, it returns a HTTP response or a Rest response.
- `_async_patch`: called when it tries to do a patch request, it returns a HTTP response or a Rest response.
- `_async_delete`: called when it tries to do a delete request, it returns a HTTP response or a Rest response.
- `_async_request`: called when it tries to do a generic request, it returns a HTTP response or a Rest response.

### How to implement a new HTTP client

You must implement an `SyncService` and `AsyncService` for your new library.

#### Detecting your new client

First, you need to add an import test here, it will tell to the rest of the code which clients are available.

```py
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
```

#### Implementing `SyncService` and `AsyncService`

You must use `elif LIBRARIES["your-client"]:` to check if your library is available, also, you must remind each client has a different relevance, so, sort them by relevance.

#### `SyncService` example

Implementing `requests` library.

```py
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

        def _sync_proxy(self, request: Callable[[], requests.Response], stream: bool) -> StreamingHttpResponse:
            try:
                response = request()

            except Exception as e:
                raise ValidationException("Unexpected error: " + str(e), code=500, slug="unexpected-error")

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

            def request() -> requests.Response:
                return requests.get(url, params=params, **kwargs, headers=headers)

            if self.proxy:
                return self._sync_proxy(request, kwargs.get("stream", False))

            res = request()

            return res

        def _sync_options(self, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("options", **kwargs)

            def request() -> requests.Response:
                return requests.options(url, **kwargs, headers=headers)

            if self.proxy:
                return self._sync_proxy(request, kwargs.get("stream", False))

            res = request()

            return res

        def _sync_head(self, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("head", **kwargs)

            def request() -> requests.Response:
                return requests.head(url, **kwargs, headers=headers)

            if self.proxy:
                return self._sync_proxy(request, kwargs.get("stream", False))

            res = request()

            return res

        def _sync_post(self, url, data=None, json=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("post", data=data, json=json, **kwargs)

            def request() -> requests.Response:
                return requests.post(url, data=data, json=json, **kwargs, headers=headers)

            if self.proxy:
                return self._sync_proxy(request, kwargs.get("stream", False))

            res = request()

            return res

        def _sync_webhook(self, url, data=None, json=None, **kwargs):
            url = self.app.webhook_url
            headers = self._authenticate("post", data=data, json=json, **kwargs)

            def request() -> requests.Response:
                return requests.post(url, data=data, json=json, **kwargs, headers=headers)

            if self.proxy:
                return self._sync_proxy(request, kwargs.get("stream", False))

            res = request()

            return res

        def _sync_put(self, url, data=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("put", data=data, **kwargs)

            def request() -> requests.Response:
                return requests.put(url, data=data, **kwargs, headers=headers)

            if self.proxy:
                return self._sync_proxy(request, kwargs.get("stream", False))

            res = request()

            return res

        def _sync_patch(self, url, data=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("patch", data=data, **kwargs)

            def request() -> requests.Response:
                return requests.patch(url, data=data, **kwargs, headers=headers)

            if self.proxy:
                return self._sync_proxy(request, kwargs.get("stream", False))

            res = request()

            return res

        def _sync_delete(self, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("delete", **kwargs)

            def request() -> requests.Response:
                return requests.delete(url, **kwargs, headers=headers)

            if self.proxy:
                return self._sync_proxy(request, kwargs.get("stream", False))

            res = request()

            return res

        def _sync_request(self, method, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate(method, **kwargs)

            def request() -> requests.Response:
                return requests.request(method, url, **kwargs, headers=headers)

            if self.proxy:
                return self._sync_proxy(request, kwargs.get("stream", False))

            res = request()

            return res
```

#### `AsyncService` example

Implementing `aiohttp` library.

```py
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
            try:
                r = await response

            except Exception as e:
                raise ValidationException("Unexpected error: " + str(e), code=500, slug="unexpected-error")

            header_keys = [x for x in r.headers.keys() if x not in self.banned_keys]

            headers = {}
            for header in header_keys:
                headers[str(header)] = r.headers[header]

            return HttpResponse(await r.content.read(), status=r.status, headers=headers)

        def _async_get(self, url, params=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("get", params=params, **kwargs)

            obj = self.session.get(url, params=params, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._async_proxy(res)

            return res

        def _async_options(self, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("options", **kwargs)

            obj = self.session.options(url, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._async_proxy(res)

            return res

        def _async_head(self, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("head", **kwargs)

            obj = self.session.head(url, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._async_proxy(res)

            return res

        def _async_post(self, url, data=None, json=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("post", data=data, json=json, **kwargs)

            obj = self.session.post(url, data=data, json=json, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._async_proxy(res)

            return res

        def _async_webhook(self, url, data=None, json=None, **kwargs):
            url = self.app.webhook_url
            headers = self._authenticate("post", data=data, json=json, **kwargs)

            obj = self.session.post(url, data=data, json=json, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._async_proxy(res)

            return res

        def _async_put(self, url, data=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("put", data=data, **kwargs)

            obj = self.session.put(url, data=data, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._async_proxy(res)

            return res

        def _async_patch(self, url, data=None, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("patch", data=data, **kwargs)

            obj = self.session.patch(url, data=data, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._async_proxy(res)

            return res

        def _async_delete(self, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate("delete", **kwargs)

            obj = self.session.delete(url, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._async_proxy(res)

            return res

        def _async_request(self, method, url, **kwargs):
            url = self.app.app_url + self._fix_url(url)
            headers = self._authenticate(method, **kwargs)

            obj = self.session.request(method, url, **kwargs, headers=headers)
            self.to_close.append(obj)

            res = obj.__aenter__()

            # wraps client response to be used within django views
            if self.proxy:
                return self._async_proxy(res)

            return res
```
