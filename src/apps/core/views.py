from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def home(request):
    return render(request, "home.html")


@login_required
def dashboard(request):
    return render(request, "dashboard/index.html")


def permission_denied(request, exception):
    return render(request, "403.html", status=403)


def page_not_found(request, exception):
    return render(request, "404.html", status=404)
