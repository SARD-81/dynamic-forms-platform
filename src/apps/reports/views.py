from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import ReportSubscriptionForm
from .models import ReportSubscription
from .selectors import get_report_subscription, get_report_subscriptions
from .services import (
    create_report_subscription,
    deactivate_report_subscription,
    generate_periodic_report_payload,
    update_report_subscription,
)


def _require_staff(request):
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied


@login_required
def subscription_list(request):
    _require_staff(request)
    return render(
        request,
        "reports/subscriptions/list.html",
        {"subscriptions": get_report_subscriptions()},
    )


@login_required
def subscription_create(request):
    _require_staff(request)
    form = ReportSubscriptionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        create_report_subscription(actor=request.user, **form.cleaned_data)
        messages.success(request, "Report subscription created.")
        return redirect("reports:list")
    return render(request, "reports/subscriptions/form.html", {"form": form, "mode": "create"})


@login_required
def subscription_update(request, subscription_id):
    _require_staff(request)
    subscription = get_report_subscription(subscription_id=subscription_id)
    if subscription is None:
        raise Http404
    initial = {
        "frequency": subscription.frequency,
        "delivery_method": subscription.delivery_method,
        "email": subscription.email,
        "endpoint_url": subscription.endpoint_url,
        "is_active": subscription.is_active,
    }
    form = ReportSubscriptionForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        update_report_subscription(
            actor=request.user,
            subscription_id=subscription.pk,
            **form.cleaned_data,
        )
        messages.success(request, "Report subscription updated.")
        return redirect("reports:list")
    return render(
        request,
        "reports/subscriptions/form.html",
        {"form": form, "mode": "update", "subscription": subscription},
    )


@login_required
@require_POST
def subscription_deactivate(request, subscription_id):
    _require_staff(request)
    if get_report_subscription(subscription_id=subscription_id) is None:
        raise Http404
    deactivate_report_subscription(actor=request.user, subscription_id=subscription_id)
    messages.success(request, "Report subscription deactivated.")
    return redirect("reports:list")


@login_required
def report_preview(request):
    _require_staff(request)
    frequency = request.GET.get("frequency", ReportSubscription.Frequency.WEEKLY)
    if frequency not in ReportSubscription.Frequency.values:
        raise Http404
    payload = generate_periodic_report_payload(frequency=frequency)
    return render(request, "reports/subscriptions/preview.html", {"payload": payload})
