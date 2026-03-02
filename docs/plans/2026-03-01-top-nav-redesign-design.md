# Top Navigation Redesign

## Overview

Replace the fixed left sidebar with a top navigation bar using pill/bubble buttons. Grouped items use hover dropdowns. User controls on the right.

## Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  Netaudit    [Dashboard] [Netbox ▾] [Rules ▾] [Auditing ▾]   🔍 ⚙ 👤│
└─────────────────────────────────────────────────────────────────────┘
│                                                                     │
│                     Full-width content area                         │
│                                                                     │
```

## Navigation Groups

| Pill | Type | Items |
|------|------|-------|
| Dashboard | Direct link | `/` |
| Netbox | Hover dropdown | Devices (`/devices`), Groups (`/groups`) |
| Rules | Hover dropdown | Simple Rules (`/rules/simple`), Custom Rules (`/rules/custom`) |
| Auditing | Hover dropdown | Audits (`/audits`), Schedules (`/schedules`) |

## Right Controls

- Search button (opens existing command palette, shows keyboard hint)
- Settings gear icon (links to `/settings`)
- User avatar (click dropdown with username, role badge, Profile link, Logout button)
- Admin-only: Users page accessible via command palette or Settings area

## Styling

- Nav bar: sticky top, ~56px, background `#1a1a2e` (matches old sidebar)
- Active pill: `bg-primary text-primary-foreground` highlight
- Inactive pills: transparent with `text-foreground`, hover shows subtle background
- Hover dropdowns: card-style with shadow and border, ~100ms hover delay
- Parent pill stays highlighted while dropdown is open

## Breadcrumbs

Removed. The nav pills indicate current section; page titles provide specifics.

## Files Changed

- **Rewrite**: `app-layout.tsx` - remove sidebar reference, full-width content
- **Rewrite**: `app-header.tsx` - becomes the top nav bar (logo + pills + controls)
- **Delete**: `app-sidebar.tsx` - no longer needed
- **No changes**: command-palette.tsx, page components, routing
