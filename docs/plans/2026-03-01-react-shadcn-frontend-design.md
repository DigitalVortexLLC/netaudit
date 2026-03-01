# React + shadcn/ui Frontend Design

**Date:** 2026-03-01
**Status:** Approved

## Overview

Rebuild the Netaudit web frontend as a fully separate React SPA using shadcn/ui, replacing the current Django template + HTMX approach. Django remains as a pure API server. The existing color scheme is preserved by customizing shadcn's CSS variables.

Auth pages (login, signup, password reset) keep the existing split-card visual style but are rebuilt in React.

## Tech Stack

- **Vite + React 18 + TypeScript**
- **shadcn/ui** (Radix UI + Tailwind CSS)
- **React Router v6** — client-side routing
- **TanStack Query (React Query)** — server state, caching, polling
- **Axios** — HTTP client with JWT interceptor
- **Lucide React** — icons (shadcn's icon set)
- **Zod** — form validation schemas

## Architecture

```
[React SPA :5173]  ──HTTP/JWT──>  [Django API :8000 /api/v1/]
```

- Fully separate frontend and backend
- CORS already configured (`CORS_ALLOW_ALL_ORIGINS = True` in dev)
- JWT auth: access token (30 min) + refresh token (7 days)
- React SPA served by Vite in dev; built to static files for production

## Color Scheme (Preserved)

Map existing colors to shadcn CSS variables (HSL):

| Element           | Hex       | Role in shadcn             |
| ----------------- | --------- | -------------------------- |
| `#242424`         | Content bg | `--background`            |
| `#1a1a2e`         | Sidebar bg | `--sidebar-background`    |
| `#2d2d2d`         | Cards      | `--card`                  |
| `#64b5f6`         | Accent     | `--primary`               |
| `#1976d2`         | Buttons    | `--primary` (darker)      |
| `#e0e0e0`         | Body text  | `--foreground`            |
| `#b0b0c8`         | Muted text | `--muted-foreground`      |
| `#2a2a4a`         | Borders    | `--border`                |
| `#333`            | Input bg   | `--input`                 |
| `#3a3a3a`         | Separator  | `--border`                |

Badge colors remain unchanged (see existing `style.css` for full palette).

## Layout

### Sidebar (fixed left)
- App name "Netaudit" at top
- Navigation with Lucide icons:
  - `LayoutDashboard` — Dashboard
  - `Server` — Devices
  - `FolderTree` — Groups
  - `Shield` — Simple Rules
  - `Code` — Custom Rules
  - `ClipboardCheck` — Audits
  - `Clock` — Schedules
  - `Settings` — Settings
  - `Users` — Users (admin only, role-gated)
- User section at bottom: username, role badge, profile link, logout
- Active item: `#64b5f6` text + left border accent
- Collapsible on smaller screens

### Topbar (header)
- Breadcrumbs (e.g., "Devices > router-01")
- Command palette trigger (Cmd+K / Ctrl+K)
- User avatar/initials circle

### Command Palette (Cmd+K)
- shadcn `CommandDialog` component
- Quick navigation to any page
- Search devices, rules, audits by name
- Recent items section

## Pages

### Dashboard (`/`)
- Summary cards: device count, recent audit count (24h), pass rate (7d)
- shadcn `Card` components with metric + trend display
- Recent audits table (shadcn `Table`)
- API: `GET /api/v1/dashboard/summary/`, `GET /api/v1/audits/?ordering=-created_at&page_size=10`

### List Pages (Devices, Groups, Rules, Audits, Schedules, Users)
- shadcn `DataTable` pattern: sortable columns, filtering, pagination
- Search bar + filter dropdowns at top
- "Add New" primary button in page header
- Row actions: Edit, Delete (with confirmation dialog)
- Empty state component when no data
- Pagination: page numbers matching Django's 25/page default

### Detail Pages (Device, Group, Audit Run)
- Card-based layout with key-value detail grid
- Related data in sections:
  - Device: headers table, group memberships
  - Group: member devices list, "Run Audit" action
  - Audit: rule results table with outcome badges, config snapshot viewer
- Action buttons: Edit, Delete, Test Connection, Run Audit

### Audit Detail — Real-time Status
- TanStack Query `refetchInterval: 3000` while status is `pending`/`fetching_config`/`running_rules`
- Stop polling on terminal status (`completed`/`failed`)
- Visual progress indicator (spinner or step indicator)
- Results populate as they arrive

### Form Pages (Device, Group, Rule, Schedule, Settings, User Edit, Profile)
- shadcn `Form` components with Zod validation schemas
- Card wrapper for form sections
- Inline field error messages
- Device form: dynamic header rows (add/remove)
- Custom rule form: code editor textarea (monospace)
- Submit + Cancel buttons

### Auth Pages (Login, Signup, Password Reset)
- Rebuilt in React but preserving current split-card visual style
- Left panel: navy gradient brand section with "Netaudit" logo
- Right panel: form on dark card background
- NOT using shadcn styling — custom CSS matching existing auth design

## API Integration

### Axios Instance
- Base URL: `http://localhost:8000/api/v1/`
- Request interceptor: attach `Authorization: Bearer <access_token>`
- Response interceptor: on 401, attempt token refresh via `/auth/token/refresh/`
- If refresh fails: clear tokens, redirect to `/login`

### Token Storage
- Access token: in-memory (React state/context)
- Refresh token: httpOnly cookie (managed by dj-rest-auth, `JWT_AUTH_HTTPONLY: True`)

### TanStack Query Hooks
One custom hook per resource:
- `useDevices()`, `useDevice(id)`, `useCreateDevice()`, `useUpdateDevice()`, `useDeleteDevice()`
- `useGroups()`, `useGroup(id)`, `useCreateGroup()`, etc.
- `useSimpleRules()`, `useCustomRules()`, etc.
- `useAuditRuns()`, `useAuditRun(id)`, `useAuditResults(id)`, `useCreateAudit()`
- `useSchedules()`, etc.
- `useDashboardSummary()`
- `useSiteSettings()`, `useUpdateSiteSettings()`
- `useUsers()` (admin only), `useProfile()`, `useUpdateProfile()`

Mutations invalidate relevant query caches on success.

### Role-Based UI
- Auth context provides `user.role` (`admin` | `editor` | `viewer`)
- Sidebar: hide "Users" for non-admins
- List pages: hide Add/Edit/Delete for viewers
- Protected route wrapper redirects unauthorized users to dashboard

## Project Structure

```
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── components.json              # shadcn config
├── src/
│   ├── main.tsx                 # Entry point
│   ├── App.tsx                  # Router + providers
│   ├── globals.css              # Tailwind base + shadcn theme (custom colors)
│   ├── lib/
│   │   ├── utils.ts             # shadcn cn() helper
│   │   └── api.ts               # Axios instance + interceptors
│   ├── hooks/
│   │   ├── use-auth.ts
│   │   ├── use-devices.ts
│   │   ├── use-groups.ts
│   │   ├── use-rules.ts
│   │   ├── use-audits.ts
│   │   ├── use-schedules.ts
│   │   ├── use-settings.ts
│   │   └── use-users.ts
│   ├── components/
│   │   ├── ui/                  # shadcn components (auto-generated)
│   │   ├── layout/
│   │   │   ├── app-sidebar.tsx
│   │   │   ├── app-header.tsx
│   │   │   ├── command-palette.tsx
│   │   │   └── breadcrumbs.tsx
│   │   ├── data-table/          # Reusable table + columns
│   │   │   ├── data-table.tsx
│   │   │   └── data-table-pagination.tsx
│   │   └── badges.tsx           # Status/severity badge components
│   ├── pages/
│   │   ├── auth/
│   │   │   ├── login.tsx
│   │   │   ├── signup.tsx
│   │   │   └── password-reset.tsx
│   │   ├── dashboard.tsx
│   │   ├── devices/
│   │   │   ├── list.tsx
│   │   │   ├── detail.tsx
│   │   │   └── form.tsx
│   │   ├── groups/
│   │   │   ├── list.tsx
│   │   │   ├── detail.tsx
│   │   │   └── form.tsx
│   │   ├── rules/
│   │   │   ├── simple-list.tsx
│   │   │   ├── simple-form.tsx
│   │   │   ├── custom-list.tsx
│   │   │   └── custom-form.tsx
│   │   ├── audits/
│   │   │   ├── list.tsx
│   │   │   └── detail.tsx
│   │   ├── schedules/
│   │   │   ├── list.tsx
│   │   │   └── form.tsx
│   │   ├── settings.tsx
│   │   ├── users/
│   │   │   ├── list.tsx
│   │   │   └── edit.tsx
│   │   └── profile.tsx
│   └── types/
│       ├── device.ts
│       ├── rule.ts
│       ├── audit.ts
│       ├── schedule.ts
│       ├── settings.ts
│       └── user.ts
```

## API Endpoints Reference

| Endpoint                              | Methods         | Purpose                    |
| ------------------------------------- | --------------- | -------------------------- |
| `/auth/login/`                        | POST            | Get JWT tokens             |
| `/auth/logout/`                       | POST            | Blacklist refresh token    |
| `/auth/register/`                     | POST            | User registration          |
| `/auth/token/refresh/`                | POST            | Refresh access token       |
| `/auth/user/`                         | GET             | Current user info          |
| `/devices/`                           | GET, POST       | List/create devices        |
| `/devices/{id}/`                      | GET, PUT, DEL   | Device CRUD                |
| `/devices/{id}/test_connection/`      | POST            | Test device API connection |
| `/groups/`                            | GET, POST       | List/create groups         |
| `/groups/{id}/`                       | GET, PUT, DEL   | Group CRUD                 |
| `/groups/{id}/run_audit/`             | POST            | Run audit on group devices |
| `/rules/simple/`                      | GET, POST       | List/create simple rules   |
| `/rules/simple/{id}/`                 | GET, PUT, DEL   | Simple rule CRUD           |
| `/rules/custom/`                      | GET, POST       | List/create custom rules   |
| `/rules/custom/{id}/`                 | GET, PUT, DEL   | Custom rule CRUD           |
| `/rules/custom/{id}/validate/`        | POST            | Validate Python syntax     |
| `/audits/`                            | GET, POST       | List/create audit runs     |
| `/audits/{id}/`                       | GET             | Audit run detail           |
| `/audits/{id}/results/`              | GET             | Audit rule results         |
| `/audits/{id}/config/`               | GET             | Config snapshot            |
| `/schedules/`                         | GET, POST       | List/create schedules      |
| `/schedules/{id}/`                    | GET, PUT, DEL   | Schedule CRUD              |
| `/settings/`                          | GET, PUT, PATCH | Site settings              |
| `/dashboard/summary/`                | GET             | Dashboard stats            |
