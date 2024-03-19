import uuid

from adrf.requests import AsyncRequest as BaseAsyncRequest
from django.contrib.auth.models import User
from django.http.request import HttpRequest as BaseHttpRequest


class AsyncLinkedHttpRequest(BaseAsyncRequest):
    def __init__(self, *args, **kwargs):
        raise Exception("This AsyncRequest class cannot be instantiated, you must use adrf.requests.AsyncRequest")

    async def get_user() -> User | None:
        pass


class LinkedHttpRequest(BaseHttpRequest):
    def __init__(self, *args, **kwargs):
        raise Exception("This AsyncRequest class cannot be instantiated, you must use django.http.request.HttpRequest")

    def get_user() -> User | None:
        pass


class LinkedToken:
    def __init__(self, *args, **kwargs):
        raise Exception("This class cannot be instantiated")

    sub: int | str | uuid.UUID
    iss: str
    app: str
    aud: str
    exp: float
    iat: float
    typ: str


class LinkedApp:
    def __init__(self, *args, **kwargs):
        raise Exception("This class cannot be instantiated")

    id: int | str | uuid.UUID
    private_key: bytes
    public_key: bytes | None
    algorithm: str
    strategy: str
    schema: str
    schema: str
    require_an_agreement: bool
    webhook_url: float
    redirect_url: float
    app_url: float


class LinkedApplication(LinkedApp):
    pass
