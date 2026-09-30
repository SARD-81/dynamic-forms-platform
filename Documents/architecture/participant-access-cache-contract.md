# Participant Access and Cache Contract

Status: Gate 3 Issue #32 implementation contract.

## Public participant URLs

Published resources use their immutable `public_id`:

- HTML Form: `/p/forms/<public_id>/`
- HTML Process: `/p/processes/<public_id>/`
- REST Form: `/api/v1/public/forms/<public_id>/`
- REST Process: `/api/v1/public/processes/<public_id>/`

Only `PUBLISHED` resources are participant-accessible. DRAFT and CLOSED resources remain available through owner/reporting paths but are not exposed through participant endpoints.

## Private access

PRIVATE resources use the existing Django password hash stored by the owning domain.

Unlock endpoints:

- `POST /p/forms/<public_id>/unlock/`
- `POST /p/processes/<public_id>/unlock/`
- `POST /api/v1/public/forms/<public_id>/unlock/`
- `POST /api/v1/public/processes/<public_id>/unlock/`

Successful browser/API-session challenges store an object-scoped boolean grant in the Django session.

Grant identity is:

`<resource_type>:<public_id>`

The session never stores the submitted password or password hash. Form and Process grants are separate even if UUID text happens to match.

### Password-attempt throttling

Private unlock attempts are bounded before Django password hashing runs.

The rate-limit identity is scoped by resource type, public ID, and client address. The shared Django cache is authoritative for the cross-session/client counter. A local Django-session counter remains as an additional defense, but it is not permitted to replace the shared guarantee.

Default policy:

- 5 reserved password-verification attempts;
- 15-minute fixed window;
- each attempt is reserved in the shared cache before Django password hashing runs;
- HTTP 429 after the limit is reached;
- `Retry-After` communicates the configured window;
- successful unlock clears both counters;
- if the shared throttle cannot be read or updated, PRIVATE unlock fails closed with HTTP 503 and does not proceed to password hashing.

Only counters and hashed client identity are stored in cache. Submitted passwords and password hashes are never cached.

## View counting

`view_count` is an authoritative database value.

A view increments only after a successful participant detail GET. Password failures, unlock POSTs, DRAFT/CLOSED lookups, HEAD requests, and rejected requests do not increment it.

Updates use database-side `F("view_count") + 1` expressions to avoid read-modify-write races.

## Redis cache

Production/development cache configuration uses Django's cache abstraction:

- setting: `CACHES["default"]`
- backend: `django.core.cache.backends.redis.RedisCache`
- location: frozen `REDIS_CACHE_URL`
- logical DB: architecture reserves Redis DB 0
- socket connect timeout: 1 second
- socket read/write timeout: 1 second

Tests override the backend with deterministic `LocMemCache`.

Domain code does not import or call a Redis client directly.

### Keys

Safe published read models use:

- `participant:form:<public_id>:v1`
- `participant:process:<public_id>:v1`

Unlock throttling uses a separate versioned key scoped by resource, public ID, and a SHA-256-derived client-address digest.

The cached read payload contains display/schema data only. It excludes:

- raw passwords;
- password hashes;
- OTP values;
- resume tokens;
- authoritative view counters.

### Fallback

Participant read-model cache reads/writes/deletes are best-effort. Cache exceptions fall back to authoritative database reads and never decide access eligibility.

Unlock throttling also keeps a per-session fallback counter, so a temporary Redis failure does not immediately restore unlimited password hashing for an existing participant session.

Redis connect/read timeouts are bounded so cache failure falls back promptly instead of waiting for an OS-level timeout.

Lifecycle/access checks always use the database before a cached read model is returned.

### Invalidation ownership

Form lifecycle Services invalidate the Form participant key on publish/close.

Process lifecycle Services invalidate the Process participant key on publish/close.

Published Form question schema and published Process step schema are immutable by the frozen lifecycle rules, so DRAFT builder writes do not own participant-cache invalidation.
