# Middlewares

## `linked_services_middleware`

This middleware sets the `Service` header to the app name if it's not already set.

```python
from linked_services.django.middlewares import linked_services_middleware

MIDDLEWARE = [
    ...
    'linked_services.django.middlewares.linked_services_middleware',
    ...
]
```
