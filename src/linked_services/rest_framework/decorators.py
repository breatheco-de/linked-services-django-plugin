from linked_services.core.decorators import get_decorators, get_handlers
from linked_services.django.actions import get_app_keys, get_user_scopes

__all__ = ["scope", "ascope"]


link_schema, signature_schema = get_handlers(get_app_keys, get_user_scopes)
scope, ascope = get_decorators(link_schema, signature_schema)
