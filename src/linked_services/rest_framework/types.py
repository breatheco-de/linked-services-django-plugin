from adrf.requests import AsyncRequest as BaseAsyncRequest
from django.contrib.auth.models import User
from django.http.request import HttpRequest as BaseHttpRequest


class AsyncRequest(BaseAsyncRequest):
    def __init__(self, *args, **kwargs):
        raise Exception("This AsyncRequest class cannot be instantiated, you must use adrf.requests.AsyncRequest")

    async def get_user() -> User | None:
        pass


class HttpRequest(BaseHttpRequest):
    def __init__(self, *args, **kwargs):
        raise Exception("This AsyncRequest class cannot be instantiated, you must use adrf.requests.AsyncRequest")

    def get_user() -> User | None:
        pass
