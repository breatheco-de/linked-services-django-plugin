# Scopes

`scope` and `ascope` checks automatically the auth headers provided by its pairwise. It will check if the application that made the request has those required scopes to execute the request. All applications that does not requires an agreement will be treated as if these has all availabled scopes to execute the request.

## Decorators

- `scope`: synchronous implementation that manages the authentication and it will checks the scopes if the current application requires an agreement.
- `ascope`: asynchronous implementation that manages the authentication and it will checks the scopes if the current application requires an agreement.

## Parameters

- scopes: list of scopes.
- mode: use an alternative option to sign the request. Default is `JWT`.

## Name convention

I would recommend your that you would use the following naming convention, `action_name:data_name` like `read:repo` or `data_name` like `repo`.

## Examples

### Sync

You could want to use `scope` and `ascope` within a synchronous context if your framework does not support asynchronous operations.

```py
from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import AppUserSerializer

class AppUserView(APIView):
    permission_classes = [AllowAny]

    @scope(['read:user'])
    # action:data
    def get(self, request, app: dict, token: dict, user_id=None):
        # With the decorator I can access to the app and the token
        extra = {}
        if app.require_an_agreement:
            extra['appuseragreement__app__id'] = app.id

        if token.sub:
            extra['id'] = token.sub

        if user_id:
            if token.sub and token.sub != user_id:
                raise ValidationException('This user does not have access to this resource',
                                          code=403,
                                          slug='user-with-no-access',
                                          silent=True)

            if 'id' not in extra:
                extra['id'] = user_id

            user = User.objects.filter(**extra).first()
            if not user:
                raise ValidationException('User not found',
                                          code=404,
                                          slug='user-not-found',
                                          silent=True)

            serializer = AppUserSerializer(user, many=False)
            return Response(serializer.data)

        # test this path
        items = User.objects.filter(**extra)
        serializer = AppUserSerializer(items, many=True)

        return Response(serializer.data)
```

### Async

This is the most convenient option if you are using some ASGI server.

```py
import asyncio

from adrf.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from linked_services.django.actions import aget_app
from linked_services.django.models import FirstPartyWebhookLog
from linked_services.rest_framework.decorators import ascope


@api_view(["POST"])
@permission_classes([AllowAny])
@ascope(["webhook"], mode="jwt")
async def app_webhook(request, app: dict, token: dict):

    async def process_webhook(data):
        nonlocal app, token

        app = await aget_app(app.id)
        external_id = data.get("id", None)
        kwargs = {
            "app": app,
            "user_id": token.sub,
            "external_id": external_id,
            "type": data.get("type", "unknown"),
        }
        if external_id:
            x, created = await FirstPartyWebhookLog.objects.aget_or_create(
                **kwargs, defaults={"data": data.get("data", None)}
            )
            if not created:
                x.data = data.get("data", None)
                await x.asave()

        else:
            kwargs["data"] = data.get("data", None)
            await FirstPartyWebhookLog.objects.acreate(**kwargs)

    data = request.data if isinstance(request.data, list) else [request.data]

    to_process = []

    for x in data:
        p = process_webhook(x)
        to_process.append(p)

    await asyncio.gather(*to_process)

    return Response(None, status=status.HTTP_204_NO_CONTENT)
```
