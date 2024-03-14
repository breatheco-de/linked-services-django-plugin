# Rest frameworks

To implement `scope` and `ascope` you must use `get_decorators` and `get_handlers` functions to get both decorators.

## get_app_keys

### arguments

- `app_slug`: - slug or your application.

### Returns

It returns a tuple of (info, key, legacy_key or None) where:

- info: (app_id, algorithm, strategy, schema, require_an_agreement, required_scopes, optional_scopes, webhook_url, redirect_url, app_url)
- key and legacy_key: (public_key, private_key)

#### info

- `app_id`: application id.
- `algorithm`: algorithm of the keys used.
- `strategy`: authentication strategy used by default.
- `schema`: schema of the keys used.
- `require_an_agreement`: if true, the user must accept share its data with the other application.
- `required_scopes`: list of strings with all scopes that are required.
- `optional_scopes` list of strings with all scopes that are optional.
- `webhook_url`: webhook url.
- `redirect_url`: redirect url.
- `app_url`: application url.

#### key and legacy_key

- `public_key`: public key string
- `private_key`: private key string or None

## get_user_scopes

### arguments

- `app_slug`: slug or your application.
- `user_id`: optional user id.

### Returns

Two tuple of strings, the second tuple should be None. It returns the required scopes as first tuple and the optional as second tuple.

## Example

```py
from linked_services.core.decorators import get_decorators, get_handlers
from linked_services.django.actions import get_app_keys, get_user_scopes

__all__ = ["scope", "ascope"]


link_schema, signature_schema = get_handlers(get_app_keys, get_user_scopes)
scope, ascope = get_decorators(link_schema, signature_schema)

```
