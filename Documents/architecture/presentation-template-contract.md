# Gate 3 Shared Presentation Template Contract

**Status:** ACTIVE GATE 3 CONTRACT  
**Issue:** #27  
**Architecture baseline:** BL-ARCH-002

## Purpose

Define the shared Django Template presentation foundation used by Gate 3 HTML features.

This contract keeps account, form, process, and report pages visually and structurally consistent
without introducing a SPA, frontend framework, or build pipeline.

It does not define domain business behavior.

## Shared template locations

Project-wide templates live in:

```text
src/templates/
```

Current shared structure:

```text
src/templates/
├── base.html
├── home.html
├── 403.html
├── 404.html
├── dashboard/
│   └── index.html
├── public/
│   └── base_public.html
└── includes/
    ├── _navigation.html
    ├── _messages.html
    ├── _form_field.html
    ├── _form_errors.html
    ├── _state_empty.html
    ├── _state_loading.html
    └── _state_error.html
```

Domain-owned templates should normally remain namespaced inside their Django app:

```text
src/apps/<app>/templates/<app>/...
```

Examples:

```text
src/apps/accounts/templates/accounts/login.html
src/apps/forms/templates/forms/form_list.html
src/apps/processes/templates/processes/process_detail.html
src/apps/reports/templates/reports/form_report.html
```

This avoids template-name collisions while allowing every domain page to extend the project shell.

## Naming convention

- full page templates use descriptive snake_case names;
- shared partials begin with an underscore;
- domain templates are namespaced under the owning app;
- reusable project-level presentation belongs under `src/templates/includes/`;
- domain-specific fragments stay with the domain app instead of moving into `core`.

## Base template contract

Domain HTML pages should extend:

```django
{% extends "base.html" %}
```

Primary blocks:

| Block | Purpose |
|---|---|
| `title` | Browser/page title |
| `extra_head` | Page-specific metadata or safe extra CSS references |
| `body_class` | Optional page-level body class |
| `site_header` | Rare full header override; normal pages should keep the shared navigation |
| `content` | Main page content |
| `scripts` | Small page-specific JavaScript after shared JS |

The base template owns:

- document structure and viewport metadata;
- skip link and main-content landmark;
- shared responsive navigation;
- Django message rendering;
- shared CSS and JavaScript loading;
- common footer.

Pages must not copy the complete HTML document when extending the shell is sufficient.

## Public participation shell

Participant-facing Form and Process pages should extend:

```django
{% extends "public/base_public.html" %}
```

Available public-page blocks:

| Block | Purpose |
|---|---|
| `public_kicker` | Small context label |
| `public_title` | Form/Process display title |
| `public_intro` | Description or participant guidance |
| `public_content` | Password challenge, questions, process step content, or completion state |

Public access rules, passwords, visibility, view counting, submissions, and process execution remain
owned by their relevant Gate 3 Issues. The shell contains no such business rules.

## Shared partials

### Messages

```django
{% include "includes/_messages.html" %}
```

Already included by `base.html`. Domain pages normally do not include it again.

### Bound form field

```django
{% include "includes/_form_field.html" with field=form.title %}
```

The partial provides:

- a real `label` bound to the widget id;
- required-field indication;
- help text;
- field-level validation errors.

Domain forms remain responsible for validation and widget attributes specific to their behavior.

### Non-field form errors

```django
{% include "includes/_form_errors.html" with form=form %}
```

### Empty state

```django
{% include "includes/_state_empty.html" with state_title="No forms yet" state_message="Create your first form to get started." %}
```

Optional action values:

- `state_action_url`
- `state_action_label`

### Loading state

```django
{% include "includes/_state_loading.html" with state_message="Loading report…" %}
```

### Error state

```django
{% include "includes/_state_error.html" with state_title="Unable to load report" state_message="Try again later." %}
```

## Static assets

Shared presentation assets live under the installed `core` app:

```text
src/apps/core/static/core/
├── app.css
└── app.js
```

This uses Django staticfiles app discovery and requires no new static-file setting or build tool.

Domain-owned assets should be similarly namespaced:

```text
src/apps/<app>/static/<app>/...
```

Do not add React, Vue, Angular, Tailwind build infrastructure, npm tooling, or a second CSS framework
for Gate 3 domain pages without an approved architecture change.

## Navigation integration

The shared navigation owns only presentation state:

- anonymous users see Sign in / Create account actions;
- authenticated users see Dashboard / Sign out and their username.

Issue #27 does not implement authentication.

Until #26 lands, auth actions use conventional fallback paths under `/accounts/`. The navigation
also attempts to resolve the preferred named routes:

```text
accounts:login
accounts:register
accounts:logout
```

Issue #26 should provide those names or deliberately update this shared integration point in its PR.

Logout is rendered as a POST form rather than a state-changing GET link.

## Dashboard integration

`/dashboard/` requires authentication and currently contains presentation-only placeholders for:

- Categories
- Forms
- Processes
- Reports

Domain Issues should replace their own placeholder with real navigation only when the corresponding
owner/manage route exists on `dev`.

The dashboard must not import domain models or duplicate domain permissions.

## Error handling

Project URL configuration assigns:

- HTTP 403 → `apps.core.views.permission_denied`
- HTTP 404 → `apps.core.views.page_not_found`

Both handlers use the shared page shell.

Debug-mode technical error pages remain Django's development behavior.

## Accessibility baseline

Shared presentation establishes these minimum conventions:

- one main-content landmark and a keyboard-visible skip link;
- semantic navigation and headings;
- visible focus states;
- buttons declare `type`;
- forms use explicit labels;
- validation/system errors use alert semantics where appropriate;
- loading states use live status semantics;
- navigation remains visible without JavaScript and is progressively collapsed only when JS runs;
- reduced-motion preferences are respected.

Domain pages must preserve these conventions.

## JavaScript boundary

`core/app.js` is intentionally small and framework-free.

It currently owns only:

- responsive navigation disclosure;
- Escape-key navigation close behavior;
- dismissing rendered Django messages.

Business validation, domain state transitions, access decisions, and API rules do not belong in this
shared JavaScript file.

## Verification

Issue #27 tests cover:

- anonymous navigation;
- authenticated navigation;
- dashboard login protection;
- base/public template rendering;
- shared field/error rendering;
- custom 403/404 presentation;
- domain placeholders.

Normal repository checks remain required:

```bash
ruff format --check .
ruff check .
pytest
python src/manage.py makemigrations --check --dry-run
```
