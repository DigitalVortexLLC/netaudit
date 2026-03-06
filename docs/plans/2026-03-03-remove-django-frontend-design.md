# Remove Django Template Frontend

## Goal

Strip the legacy Django template/HTMX frontend, keeping only the DRF API layer. Enable allauth headless mode so MFA/passkey flows are available as API endpoints for the React SPA.

## Files to Delete

### Templates
- `backend/templates/` (base.html, base_auth.html, account/*, accounts/*, partials/*)
- `backend/audits/templates/`
- `backend/devices/templates/`
- `backend/rules/templates/`
- `backend/settings/templates/`

### Static files
- `backend/static/` (style.css)

### HTML views
- `backend/accounts/views_html.py`
- `backend/audits/views_html.py`
- `backend/devices/views_html.py`
- `backend/rules/views_html.py`
- `backend/settings/views_html.py`

### HTML URL configs
- `backend/accounts/urls_html.py`
- `backend/audits/urls_html.py`
- `backend/audits/urls_html_schedules.py`
- `backend/devices/urls_html.py`
- `backend/devices/urls_html_groups.py`
- `backend/rules/urls_html.py`
- `backend/settings/urls_html.py`

### Template infrastructure
- `backend/common/templatetags/badge_tags.py`
- `backend/common/templatetags/nav_tags.py`
- `backend/accounts/context_processors.py`

## Files to Modify

### `config/urls.py`
- Remove all template URL includes (dashboard, accounts/allauth, devices, groups, rules, schedules, settings HTML routes)
- Add `path("_allauth/", include("allauth.headless.urls"))`
- Keep `path("accounts/", include("allauth.urls"))` with `HEADLESS_ONLY=True` (needed for OAuth callbacks)

### `config/settings/base.py`
- Remove `django_htmx` from `INSTALLED_APPS`
- Remove `HtmxMiddleware` from `MIDDLEWARE`
- Add `allauth.headless` to `INSTALLED_APPS`
- Add `HEADLESS_ONLY = True`
- Add `HEADLESS_FRONTEND_URLS` pointing to SPA routes for email confirmation and password reset
- Remove `backend/templates/` from `TEMPLATES[0]["DIRS"]` (keep engine config for admin)
- Remove `accounts.context_processors.user_role` from context processors
- Remove `STATICFILES_DIRS` (keep `STATIC_URL`/`STATIC_ROOT` for admin)
- Update `LOGIN_URL` / `LOGIN_REDIRECT_URL`

### `requirements.txt`
- Remove `django-htmx`
- Change `django-allauth[mfa]` to `django-allauth[mfa,headless]`

## What Stays Untouched
- All `views.py` (DRF ViewSets and APIViews)
- All `urls.py` (API routes under `/api/v1/`)
- `accounts/adapters.py` (first-user-admin logic via allauth)
- `accounts/middleware.py` (AuthHookMiddleware)
- `audit_runner/templates/` (Jinja2 code-generation templates, not frontend)
- Django admin (`/admin/`)
- allauth core, MFA, and WebAuthn config
- All serializers, models, and business logic
