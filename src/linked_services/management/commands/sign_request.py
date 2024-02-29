from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sign a request with a symmetric key"

    def add_arguments(self, parser):
        parser.add_argument("app", nargs="?", type=int)
        parser.add_argument("user", nargs="?", type=int)
        parser.add_argument("method", nargs="?", type=str)
        parser.add_argument("params", nargs="?", type=str)
        parser.add_argument("body", nargs="?", type=str)
        parser.add_argument("headers", nargs="?", type=str)

    def handle(self, *args, **options):
        from linked_services.django.actions import get_signature

        from ...models import App

        if not options["app"]:
            raise Exception("Missing app id")

        options["method"] = options["method"] if options["method"] is not None else "get"
        options["params"] = eval(options["params"]) if options["params"] is not None else {}
        options["body"] = eval(options["body"]) if options["body"] is not None else None
        options["headers"] = eval(options["headers"]) if options["headers"] is not None else {}

        try:
            app = App.objects.get(id=options["app"])

        except App.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'App {options["app"]} not found'))
            return

        sign, now = get_signature(
            app,
            options["user"],
            method=options["method"],
            params=options["params"],
            body=options["body"],
            headers=options["headers"],
            reverse=True,
        )

        self.stdout.write(
            f"Authorization: Signature App={app.slug},"
            f"Nonce={sign},"
            f'SignedHeaders={";".join(options["headers"])},'
            f"Date={now}"
        )
