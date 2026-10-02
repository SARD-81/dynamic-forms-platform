# ADR-0001 — Python, Django, and ASGI Runtime Baseline

**Status:** ACCEPTED  
**Date:** 2026-09-20  
**Gate:** 2B — Python / Django / ASGI Bootstrap  
**Will be incorporated into:** BL-FOUNDATION-001

## Context

The project needs a stable, understandable Django runtime that supports the frozen REST, Channels/WebSocket, PostgreSQL, and future async architecture without exceeding the team's intended implementation level.

## Decision

Use:

- Python 3.12
- Django 5.2 LTS
- Django REST Framework 3.18.x
- Channels 4.3.x
- Daphne through the Channels Daphne extra
- Psycopg 3.3.x

Daphne is first in `INSTALLED_APPS`; `channels` is also installed.

The root ASGI application is a `ProtocolTypeRouter` containing HTTP only in Gate 2B. WebSocket consumers/routes are intentionally deferred.

## Why

Django 5.2 is LTS and supports Python 3.12. This is a stable long-lived choice and avoids moving to Django 6.x without a project requirement.

Python 3.12 is mature and straightforward across Windows and Linux.

## Consequences

- no SQLite configuration;
- Custom User exists before project migrations;
- environment hardening belongs to Gate 2C;
- WebSocket business routing belongs to reporting work;
- after BL-FOUNDATION-001 freezes, major/minor runtime changes require change control.
