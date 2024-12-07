from asgiref.sync import iscoroutinefunction
from django.utils.decorators import sync_and_async_middleware

from linked_services.core.settings import get_setting


@sync_and_async_middleware
def linked_services_middleware(get_response):
    def set_header(response):
        if "Service" not in response.headers and (app_name := get_setting("app_name", None)):
            response.headers["Service"] = app_name

    if iscoroutinefunction(get_response):

        async def middleware(request):
            response = await get_response(request)
            set_header(response)
            return response

    else:

        def middleware(request):
            response = get_response(request)
            set_header(response)
            return response

    return middleware
