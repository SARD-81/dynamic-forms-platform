# API Conventions & Architecture

This document defines the core standards for the Dynamic Forms Platform API (Gate 3). All new endpoints must strictly adhere to these conventions.

## 1. Routing & Domains
- **Base Path:** All API routes begin with `/api/v1/`.
- **App Routing Convention:** Each domain manages its own `api_urls.py`. The core configuration (`config/api_router.py`) acts solely as a central router.
  - Example: `/api/v1/accounts/` maps to `apps.accounts.api_urls`.
- **Code Organization:** Views, serializers, and permissions must be strictly isolated within their respective domain apps (e.g., `apps/accounts/api_views.py`, `apps/accounts/serializers.py`).
- **Business Logic:** No business logic, serializers, or views should exist inside the `config` directory.

## 2. Documentation (OpenAPI/Swagger)
- **Schema URL:** `/api/schema/` (Generates the raw OpenAPI YAML/JSON schema).
- **Swagger UI URL:** `/api/v1/docs/` (Interactive API documentation).
- **Tooling:** Powered by `drf-spectacular`. This tool was selected for its native OpenAPI 3.0 schema generation, deep integration with Django REST Framework, and superior handling of complex serializers compared to legacy tools like drf-yasg.

## 3. Versioning
- **Strategy:** URL Path Versioning (e.g., `/v1/`).
- Major versions change the path (`/v2/`). Minor non-breaking changes are rolled directly into the active version.

## 4. Authentication & Permissions
- **Method:** Session Authentication (Token-based auth is deferred to future requirements).
- **Protected Endpoints:** Must return `403 Forbidden` for unauthenticated requests (standard DRF Session Auth behavior) or when lacking specific privileges.

## 5. Error Shape
Standardized JSON error response format:
*(Note: This is the target convention for all future Domain APIs. Existing/Core endpoints may currently use standard DRF error formats until fully standardized.)*
```json
{
  "error_code": "STRING_CODE",
  "detail": "Human readable message",
  "field_errors": {
    "field_name": ["List of errors"]
  }
}