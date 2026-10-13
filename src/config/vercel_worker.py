"""Keep Celery task bodies and Django cleanup signals outside the ASGI loop."""

from celery.worker.worker import WorkController


class DjangoThreadWorker(WorkController):
    def __init__(self, *args, **kwargs):
        # The native adapter requests a solo pool and hands tasks off from the
        # async queue callback. A thread pool runs the full Celery trace (including
        # pre/postrun database cleanup) in a synchronous worker thread instead.
        kwargs["pool"] = "threads"
        super().__init__(*args, **kwargs)
