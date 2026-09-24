# API Conventions & Architecture

This document defines the core standards for the Dynamic Forms Platform API (Gate 3). All new endpoints must strictly adhere to these conventions.

## 1. Routing & Domains
- **Base Path:** All API routes begin with `/api/v1/`.
- **App Routing Convention:** Each domain manages its own `api_urls.py`. The core configuration (`config/api_router.py`) acts solely as a central router.
  - Example: `/api/v1/accounts/` maps to `apps.accounts.api_urls`.
- **Business Logic:** No business logic, serializers, or views should exist inside the `config` directory.

## 2. Documentation (OpenAPI/Swagger)
- **Schema URL:** `/api/schema/` (Generates the raw OpenAPI YAML/JSON schema).
- **Swagger UI URL:** `/api/v1/docs/` (Interactive API documentation).
- **Tooling:** Powered by `drf-spectacular`.

## 3. Versioning
- **Strategy:** URL Path Versioning (e.g., `/v1/`).
- Major versions change the path (`/v2/`). Minor non-breaking changes are rolled directly into the active version.

## 4. Authentication & Permissions
- **Method:** JSON Web Token (JWT) / Session Auth (depending on client type).
- **Protected Endpoints:** Must return `401 Unauthorized` for unauthenticated requests, and `403 Forbidden` for authenticated requests lacking specific privileges.

## 5. Error Shape
Standardized JSON error response format across all endpoints:
```json
{
  "error_code": "STRING_CODE",
  "detail": "Human readable message",
  "field_errors": {
    "field_name": ["List of errors"]
  }
}