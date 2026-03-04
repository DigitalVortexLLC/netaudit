# Remove Django Template Frontend — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Strip the legacy Django template/HTMX frontend layer and enable allauth headless mode, leaving only the DRF API for the React SPA.

**Architecture:** Delete all `views_html.py`, `urls_html*.py`, templates, static files, and template infrastructure. Modify `config/urls.py` and `config/settings/base.py` to remove HTMX, add allauth headless, and clean up template-only settings. Remove `django-htmx` from requirements.

**Tech Stack:** Django 5.1, django-allauth 65.x (with headless + MFA extras), dj-rest-auth, React SPA

---

### Task 1: Update requirements.txt

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: Remove django-htmx and add headless extra to allauth**

In `backend/requirements.txt`:
- Remove the line: `django-htmx>=1.19,<2.0`
- Change: `django-allauth[mfa]>=65.0,<66.0` → `django-allauth[mfa,headless]>=65.0,<66.0`

**Step 2: Install updated dependencies**

Run: `cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/fervent-lederberg && pip install -r backend/requirements.txt`
Expected: All packages install successfully, `django-htmx` is no longer required.

**Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: remove django-htmx, add allauth headless extra"
```

---

### Task 2: Update Django settings

**Files:**
- Modify: `backend/config/settings/base.py`

**Step 1: Update INSTALLED_APPS**

Remove `"django_htmx",` (line 27) and `"common",` (line 43).
Add `"allauth.headless",` after `"allauth.mfa",` (after line 31).

Result:
```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "corsheaders",
    "django_filters",
    "django_q",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "allauth.headless",
    "allauth.socialaccount",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    # Local apps
    "accounts",
    "devices",
    "rules",
    "audits",
    "settings",
    "notifications",
    "config_sources",
]
```

**Step 2: Update MIDDLEWARE**

Remove `"django_htmx.middleware.HtmxMiddleware",` (line 58).

**Step 3: Update TEMPLATES**

- Change `"DIRS": [BASE_DIR / "templates"],` to `"DIRS": [],`
- Remove `"accounts.context_processors.user_role",` from context processors.

Result:
```python
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
```

**Step 4: Remove STATICFILES_DIRS**

Delete line 100: `STATICFILES_DIRS = [BASE_DIR / "static"]`

(Keep `STATIC_URL` and `STATIC_ROOT` — Django admin needs them.)

**Step 5: Add allauth headless settings**

Replace lines 147-148:
```python
LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/accounts/login/"
```

With:
```python
HEADLESS_ONLY = True
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": "/verify-email/{key}",
    "account_reset_password_from_key": "/reset-password/{key}",
    "account_signup": "/signup",
}
```

**Step 6: Verify settings load without error**

Run: `cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/fervent-lederberg/backend && python -c "import django; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development'); django.setup(); print('Settings OK')"`
Expected: `Settings OK`

**Step 7: Commit**

```bash
git add backend/config/settings/base.py
git commit -m "chore: update settings for headless-only allauth, remove HTMX"
```

---

### Task 3: Update URL configuration

**Files:**
- Modify: `backend/config/urls.py`

**Step 1: Replace urls.py contents**

Replace the full file with:
```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Allauth (headless API + OAuth callbacks)
    path("accounts/", include("allauth.urls")),
    path("_allauth/", include("allauth.headless.urls")),
    # DRF API
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("devices.urls")),
    path("api/v1/", include("rules.urls")),
    path("api/v1/", include("audits.urls")),
    path("api/v1/", include("settings.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
    path("api/v1/", include("config_sources.urls")),
]
```

**Step 2: Verify URL resolution**

Run: `cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/fervent-lederberg/backend && python -c "import django; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development'); django.setup(); from django.urls import reverse; print(reverse('admin:index')); print('URLs OK')"`
Expected: `/admin/` and `URLs OK`

**Step 3: Commit**

```bash
git add backend/config/urls.py
git commit -m "chore: remove template URL routes, add allauth headless URLs"
```

---

### Task 4: Delete HTML view files

**Files:**
- Delete: `backend/accounts/views_html.py`
- Delete: `backend/audits/views_html.py`
- Delete: `backend/devices/views_html.py`
- Delete: `backend/rules/views_html.py`
- Delete: `backend/settings/views_html.py`

**Step 1: Remove all views_html.py files**

```bash
cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/fervent-lederberg
git rm backend/accounts/views_html.py backend/audits/views_html.py backend/devices/views_html.py backend/rules/views_html.py backend/settings/views_html.py
```

**Step 2: Commit**

```bash
git commit -m "chore: delete template-rendering views"
```

---

### Task 5: Delete HTML URL config files

**Files:**
- Delete: `backend/accounts/urls_html.py`
- Delete: `backend/audits/urls_html.py`
- Delete: `backend/audits/urls_html_schedules.py`
- Delete: `backend/devices/urls_html.py`
- Delete: `backend/devices/urls_html_groups.py`
- Delete: `backend/rules/urls_html.py`
- Delete: `backend/settings/urls_html.py`

**Step 1: Remove all urls_html files**

```bash
cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/fervent-lederberg
git rm backend/accounts/urls_html.py backend/audits/urls_html.py backend/audits/urls_html_schedules.py backend/devices/urls_html.py backend/devices/urls_html_groups.py backend/rules/urls_html.py backend/settings/urls_html.py
```

**Step 2: Commit**

```bash
git commit -m "chore: delete template URL configs"
```

---

### Task 6: Delete templates and static files

**Files:**
- Delete: `backend/templates/` (entire directory)
- Delete: `backend/static/` (entire directory)
- Delete: `backend/audits/templates/` (entire directory)
- Delete: `backend/devices/templates/` (entire directory)
- Delete: `backend/rules/templates/` (entire directory)
- Delete: `backend/settings/templates/` (entire directory)

**Important:** Do NOT delete `backend/audit_runner/templates/` — those are Jinja2 code-generation templates (`.j2` files), not frontend HTML.

**Step 1: Remove template and static directories**

```bash
cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/fervent-lederberg
git rm -r backend/templates/ backend/static/ backend/audits/templates/ backend/devices/templates/ backend/rules/templates/ backend/settings/templates/
```

**Step 2: Commit**

```bash
git commit -m "chore: delete Django templates and static files"
```

---

### Task 7: Delete template infrastructure

**Files:**
- Delete: `backend/common/templatetags/badge_tags.py`
- Delete: `backend/common/templatetags/nav_tags.py`
- Delete: `backend/common/templatetags/__init__.py`
- Delete: `backend/common/templatetags/` (directory)
- Delete: `backend/accounts/context_processors.py`
- Delete: `backend/common/` (entire app — nothing else uses it)

**Step 1: Remove template tags, context processor, and common app**

```bash
cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/fervent-lederberg
git rm -r backend/common/
git rm backend/accounts/context_processors.py
```

**Step 2: Commit**

```bash
git commit -m "chore: delete template tags, context processor, and common app"
```

---

### Task 8: Run full test suite and verify

**Step 1: Run all existing tests**

Run: `cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/fervent-lederberg/backend && python -m pytest --tb=short -q`
Expected: All tests pass. No test references the deleted HTML views or templates.

**Step 2: Verify Django check passes**

Run: `cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/fervent-lederberg/backend && python manage.py check --settings=config.settings.development`
Expected: `System check identified no issues.`

**Step 3: Verify migrations are clean**

Run: `cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/fervent-lederberg/backend && python manage.py showmigrations --settings=config.settings.development 2>&1 | head -5`
Expected: No errors. Migrations listed normally.

**Step 4: Verify allauth headless endpoint is accessible**

Run: `cd /Users/aaronroth/Documents/netaudit/.claude/worktrees/fervent-lederberg/backend && python -c "import django; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development'); django.setup(); from django.urls import reverse; print(reverse('headless:browser:account:login')); print('Headless OK')"`
Expected: Prints the headless login URL path and `Headless OK`.

**Step 5: Fix any issues found, then commit if there were fixes**

If any tests fail or checks report issues, fix them before proceeding.

---

### Task 9: Verify no dangling references

**Step 1: Search for any remaining references to deleted modules**

Run a grep across the backend for references to deleted files:
- `views_html`
- `urls_html`
- `badge_tags`
- `nav_tags`
- `context_processors.user_role`
- `django_htmx`

Expected: No matches in any `.py` files (only this plan doc and the design doc should match).

**Step 2: Commit any final cleanups**

If any dangling references are found, fix and commit them.
