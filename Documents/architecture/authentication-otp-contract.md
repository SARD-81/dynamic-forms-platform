# Gate 3 Authentication and Email OTP Contract

**Status:** ACTIVE GATE 3 CONTRACT  
**Issue:** #26  
**Architecture baseline:** BL-ARCH-002  
**Data baseline:** BL-DATA-002  
**Presentation dependency:** Issue #27 shared template shell

## Purpose

Define the Gate 3 account activation and session-authentication behavior implemented by the
`accounts` app.

The contract uses the frozen `accounts.User` and `OTPChallenge` models. It does not change the
user identifier, data model, authentication backend, or database schema.

## Registration lifecycle

Registration accepts:

- username;
- unique email;
- password.

The Service:

1. normalizes the email;
2. validates the frozen User fields;
3. runs Django password validation;
4. creates the User with `is_active=False`;
5. generates a numeric OTP with Python `secrets`;
6. stores only a Django password hash of the OTP;
7. stores the challenge expiry;
8. schedules the email through `transaction.on_commit(...)`.

The raw OTP is never persisted.

Django's default `ModelBackend` remains authoritative for password login. Inactive users therefore
cannot authenticate until registration OTP verification activates the account.

## OTP constants

Gate 3 uses settings/configuration constants, not environment reads inside business code:

| Setting | Value |
|---|---:|
| `ACCOUNT_OTP_LENGTH` | 6 digits |
| `ACCOUNT_OTP_LIFETIME_SECONDS` | 300 |
| `ACCOUNT_OTP_MAX_ATTEMPTS` | 5 failed attempts |
| `ACCOUNT_OTP_RESEND_COOLDOWN_SECONDS` | 60 |
| `ACCOUNT_OTP_RATE_LIMIT_COUNT` | 5 sends |
| `ACCOUNT_OTP_RATE_LIMIT_WINDOW_SECONDS` | 900 |

Leading zeros are preserved.

## Verification semantics

Verification is transactional and locks the relevant User/challenge rows.

A code is rejected when:

- no pending account/challenge exists;
- the account is already active;
- the challenge has expired;
- five failed attempts have already occurred;
- the submitted code does not match the stored hash.

A wrong code increments `attempt_count` and commits that increment before the Service raises the
public verification error.

A successful code:

- writes `verified_at`;
- activates the User;
- cannot be reused.

## Resend semantics

Resend is available only for inactive accounts.

Before creating a replacement code, the Service enforces:

- 60-second cooldown after the latest send;
- maximum five challenge sends in the rolling 15-minute window.

When a resend is accepted, any still-usable previous registration challenge is invalidated by
setting its `expires_at` to the current time. `verified_at` remains reserved for a code that was
actually consumed successfully.

The new challenge is then created and emailed after commit.

## Production email transport

Production delivery is governed by approved CHG-0004.

The production settings contract requires:

- SMTP host;
- positive SMTP port;
- SMTP username/password;
- TLS boolean with a default of enabled;
- a positive finite SMTP timeout in seconds;
- default sender identity.

The timeout is configuration-owned and maps to Django's `EMAIL_TIMEOUT`. It is not hard-coded in the
account Service. An unlimited/`None` production SMTP timeout is not permitted.

Development keeps the console backend and tests keep the local-memory backend.

## Email failure semantics

Email is a post-commit side effect.

If delivery raises an exception or reports zero deliveries:

- the database transaction is already committed;
- the user remains inactive;
- the newly-created challenge remains structurally valid;
- the caller receives an explicit delivery error;
- the user can recover through the resend flow after the normal cooldown.

The Service never claims that database state was rolled back after a post-commit delivery failure.

## HTML routes

| Method | Route | Purpose |
|---|---|---|
| GET/POST | `/accounts/register/` | Registration |
| GET/POST | `/accounts/verify/` | OTP verification |
| POST | `/accounts/otp/resend/` | OTP resend |
| GET/POST | `/accounts/login/` | Password/session login |
| POST | `/accounts/logout/` | Session logout |
| GET | `/accounts/me/` | Authenticated account page |

Account templates extend the shared Issue #27 shell and use its form/error partials.

The verify and resend forms use separate prefixes so they never emit duplicate field IDs on the same
page.

## REST routes

Issue #26 owns these app-level routes:

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/v1/accounts/csrf/` | Obtain same-site CSRF token for session API |
| POST | `/api/v1/accounts/register/` | Registration |
| POST | `/api/v1/accounts/verify/` | OTP verification |
| POST | `/api/v1/accounts/resend/` | OTP resend |
| POST | `/api/v1/accounts/login/` | Create authenticated Django session |
| POST | `/api/v1/accounts/logout/` | End authenticated Django session |
| GET | `/api/v1/accounts/me/` | Current authenticated user |

The anonymous state-changing account endpoints explicitly apply Django CSRF protection. The
authenticated `me` and `logout` endpoints use DRF SessionAuthentication + IsAuthenticated.

## API foundation coordination

Issue #28 owns the shared API/OpenAPI foundation.

Until #28 is merged, the project root URLconf includes `apps.accounts.api_urls` directly under
`/api/v1/accounts/` so Issue #26 is independently executable and testable.

When #28 rebases/merges its shared `config.api_router`, the integration should move this include
under that router without changing the account app URLs, Services, serializers, or API views.

This is an integration-location change only and must not create a parallel accounts API.

## Service and Selector boundaries

Write/state-changing operations live in `apps.accounts.services`:

- registration;
- challenge creation/resend;
- verification/activation;
- session login;
- session logout.

Reusable User lookup helpers live in `apps.accounts.selectors`.

HTML and API handlers translate input/output and service exceptions; they do not reimplement OTP
business rules.

## Security rules

- no raw OTP is persisted;
- OTP generation uses `secrets`;
- OTP comparison uses Django password hashing helpers;
- account passwords use Django's normal User password hashing;
- inactive users cannot authenticate;
- login redirect targets are restricted to allowed local URLs;
- logout is state-changing POST, not GET;
- session API login is CSRF-protected;
- no account business code reads host environment variables directly;
- API responses never return the OTP.

## Verification

Issue #26 regression tests cover:

- leading-zero OTP generation and hash-only persistence;
- duplicate email and password validation;
- expiration;
- incorrect attempts and exhaustion;
- successful one-time verification;
- resend invalidation;
- cooldown and rolling rate limit;
- post-commit email failure coherence;
- complete HTML register/verify/login/logout flow;
- inactive and wrong-password login rejection;
- HTML current-user permission;
- complete REST register/verify/login/me/logout flow;
- REST permission behavior;
- enforced CSRF behavior for API login;
- production SMTP fail-fast behavior for missing configuration;
- positive integer validation for SMTP port and timeout;
- production SMTP mapping, TLS default, and finite `EMAIL_TIMEOUT`;
- unchanged development console and test local-memory email backends.

Normal repository checks remain required:

```bash
ruff format --check .
ruff check .
pytest
python src/manage.py makemigrations --check --dry-run
```
