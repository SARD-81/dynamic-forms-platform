from unittest.mock import patch

import pytest
from django.test import override_settings


@override_settings(VERCEL_CRON_ENABLED=True, CRON_SECRET="test-cron-secret")
@pytest.mark.parametrize("authorization", [None, "Bearer wrong", "test-cron-secret"])
def test_cron_rejects_unauthorized_without_enqueue(client, authorization):
    headers = {"HTTP_AUTHORIZATION": authorization} if authorization else {}
    with patch("apps.reports.cron.dispatch_due_report_subscriptions.delay") as enqueue:
        response = client.get("/internal/cron/reports/", **headers)
    assert response.status_code == 401
    enqueue.assert_not_called()


@override_settings(VERCEL_CRON_ENABLED=True, CRON_SECRET="test-cron-secret")
def test_cron_enqueues_and_handles_queue_outage(client):
    with patch("apps.reports.cron.dispatch_due_report_subscriptions.delay") as enqueue:
        response = client.get(
            "/internal/cron/reports/", HTTP_AUTHORIZATION="Bearer test-cron-secret"
        )
        assert response.status_code == 202
        enqueue.assert_called_once_with()
        enqueue.side_effect = RuntimeError("provider secret must never be returned")
        response = client.get(
            "/internal/cron/reports/", HTTP_AUTHORIZATION="Bearer test-cron-secret"
        )
    assert response.status_code == 503
    assert b"provider secret" not in response.content


def test_cron_disabled_in_docker_and_rejects_post(client):
    assert client.get("/internal/cron/reports/").status_code == 404
    assert client.post("/internal/cron/reports/").status_code == 405
