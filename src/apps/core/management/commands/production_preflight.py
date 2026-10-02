from uuid import uuid4

from django.conf import settings
from django.core.cache import caches
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.utils.module_loading import import_string


class Command(BaseCommand):
    help = "Check application readiness for production without domain writes."

    # Run only our explicit checks, keeping output predictable.
    requires_system_checks = []
    requires_migrations_checks = False

    def handle(self, *args, **options):
        checks = (
            ("settings", self.check_settings),
            ("debug", self.check_debug),
            ("hosts", self.check_hosts),
            ("database", self.check_database),
            ("cache", self.check_cache),
            ("static", self.check_static),
            ("email", self.check_email),
            ("runtime", self.check_runtime),
        )

        failed = False

        for name, check in checks:
            try:
                check()
            except Exception:
                # Exception messages can contain credentials or URLs.
                self.stdout.write(f"FAIL {name}")
                failed = True
            else:
                self.stdout.write(f"PASS {name}")

        if failed:
            raise CommandError("Production preflight failed.") from None

        self.stdout.write("Production preflight passed.")

    def check_settings(self):
        # Django loads settings before dispatching this command.
        if not settings.configured:
            raise ValueError

        # Access runtime settings without displaying their values.
        if not settings.SECRET_KEY:
            raise ValueError

        if not settings.ASGI_APPLICATION:
            raise ValueError

    def check_debug(self):
        if settings.DEBUG is not False:
            raise ValueError

    def check_hosts(self):
        hosts = settings.ALLOWED_HOSTS

        if not isinstance(hosts, (list, tuple)) or not hosts:
            raise ValueError

        if any(not isinstance(host, str) or not host.strip() for host in hosts):
            raise ValueError

    def check_database(self):
        connection = connections["default"]
        connection.ensure_connection()

        if not connection.is_usable():
            raise ValueError

    def check_cache(self):
        cache = caches["default"]
        key = f"production_preflight:{uuid4().hex}"
        value = uuid4().hex

        try:
            cache.set(key, value, timeout=30)

            if cache.get(key) != value:
                raise ValueError
        finally:
            cache.delete(key)

    def check_static(self):
        if not settings.STATIC_URL:
            raise ValueError

        if not settings.STATIC_ROOT:
            raise ValueError

    def check_email(self):
        # Instantiate the configured backend; do not open it or send mail.
        get_connection(fail_silently=False)

        if not settings.DEFAULT_FROM_EMAIL:
            raise ValueError

    def check_runtime(self):
        application = import_string(settings.ASGI_APPLICATION)

        if not callable(application):
            raise ValueError
