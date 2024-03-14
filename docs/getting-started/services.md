# Services

`Service` resolves automatically what is the credentials required by its pairwise. It could returns a HTTP response or a Rest response, depending it's used as proxy or it does not.

## Examples

### Sync

You could want to use `Service` within a synchronous context if your framework does not support asynchronous operations or if your are using Celery.

#### Proxy

```py
from rest_framework.views import APIView
from linked_services.django.service import Service


class MeCodeRevisionView(APIView):

    def get(self, request, task_id=None):
        with Service('rigobot', request.user.id, proxy=True) as s:
            return s.get('/v1/finetuning/me/coderevision', params=request.GET, stream=True)
```

#### Client

```py
from linked_services.django.service import Service


def my_func(url, whatchers=None):
    if whatchers is None:
        whatchers = []

    with Service('rigobot') as s:
        if task.task_status == 'DONE':
            response = s.post('/v1/finetuning/me/repository/',
                                json={
                                    'url': url,
                                    'watchers': whatchers,
                                })
            data = response.json()
            print(data)
```

### Async

This is the most convenient implementation of the service, because it blocks until the response is received. It's not compatible with celery yet.

#### Proxy

```py
from adrf.views import APIView
from linked_services.django.service import Service


class MeCodeRevisionView(APIView):

    def get(self, request, task_id=None):
        async with Service('rigobot', request.user.id, proxy=True) as s:
            return await s.get('/v1/finetuning/me/coderevision', params=request.GET)
```

#### Client

```py
from linked_services.django.service import Service


async def my_func(url, whatchers=None):
    if whatchers is None:
        whatchers = []

    async with Service('rigobot') as s:
        if task.task_status == 'DONE':
            response = await s.post('/v1/finetuning/me/repository/',
                                json={
                                    'url': url,
                                    'watchers': whatchers,
                                })
            data = response.json()
            print(data)
```

## Arguments

- `app_pk`: it could be the slug or the id of the application.
- `user_pk`: it could be the username or the id of the user. Default is `None`.
- `mode`: it can be one of the following, jwt or signature. Default is `jwt`.
- `proxy`: if it's `True`, it returns a HTTP response in the chosen framework, like `djangorestframework`.

## Returns

- If `Proxy is True`: returns a HTTP response of the chosen HTTP library.
- If `Proxy is not True`: returns a HTTP response of the chosen REST library.

## Library preferences

### `sync`

1. `httpx`
2. `requests`

### `async`

1. `aiohttp`
2. `httpx`
3. `requests`

## Which HTTP libraries are supported right now

- `aiohttp`
- `requests`

## Which REST libraries are supported right now

- `djangorestframework`
