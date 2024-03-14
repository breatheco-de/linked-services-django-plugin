# Views

Linked services implemented `authorize_view` and `app_webhook` endpoint handlers to share the implementation between all services.

## `app_webhook`

It's a webhook endpoint that saves them to be processed by `first_party_webhooks` command.

## `authorize_view`

It's a function that return an endpoint handler.

### Arguments

- `login_url`: the login url. Default to `os.getenv("LOGIN_URL")`
- `app_url`: the app url. Default to `os.getenv("APP_URL")`
- `get_language`: a function that receives a request and returns the user language. Default to `lambda request: 'en'`

## Example

```py
from django.urls import path
from linked_services.rest_framework.views import app_webhook, authorize_view

from breathecode.authenticate.actions import get_user_language


app_name = 'authenticate'
urlpatterns = [
    # authorize
    path('authorize/<str:app_slug>',
         authorize_view(login_url='/v1/auth/view/login', get_language=get_user_language),
         name='authorize_slug'),

    path('app/webhook', app_webhook, name='app_webhook'),
]
```
