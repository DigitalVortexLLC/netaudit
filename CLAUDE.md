# CLAUDE.md

## Project Overview

NetAudit is a full-stack network device compliance auditing system. It validates network device configurations against defined rules via SSH (Netmiko), supports scheduled audits with live WebSocket updates, and provides role-based access control (Admin, Editor, Viewer).

## Tech Stack

- **Backend:** Django 5.1+, Django REST Framework, Django Channels, Django-Q2, PostgreSQL 16, Redis 7
- **Frontend:** React 19, TypeScript 5.9, Vite 7, Tailwind CSS 4, shadcn/ui, React Query v5
- **Deployment:** Docker Compose (Nginx, Daphne, PostgreSQL, Redis, Q2 worker)

## Project Structure

```
backend/          # Django REST API
  accounts/       # Auth & user management (JWT, roles)
  audits/         # Audit runs, schedules, results
  devices/        # Device & group management
  rules/          # Simple patterns + custom Python rules
  notifications/  # Webhook providers
  config/         # Django settings (base, development, production)
frontend/         # React SPA (Vite)
  src/pages/      # Route components
  src/components/ # UI components (shadcn/ui in components/ui/)
  src/hooks/      # Custom React hooks (API calls via React Query)
  src/lib/        # Utilities (API client, helpers)
  src/types/      # TypeScript type definitions
```

## Common Commands

### Frontend (run from `frontend/`)

```bash
npm install        # Install dependencies
npm run dev        # Dev server on port 5173
npm run build      # TypeScript check + production build
npm run lint       # ESLint
```

### Backend (run from `backend/`)

```bash
pip install -r requirements.txt          # Install dependencies
python manage.py migrate                 # Run migrations
python manage.py runserver               # Dev server on port 8000
python manage.py qcluster               # Start task queue worker
pytest                                   # Run tests
```

### Docker

```bash
./start.sh              # Build and start all services
docker compose up -d    # Start in background
docker compose down     # Stop services
```

## Development Guidelines

- Django settings default to `config.settings.development`; production uses `config.settings.production`
- API base path: `/api/v1/`; WebSocket: `/ws/audits/<audit_id>/`
- Frontend API client is in `frontend/src/lib/api.ts`; uses Axios with JWT auth
- Commit style: conventional commits (`feat:`, `fix:`, `test:`, `docs:`)
- Backend tests use pytest with Django fixture mixins; run `pytest` from `backend/`
- Frontend uses ESLint flat config with TypeScript rules
- Sensitive fields use `django-encrypted-model-fields`; never log or expose credentials
- Custom rules are validated via Python AST before saving
- Default pagination: 25 items/page

## Environment Variables

Key variables (see `.env.example`): `POSTGRES_*`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `REDIS_URL`, `FIELD_ENCRYPTION_KEY`, `VITE_API_URL`
