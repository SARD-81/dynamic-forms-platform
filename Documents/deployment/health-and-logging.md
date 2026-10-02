# Operational health and logging

`GET`/`HEAD /health/live/` returns `200 {"status":"ok"}` when Django can answer a request.
It does not consult PostgreSQL or Redis. `GET`/`HEAD /health/ready/` returns the same
success shape only when a fresh PostgreSQL `SELECT 1` and a unique cache
set/get/delete probe succeed. Failure returns a generic `503 {"status":"not_ready"}`.
HEAD follows the same status decision as GET and sends no response body. Other
methods return 405 without probing dependencies, including requests without a
CSRF cookie. Only these public method-guarded operational views are exempt;
application/auth mutation endpoints retain their CSRF checks. These routes require no login
and reveal no host, URL, password or exception.

The database probe uses a disposable Django connection. Its query timeout and TCP
keepalive options never change a business connection's session. Connections are
closed after every probe. Redis uses the configured Django cache backend, with
unique, short-lived keys, finite connect/read timeouts and no timeout retries.

Timeouts are resolved in settings, with safe defaults and validated integer ranges:

| Environment value | Default | Accepted range |
| --- | --- | --- |
| `POSTGRES_CONNECT_TIMEOUT_SECONDS` | 2 seconds | 2–10 |
| `READINESS_DB_QUERY_TIMEOUT_MS` | 1000 ms | 100–5000 |
| `REDIS_CONNECT_TIMEOUT_SECONDS` | 1 second | 1–5 |
| `REDIS_SOCKET_TIMEOUT_SECONDS` | 1 second | 1–5 |

PostgreSQL connection timeout is per resolved host/address. The supported
production topology uses one internal PostgreSQL service and one Redis service;
external multi-host/DNS configurations need their own latency acceptance. The
probe-only PostgreSQL connection also uses finite TCP keepalive/user timeout bounds
on the Linux production runtime. Tests exercise silent TCP peers, not just mocked
exceptions. Nginx and public verifiers provide an additional finite HTTP boundary.

Python/Django/Celery logs use a console handler and `SensitiveDataFilter`. The filter
renders parameterized messages before redaction, sanitizes exception and stack
text, and removes the original exception tuple so later formatters cannot reproduce
an unsanitized traceback. Passwords, bearer tokens, API keys, OTPs, SMTP credentials,
access secrets, resume tokens and URL userinfo/query tokens are covered. Celery
does not replace the configured root handlers or redirect arbitrary stdout.

Use meaningful messages and named fields. Never log complete request bodies,
session cookies, raw answers or unlabeled secrets; a pattern filter cannot identify
every arbitrary private string. Readiness failure logs use fixed messages and omit
dependency exception text. Nginx access logging must omit query strings because
participant URLs may contain resume tokens.

This is the #80 operational contract under effective CHG-0006. Production ingress
and settings wiring belong to #81; automated full topology verification belongs
to #83. HTTP reporting remains authoritative; #41 is optional.
