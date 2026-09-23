from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from django import forms
from django.core.exceptions import PermissionDenied
from django.template.loader import render_to_string
from django.test import override_settings
from django.urls import path, reverse


def forbidden_view(request):
    raise PermissionDenied


urlpatterns = [
    path("forbidden/", forbidden_view),
]

handler403 = "apps.core.views.permission_denied"


def test_anonymous_navigation_state(client):
    response = client.get(reverse("core:home"))

    content = response.content.decode()
    assert response.status_code == 200
    assert "Sign in" in content
    assert "Create account" in content
    assert "Sign out" not in content
    assert 'aria-controls="primary-navigation"' in content


@pytest.mark.django_db
def test_authenticated_navigation_state(client, user):
    client.force_login(user)

    response = client.get(reverse("core:dashboard"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Dashboard" in content
    assert f"Signed in as {user.get_username()}" in content
    assert "Sign out" in content
    assert "Create account" not in content


def test_dashboard_requires_login(client):
    response = client.get(reverse("core:dashboard"))

    redirect = urlparse(response.url)
    assert response.status_code == 302
    assert redirect.path == "/accounts/login/"
    assert parse_qs(redirect.query) == {"next": ["/dashboard/"]}


def test_base_and_public_templates_render_without_missing_context():
    base_html = render_to_string("base.html")
    public_html = render_to_string("public/base_public.html")

    assert "Dynamic Forms Platform" in base_html
    assert 'id="main-content"' in base_html
    assert "Participation" in public_html
    assert "Form or process" in public_html


def test_shared_form_field_escapes_help_text_and_matches_django_description_ids():
    class SampleForm(forms.Form):
        name = forms.CharField(
            label="Display name",
            required=True,
            help_text='<img src=x onerror="alert(1)">',
        )

    form = SampleForm(data={"name": ""})
    assert form.is_valid() is False

    field = form["name"]
    html = render_to_string("includes/_form_field.html", {"field": field})

    assert 'for="id_name"' in html
    assert "Display name" in html
    assert "This field is required." in html
    assert 'role="alert"' in html

    assert "<img" not in html
    assert "&lt;img" in html
    assert "onerror=&quot;alert(1)&quot;" in html

    assert field.aria_describedby == "id_name_helptext id_name_error"
    assert f'aria-describedby="{field.aria_describedby}"' in html
    for description_id in field.aria_describedby.split():
        assert f'id="{description_id}"' in html


def test_shared_css_preserves_checkbox_and_radio_sizing():
    css_path = Path(__file__).parents[1] / "static" / "core" / "app.css"
    css = css_path.read_text(encoding="utf-8")

    assert '.form-field input[type="checkbox"],' in css
    assert '.form-field input[type="radio"] {' in css
    assert "width: 1rem;" in css
    assert "height: 1rem;" in css

    broad_text_input_selector = ".form-field input,\n.form-field select,"
    assert broad_text_input_selector not in css


def test_404_handler_uses_shared_error_presentation(client):
    response = client.get("/route-that-does-not-exist/")

    assert response.status_code == 404
    assert "Page not found" in response.content.decode()
    assert "Return home" in response.content.decode()


@override_settings(ROOT_URLCONF=__name__)
def test_403_handler_uses_shared_error_presentation(client):
    response = client.get("/forbidden/")

    assert response.status_code == 403
    assert "Access denied" in response.content.decode()
    assert "Return home" in response.content.decode()


@pytest.mark.django_db
def test_dashboard_exposes_domain_placeholders(client, user):
    client.force_login(user)

    response = client.get(reverse("core:dashboard"))
    content = response.content.decode()

    assert 'data-feature="categories"' in content
    assert 'data-feature="forms"' in content
    assert 'data-feature="processes"' in content
    assert 'data-feature="reports"' in content
