# Tags & Comments for Audit Runs

## Overview

Add the ability to tag and comment on audit runs. Tags are configured on the settings page (predefined) but can also be created ad-hoc on the audit detail page. Comments support markdown, editing, and deletion by the author.

## Requirements

- Tags: multiple per audit, predefined list on settings page + ad-hoc creation
- Tag colors: auto-assigned from a fixed palette based on tag name hash
- Comments: markdown-formatted, editable/deletable by author, with author and timestamp
- Audit list page: show tags per row, filter by tag
- Settings page: manage predefined tags (add/delete)

## Backend

### Models (in `audits/models.py`)

**Tag**
- `id` (auto PK)
- `name` (CharField, max_length=50, unique)
- `created_at` (DateTimeField, auto_now_add)

**AuditRun** (existing, add M2M):
- `tags = ManyToManyField(Tag, blank=True, related_name="audit_runs")`

**AuditComment**
- `id` (auto PK)
- `audit_run` (FK to AuditRun, on_delete=CASCADE, related_name="comments")
- `author` (FK to User, on_delete=SET_NULL, null=True)
- `content` (TextField, stores markdown)
- `created_at` (DateTimeField, auto_now_add)
- `updated_at` (DateTimeField, auto_now)

### Serializers

- `TagSerializer`: id, name, created_at
- `AuditCommentSerializer`: id, audit_run, author (id), author_name (read-only), content, created_at, updated_at
- `AuditRunListSerializer`: add `tags` field (nested TagSerializer, many=True, read_only)
- `AuditRunDetailSerializer`: add `tags` and `comments` fields

### API Endpoints

| Endpoint | Methods | Permission | Purpose |
|---|---|---|---|
| `/api/v1/tags/` | GET, POST | Viewer(GET), Editor(POST) | List/create global tags |
| `/api/v1/tags/{id}/` | DELETE | Editor | Delete a tag |
| `/api/v1/audits/{id}/tags/` | POST | Editor | Add tag(s) to audit run |
| `/api/v1/audits/{id}/tags/{tag_id}/` | DELETE | Editor | Remove tag from audit run |
| `/api/v1/audits/{id}/comments/` | GET, POST | Viewer(GET), Editor(POST) | List/create comments |
| `/api/v1/audits/{id}/comments/{cid}/` | PUT, DELETE | Author only | Edit/delete own comment |

Existing `AuditRunViewSet.filterset_fields` gets `tags` added.

### URL Configuration

Add tag and comment routes to `audits/urls.py` and register in `config/urls.py`.

## Frontend

### Types (`types/audit.ts`)

```typescript
interface Tag {
  id: number;
  name: string;
  created_at: string;
}

interface AuditComment {
  id: number;
  audit_run: number;
  author: number | null;
  author_name: string;
  content: string;
  created_at: string;
  updated_at: string;
}

// AuditRun and AuditRunDetail get `tags: Tag[]`
// AuditRunDetail gets `comments: AuditComment[]`
```

### Hooks (`hooks/use-tags.ts`, `hooks/use-comments.ts`)

**Tags:**
- `useTags()` - GET /tags/
- `useCreateTag()` - POST /tags/
- `useDeleteTag()` - DELETE /tags/{id}/
- `useAddAuditTag(auditId)` - POST /audits/{id}/tags/
- `useRemoveAuditTag(auditId)` - DELETE /audits/{id}/tags/{tagId}/

**Comments:**
- `useAuditComments(auditId)` - GET /audits/{id}/comments/
- `useCreateComment(auditId)` - POST /audits/{id}/comments/
- `useUpdateComment(auditId)` - PUT /audits/{id}/comments/{cid}/
- `useDeleteComment(auditId)` - DELETE /audits/{id}/comments/{cid}/

### Settings Page

New "Tags" card below existing "Site Settings" card:
- List of tags as colored badges with "x" delete button
- Input + "Add" button to create
- Empty state message when no tags exist

### Audit Detail Page

**Tags section** (inline in the Details card or as a separate small section):
- Current tags as colored badges with "x" to remove
- Combobox/popover: shows predefined tags, allows typing new tag name
- New tags created on-the-fly via POST /tags/ then POST /audits/{id}/tags/

**Comments section** (new card before Config Snapshot):
- Chronological list of comments
- Each comment: author avatar/name, relative time, markdown content
- Edit/delete actions for own comments
- Textarea with submit button at the bottom
- Markdown preview toggle

### Audit List Page

- Tags column showing small badges
- Tag filter dropdown in existing filter controls

### Tag Colors

Fixed 10-color palette. Color index = simple hash of tag name % 10.

```typescript
const TAG_COLORS = [
  "bg-blue-100 text-blue-800",
  "bg-green-100 text-green-800",
  "bg-yellow-100 text-yellow-800",
  "bg-red-100 text-red-800",
  "bg-purple-100 text-purple-800",
  "bg-pink-100 text-pink-800",
  "bg-indigo-100 text-indigo-800",
  "bg-orange-100 text-orange-800",
  "bg-teal-100 text-teal-800",
  "bg-cyan-100 text-cyan-800",
];
```
