import logging
import secrets

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .tasks import dispatch_due_report_subscriptions

logger = logging.getLogger(__name__)


@require_GET
def dispatch_reports(request):
    secret = getattr(settings, "CRON_SECRET", "")
    if not getattr(settings, "VERCEL_CRON_ENABLED", False) or not secret:
        return JsonResponse({"detail": "Not found."}, status=404)
    authorization = request.headers.get("Authorization", "")
    if not secrets.compare_digest(authorization, f"Bearer {secret}"):
        return JsonResponse({"detail": "Unauthorized."}, status=401)
    try:
        dispatch_due_report_subscriptions.delay()
    except Exception:
        logger.error("Report cron enqueue failed.", exc_info=False)
        return JsonResponse({"detail": "Queue unavailable."}, status=503)
    return JsonResponse({"status": "queued"}, status=202)
