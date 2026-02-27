# Authentication & User Management Design

## Overview

Add user authentication, RBAC, and passkey support to netaudit. Single-tenant deployment where all users share data with role-based access control.

## Approach

django-allauth (v65+) with built-in WebAuthn/passkey support via its MFA module. JWT tokens for API auth via djangorestframework-simplejwt, bridged by dj-rest-auth. RBAC via Django groups synced from a role field.

## Dependencies

- `django-allauth[mfa]>=65.0,<66.0` — auth, registration, passkeys
- `dj-rest-auth>=7.0,<8.0` — REST API auth endpoints bridging allauth + simplejwt
- `djangorestframework-simplejwt>=5.3,<6.0` — JWT tokens for API

## Data Model

Custom User model extending `AbstractUser` in `accounts` app:

- `role` (CharField, choices: admin/editor/viewer, default: viewer)
- `is_api_enabled` (BooleanField, default: True)
- `created_at` / `updated_at` timestamps

A signal syncs `role` to a corresponding Django group on save, giving us both `user.role == "admin"` and `user.has_perm()`.

Passkey/WebAuthn credentials managed by allauth's `Authenticator` model. JWT uses stateless access tokens with blacklisting enabled for refresh token revocation.

No changes to existing models (devices, rules, audits). No ownership fields — single-tenant, shared data.

## RBAC Permissions

| Resource | Viewer | Editor | Admin |
|---|---|---|---|
| Devices | read | read, create, edit, delete | full + manage headers |
| Simple Rules | read | read, create, edit, delete | full |
| Custom Rules | read | read, create, edit, delete | full |
| Audit Runs | read, view results | read, trigger manual runs | full |
| Audit Schedules | read | read, create, edit, delete | full |
| Dashboard | read | read | full |
| Users | — | view own profile | full CRUD, assign roles |
| API Tokens | manage own | manage own | manage own + revoke others |
| Passkeys/MFA | manage own | manage own | manage own |

Enforcement:

- DRF API: custom permission classes (`IsAdminRole`, `IsEditorOrAbove`, `IsViewerOrAbove`)
- HTML views: `@role_required("editor")` decorator
- Templates: context processor exposes `user.role` for conditional rendering

First user created gets `admin` role. Subsequent registrations default to `viewer`.

## Auth Flows

### HTML/HTMX (session-based)

- Registration: `GET/POST /accounts/register/` — allauth signup, assigns viewer role
- Login (password): `GET/POST /accounts/login/` — allauth login, sets session cookie
- Login (passkey): allauth WebAuthn flow — browser prompt, fido2 verification, sets session
- Passkey enrollment: `GET/POST /accounts/mfa/webauthn/` — add/remove passkeys
- Password reset: allauth email-based flow
- Logout: `POST /accounts/logout/` — clears session

### API (JWT)

- Obtain tokens: `POST /api/v1/auth/login/` — username+password, returns access+refresh tokens
- Refresh: `POST /api/v1/auth/token/refresh/` — exchange refresh for new access token
- Revoke: `POST /api/v1/auth/logout/` — blacklists refresh token
- Current user: `GET /api/v1/auth/user/` — returns user info + role

## Custom Middleware

`AuthHookMiddleware` sits after Django's `AuthenticationMiddleware`. Three hook points:

- `pre_authenticate(request)` — before view dispatch (IP allowlisting, rate limiting)
- `post_authenticate(request)` — after auth resolved, before view (audit logging, role enrichment)
- `on_response(request, response)` — on response (headers, logging)

Hooks configured via setting:

```python
AUTH_HOOKS = [
    "accounts.hooks.AuditLogHook",
    "accounts.hooks.IPAllowlistHook",
]
```

Each hook is a class with those three methods (all optional, default no-op).

## Pluggable Backends

allauth's adapter pattern via custom `AccountAdapter` in `accounts/adapters.py`. Adding OIDC/SAML later requires only installing a provider package and adding config.

## Protected Routes

- All HTML views redirect unauthenticated users to `/accounts/login/`
- All API endpoints return 401 for missing/invalid tokens
- Public routes: login, register, password reset only

## UI Changes

New pages:

- Login, register, password reset (allauth template overrides extending `base.html`)
- MFA/passkey management page
- User profile page (edit profile, manage passkeys, API tokens)
- User management page (admin only — list users, change roles)

Sidebar updates:

- User info display (name + role badge) at bottom
- "Users" link (admin only)
- "Profile" link
- "Logout" button

Existing templates unchanged beyond sidebar links and auth check wrappers.

## File Structure

```
backend/
├── accounts/                      # NEW app
│   ├── models.py                  # Custom User model
│   ├── admin.py                   # User admin
│   ├── adapters.py                # Custom allauth AccountAdapter
│   ├── forms.py                   # Profile, user management forms
│   ├── views_html.py              # Profile, user management (HTMX)
│   ├── views.py                   # DRF views beyond dj-rest-auth
│   ├── serializers.py             # User serializer
│   ├── permissions.py             # Role-based permission classes
│   ├── decorators.py              # @role_required
│   ├── middleware.py              # AuthHookMiddleware
│   ├── hooks.py                   # Example hooks (audit log, IP allowlist)
│   ├── signals.py                 # Sync role to Django group
│   ├── urls.py                    # API auth routes
│   ├── urls_html.py               # HTML routes
│   ├── context_processors.py      # Expose role to templates
│   └── tests.py
├── templates/account/             # NEW — allauth overrides
├── templates/mfa/                 # NEW — MFA template overrides
├── templates/accounts/            # NEW — profile, user management
├── templates/partials/sidebar.html  # MODIFIED
├── config/settings/base.py          # MODIFIED
├── config/urls.py                   # MODIFIED
├── devices/views.py                 # MODIFIED — permission_classes
├── devices/views_html.py            # MODIFIED — @role_required
├── rules/views.py                   # MODIFIED — permission_classes
├── audits/views.py                  # MODIFIED — permission_classes
├── audits/views_html.py             # MODIFIED — @role_required
└── requirements.txt                 # MODIFIED
```
