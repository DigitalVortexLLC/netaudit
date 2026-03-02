# Tags & Comments Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add tagging and commenting to audit run detail pages, with tag management on the settings page and tag filtering on the audit list page.

**Architecture:** New `Tag` and `AuditComment` Django models with M2M relationship between `AuditRun` and `Tag`. REST API endpoints for CRUD on both. React frontend with hooks, tag badge component, comment card with markdown rendering. Tags use auto-assigned colors from a 10-color palette.

**Tech Stack:** Django REST Framework, React 19, TanStack React Query, shadcn/ui (Radix), react-markdown, Tailwind CSS

---

### Task 1: Backend — Tag and AuditComment Models + Migration

**Files:**
- Modify: `backend/audits/models.py`

**Step 1: Add Tag model, AuditComment model, and M2M field to AuditRun**

Add to `backend/audits/models.py` after the existing imports and before `class AuditRun`:

```python
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
```

Add to `AuditRun` class (after `created_at` field):

```python
    tags = models.ManyToManyField("Tag", blank=True, related_name="audit_runs")
```

Add after `AuditSchedule` class:

```python
class AuditComment(models.Model):
    audit_run = models.ForeignKey(
        AuditRun,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_comments",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author} on AuditRun {self.audit_run_id}"
```

**Step 2: Generate and run migration**

Run:
```bash
cd backend && python manage.py makemigrations audits
python manage.py migrate
```

Expected: Migration created and applied successfully.

**Step 3: Commit**

```bash
git add backend/audits/models.py backend/audits/migrations/
git commit -m "feat: add Tag and AuditComment models with AuditRun M2M"
```

---

### Task 2: Backend — Tag and AuditComment Model Tests

**Files:**
- Modify: `backend/audits/tests.py`

**Step 1: Add model tests for Tag and AuditComment**

Add to `backend/audits/tests.py` after `AuditScheduleModelTests` and before the API tests section. Also add `Tag, AuditComment` to the import from `audits.models`.

```python
class TagModelTests(AuditFixtureMixin, TestCase):
    """Tests for the Tag model."""

    def test_create_tag(self):
        tag = Tag.objects.create(name="production")
        tag.refresh_from_db()
        self.assertEqual(tag.name, "production")
        self.assertIsNotNone(tag.created_at)

    def test_tag_name_unique(self):
        Tag.objects.create(name="production")
        with self.assertRaises(Exception):
            Tag.objects.create(name="production")

    def test_str(self):
        tag = Tag.objects.create(name="maintenance")
        self.assertEqual(str(tag), "maintenance")

    def test_ordering_by_name(self):
        Tag.objects.create(name="zebra")
        Tag.objects.create(name="alpha")
        tags = list(Tag.objects.all())
        self.assertEqual(tags[0].name, "alpha")
        self.assertEqual(tags[1].name, "zebra")


class AuditRunTagTests(AuditFixtureMixin, TestCase):
    """Tests for AuditRun <-> Tag M2M relationship."""

    def test_add_tag_to_audit_run(self):
        run = self.create_audit_run()
        tag = Tag.objects.create(name="production")
        run.tags.add(tag)
        self.assertIn(tag, run.tags.all())

    def test_multiple_tags_on_audit_run(self):
        run = self.create_audit_run()
        t1 = Tag.objects.create(name="production")
        t2 = Tag.objects.create(name="maintenance")
        run.tags.add(t1, t2)
        self.assertEqual(run.tags.count(), 2)

    def test_tag_reverse_relation(self):
        run = self.create_audit_run()
        tag = Tag.objects.create(name="production")
        run.tags.add(tag)
        self.assertIn(run, tag.audit_runs.all())

    def test_remove_tag_from_audit_run(self):
        run = self.create_audit_run()
        tag = Tag.objects.create(name="production")
        run.tags.add(tag)
        run.tags.remove(tag)
        self.assertEqual(run.tags.count(), 0)


class AuditCommentModelTests(AuditFixtureMixin, TestCase):
    """Tests for the AuditComment model."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com",
            password="testpass123", role="editor",
        )

    def test_create_comment(self):
        run = self.create_audit_run()
        comment = AuditComment.objects.create(
            audit_run=run, author=self.user, content="Looks good",
        )
        comment.refresh_from_db()
        self.assertEqual(comment.content, "Looks good")
        self.assertEqual(comment.author, self.user)
        self.assertIsNotNone(comment.created_at)
        self.assertIsNotNone(comment.updated_at)

    def test_comment_ordering_by_created_at(self):
        run = self.create_audit_run()
        c1 = AuditComment.objects.create(audit_run=run, author=self.user, content="First")
        c2 = AuditComment.objects.create(audit_run=run, author=self.user, content="Second")
        comments = list(AuditComment.objects.all())
        self.assertEqual(comments[0], c1)
        self.assertEqual(comments[1], c2)

    def test_cascade_delete_on_audit_run(self):
        run = self.create_audit_run()
        AuditComment.objects.create(audit_run=run, author=self.user, content="Test")
        run.delete()
        self.assertEqual(AuditComment.objects.count(), 0)

    def test_set_null_on_author_delete(self):
        run = self.create_audit_run()
        comment = AuditComment.objects.create(
            audit_run=run, author=self.user, content="Test",
        )
        self.user.delete()
        comment.refresh_from_db()
        self.assertIsNone(comment.author)

    def test_str(self):
        run = self.create_audit_run()
        comment = AuditComment.objects.create(
            audit_run=run, author=self.user, content="Test",
        )
        self.assertIn("testuser", str(comment))
        self.assertIn(str(run.pk), str(comment))
```

**Step 2: Run tests**

Run: `cd backend && python manage.py test audits.tests.TagModelTests audits.tests.AuditRunTagTests audits.tests.AuditCommentModelTests -v2`

Expected: All tests pass.

**Step 3: Commit**

```bash
git add backend/audits/tests.py
git commit -m "test: add model tests for Tag, AuditRunTag M2M, and AuditComment"
```

---

### Task 3: Backend — Tag and Comment Serializers

**Files:**
- Modify: `backend/audits/serializers.py`

**Step 1: Add TagSerializer and AuditCommentSerializer**

Add to `backend/audits/serializers.py`:

```python
from audits.models import AuditRun, AuditSchedule, RuleResult, Tag, AuditComment


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "created_at"]
        read_only_fields = ["created_at"]


class AuditCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True, default="Deleted user")

    class Meta:
        model = AuditComment
        fields = ["id", "audit_run", "author", "author_name", "content", "created_at", "updated_at"]
        read_only_fields = ["author", "audit_run", "created_at", "updated_at"]
```

**Step 2: Add `tags` to `AuditRunListSerializer` and `AuditRunDetailSerializer`**

Update `AuditRunListSerializer`:

```python
class AuditRunListSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = AuditRun
        fields = [
            "id", "device", "device_name", "status", "trigger",
            "summary", "started_at", "completed_at", "created_at", "tags",
        ]
```

Update `AuditRunDetailSerializer`:

```python
class AuditRunDetailSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    results = RuleResultSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    comments = AuditCommentSerializer(many=True, read_only=True)

    class Meta:
        model = AuditRun
        fields = [
            "id", "device", "device_name", "status", "trigger",
            "summary", "started_at", "completed_at", "created_at",
            "results", "error_message", "config_fetched_at", "tags", "comments",
        ]
```

**Step 3: Commit**

```bash
git add backend/audits/serializers.py
git commit -m "feat: add Tag and AuditComment serializers, add tags/comments to audit serializers"
```

---

### Task 4: Backend — Tag and Comment API Views + URLs

**Files:**
- Modify: `backend/audits/views.py`
- Modify: `backend/audits/urls.py`

**Step 1: Add TagViewSet and comment views**

Add to `backend/audits/views.py`:

```python
from audits.models import AuditRun, AuditSchedule, RuleResult, Tag, AuditComment
from audits.serializers import (
    AuditRunCreateSerializer, AuditRunDetailSerializer, AuditRunListSerializer,
    AuditScheduleSerializer, RuleResultSerializer, TagSerializer, AuditCommentSerializer,
)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_permissions(self):
        if self.action == "list":
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]
```

Add tag/comment actions to `AuditRunViewSet`:

```python
    @action(detail=True, methods=["get", "post"], url_path="tags")
    def manage_tags(self, request, pk=None):
        audit_run = self.get_object()
        if request.method == "GET":
            serializer = TagSerializer(audit_run.tags.all(), many=True)
            return Response(serializer.data)
        # POST: add tag by id or name
        tag_id = request.data.get("tag_id")
        tag_name = request.data.get("name")
        if tag_id:
            try:
                tag = Tag.objects.get(pk=tag_id)
            except Tag.DoesNotExist:
                return Response({"detail": "Tag not found."}, status=status.HTTP_404_NOT_FOUND)
        elif tag_name:
            tag, _ = Tag.objects.get_or_create(name=tag_name.strip()[:50])
        else:
            return Response({"detail": "Provide tag_id or name."}, status=status.HTTP_400_BAD_REQUEST)
        audit_run.tags.add(tag)
        return Response(TagSerializer(tag).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="tags/(?P<tag_id>[^/.]+)")
    def remove_tag(self, request, pk=None, tag_id=None):
        audit_run = self.get_object()
        try:
            tag = Tag.objects.get(pk=tag_id)
        except Tag.DoesNotExist:
            return Response({"detail": "Tag not found."}, status=status.HTTP_404_NOT_FOUND)
        audit_run.tags.remove(tag)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def manage_comments(self, request, pk=None):
        audit_run = self.get_object()
        if request.method == "GET":
            comments = audit_run.comments.select_related("author").all()
            serializer = AuditCommentSerializer(comments, many=True)
            return Response(serializer.data)
        serializer = AuditCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(audit_run=audit_run, author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["put", "delete"], url_path="comments/(?P<comment_id>[^/.]+)")
    def manage_comment(self, request, pk=None, comment_id=None):
        audit_run = self.get_object()
        try:
            comment = audit_run.comments.get(pk=comment_id)
        except AuditComment.DoesNotExist:
            return Response({"detail": "Comment not found."}, status=status.HTTP_404_NOT_FOUND)
        if comment.author != request.user:
            return Response({"detail": "You can only edit your own comments."}, status=status.HTTP_403_FORBIDDEN)
        if request.method == "DELETE":
            comment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        # PUT
        serializer = AuditCommentSerializer(comment, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
```

Update `AuditRunViewSet.get_permissions` to include the new actions:

```python
    def get_permissions(self):
        if self.action in ("list", "retrieve", "results", "config", "manage_tags", "manage_comments"):
            if self.request.method == "GET":
                return [IsViewerOrAbove()]
        if self.action in ("manage_comment",):
            return [IsEditorOrAbove()]
        if self.action in ("list", "retrieve", "results", "config"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]
```

Also add `"tags"` to `AuditRunViewSet.filterset_fields`:

```python
    filterset_fields = ["device", "status", "trigger", "tags"]
```

And update the queryset to prefetch tags:

```python
    queryset = AuditRun.objects.select_related("device").prefetch_related("tags")
```

**Step 2: Register TagViewSet in URLs**

Update `backend/audits/urls.py`:

```python
from audits.views import AuditRunViewSet, AuditScheduleViewSet, DashboardSummaryView, TagViewSet

router = DefaultRouter()
router.register("audits", AuditRunViewSet, basename="auditrun")
router.register("schedules", AuditScheduleViewSet, basename="auditschedule")
router.register("tags", TagViewSet, basename="tag")
```

**Step 3: Commit**

```bash
git add backend/audits/views.py backend/audits/urls.py
git commit -m "feat: add Tag CRUD, audit tag management, and comment API endpoints"
```

---

### Task 5: Backend — API Tests for Tags and Comments

**Files:**
- Modify: `backend/audits/tests.py`

**Step 1: Add API tests for tags**

Add after `DashboardSummaryAPITests`:

```python
class TagAPITests(AuditFixtureMixin, APITestCase):
    """Tests for the Tag REST endpoints."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com",
            password="testpass123", role="admin",
        )
        self.client.force_authenticate(user=self.user)

    def test_list_tags_empty(self):
        url = reverse("tag-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_tag(self):
        url = reverse("tag-list")
        response = self.client.post(url, {"name": "production"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Tag.objects.count(), 1)
        self.assertEqual(Tag.objects.first().name, "production")

    def test_create_duplicate_tag(self):
        Tag.objects.create(name="production")
        url = reverse("tag-list")
        response = self.client.post(url, {"name": "production"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_tag(self):
        tag = Tag.objects.create(name="production")
        url = reverse("tag-detail", kwargs={"pk": tag.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Tag.objects.count(), 0)


class AuditRunTagAPITests(AuditFixtureMixin, APITestCase):
    """Tests for adding/removing tags on audit runs."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com",
            password="testpass123", role="admin",
        )
        self.client.force_authenticate(user=self.user)
        self.device = self.create_device()
        self.run = self.create_audit_run(device=self.device)

    def test_add_tag_by_id(self):
        tag = Tag.objects.create(name="production")
        url = reverse("auditrun-manage-tags", kwargs={"pk": self.run.pk})
        response = self.client.post(url, {"tag_id": tag.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(tag, self.run.tags.all())

    def test_add_tag_by_name_creates_new(self):
        url = reverse("auditrun-manage-tags", kwargs={"pk": self.run.pk})
        response = self.client.post(url, {"name": "new-tag"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Tag.objects.filter(name="new-tag").exists())
        self.assertEqual(self.run.tags.count(), 1)

    def test_add_tag_by_name_reuses_existing(self):
        Tag.objects.create(name="existing")
        url = reverse("auditrun-manage-tags", kwargs={"pk": self.run.pk})
        response = self.client.post(url, {"name": "existing"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Tag.objects.filter(name="existing").count(), 1)

    def test_remove_tag(self):
        tag = Tag.objects.create(name="production")
        self.run.tags.add(tag)
        url = reverse("auditrun-remove-tag", kwargs={"pk": self.run.pk, "tag_id": tag.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.run.tags.count(), 0)

    def test_list_tags_on_audit(self):
        tag = Tag.objects.create(name="production")
        self.run.tags.add(tag)
        url = reverse("auditrun-manage-tags", kwargs={"pk": self.run.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_audit_detail_includes_tags(self):
        tag = Tag.objects.create(name="production")
        self.run.tags.add(tag)
        url = reverse("auditrun-detail", kwargs={"pk": self.run.pk})
        response = self.client.get(url)
        self.assertIn("tags", response.data)
        self.assertEqual(len(response.data["tags"]), 1)
        self.assertEqual(response.data["tags"][0]["name"], "production")

    def test_audit_list_includes_tags(self):
        tag = Tag.objects.create(name="production")
        self.run.tags.add(tag)
        url = reverse("auditrun-list")
        response = self.client.get(url)
        item = response.data["results"][0]
        self.assertIn("tags", item)
        self.assertEqual(len(item["tags"]), 1)

    def test_filter_audits_by_tag(self):
        tag = Tag.objects.create(name="production")
        self.run.tags.add(tag)
        run2 = self.create_audit_run(device=self.device)
        url = reverse("auditrun-list")
        response = self.client.get(url, {"tags": tag.pk})
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.run.pk)


class AuditCommentAPITests(AuditFixtureMixin, APITestCase):
    """Tests for the AuditComment REST endpoints."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com",
            password="testpass123", role="admin",
        )
        self.other_user = User.objects.create_user(
            username="other", email="other@test.com",
            password="testpass123", role="editor",
        )
        self.client.force_authenticate(user=self.user)
        self.device = self.create_device()
        self.run = self.create_audit_run(device=self.device)

    def test_list_comments_empty(self):
        url = reverse("auditrun-manage-comments", kwargs={"pk": self.run.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_create_comment(self):
        url = reverse("auditrun-manage-comments", kwargs={"pk": self.run.pk})
        response = self.client.post(url, {"content": "This looks good"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AuditComment.objects.count(), 1)
        comment = AuditComment.objects.first()
        self.assertEqual(comment.content, "This looks good")
        self.assertEqual(comment.author, self.user)

    def test_create_comment_includes_author_name(self):
        url = reverse("auditrun-manage-comments", kwargs={"pk": self.run.pk})
        response = self.client.post(url, {"content": "Test"}, format="json")
        self.assertEqual(response.data["author_name"], "testuser")

    def test_update_own_comment(self):
        comment = AuditComment.objects.create(
            audit_run=self.run, author=self.user, content="Original",
        )
        url = reverse("auditrun-manage-comment", kwargs={"pk": self.run.pk, "comment_id": comment.pk})
        response = self.client.put(url, {"content": "Updated"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertEqual(comment.content, "Updated")

    def test_cannot_update_other_users_comment(self):
        comment = AuditComment.objects.create(
            audit_run=self.run, author=self.other_user, content="Other's comment",
        )
        url = reverse("auditrun-manage-comment", kwargs={"pk": self.run.pk, "comment_id": comment.pk})
        response = self.client.put(url, {"content": "Hacked"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_own_comment(self):
        comment = AuditComment.objects.create(
            audit_run=self.run, author=self.user, content="To delete",
        )
        url = reverse("auditrun-manage-comment", kwargs={"pk": self.run.pk, "comment_id": comment.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(AuditComment.objects.count(), 0)

    def test_cannot_delete_other_users_comment(self):
        comment = AuditComment.objects.create(
            audit_run=self.run, author=self.other_user, content="Other's",
        )
        url = reverse("auditrun-manage-comment", kwargs={"pk": self.run.pk, "comment_id": comment.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_audit_detail_includes_comments(self):
        AuditComment.objects.create(
            audit_run=self.run, author=self.user, content="A comment",
        )
        url = reverse("auditrun-detail", kwargs={"pk": self.run.pk})
        response = self.client.get(url)
        self.assertIn("comments", response.data)
        self.assertEqual(len(response.data["comments"]), 1)
```

**Step 2: Run all audit tests**

Run: `cd backend && python manage.py test audits -v2`

Expected: All tests pass.

**Step 3: Commit**

```bash
git add backend/audits/tests.py
git commit -m "test: add API tests for tags, audit tagging, and comments"
```

---

### Task 6: Frontend — TypeScript Types

**Files:**
- Modify: `frontend/src/types/audit.ts`

**Step 1: Add Tag and AuditComment types, update AuditRun types**

```typescript
export interface Tag {
  id: number;
  name: string;
  created_at: string;
}

export interface AuditComment {
  id: number;
  audit_run: number;
  author: number | null;
  author_name: string;
  content: string;
  created_at: string;
  updated_at: string;
}
```

Add `tags: Tag[]` to `AuditRun` interface.
Add `tags: Tag[]` and `comments: AuditComment[]` to `AuditRunDetail` interface.

**Step 2: Commit**

```bash
git add frontend/src/types/audit.ts
git commit -m "feat: add Tag and AuditComment TypeScript types"
```

---

### Task 7: Frontend — Tag Hooks

**Files:**
- Create: `frontend/src/hooks/use-tags.ts`

**Step 1: Create tag hooks**

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { Tag } from "@/types";

export function useTags() {
  return useQuery({
    queryKey: ["tags"],
    queryFn: async () => {
      const response = await api.get<Tag[]>("/tags/");
      return response.data;
    },
  });
}

export function useCreateTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      const response = await api.post<Tag>("/tags/", { name });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      toast.success("Tag created");
    },
    onError: () => toast.error("Failed to create tag"),
  });
}

export function useDeleteTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/tags/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      queryClient.invalidateQueries({ queryKey: ["audits"] });
      toast.success("Tag deleted");
    },
    onError: () => toast.error("Failed to delete tag"),
  });
}

export function useAddAuditTag(auditId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { tag_id?: number; name?: string }) => {
      const response = await api.post<Tag>(`/audits/${auditId}/tags/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audits", auditId] });
      queryClient.invalidateQueries({ queryKey: ["audits"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
    },
    onError: () => toast.error("Failed to add tag"),
  });
}

export function useRemoveAuditTag(auditId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (tagId: number) => {
      await api.delete(`/audits/${auditId}/tags/${tagId}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audits", auditId] });
      queryClient.invalidateQueries({ queryKey: ["audits"] });
    },
    onError: () => toast.error("Failed to remove tag"),
  });
}
```

**Step 2: Commit**

```bash
git add frontend/src/hooks/use-tags.ts
git commit -m "feat: add tag React Query hooks"
```

---

### Task 8: Frontend — Comment Hooks

**Files:**
- Create: `frontend/src/hooks/use-comments.ts`

**Step 1: Create comment hooks**

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { AuditComment } from "@/types";

export function useAuditComments(auditId: number) {
  return useQuery({
    queryKey: ["audits", auditId, "comments"],
    queryFn: async () => {
      const response = await api.get<AuditComment[]>(`/audits/${auditId}/comments/`);
      return response.data;
    },
    enabled: !!auditId,
  });
}

export function useCreateComment(auditId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (content: string) => {
      const response = await api.post<AuditComment>(`/audits/${auditId}/comments/`, { content });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audits", auditId, "comments"] });
      queryClient.invalidateQueries({ queryKey: ["audits", auditId] });
    },
    onError: () => toast.error("Failed to add comment"),
  });
}

export function useUpdateComment(auditId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ commentId, content }: { commentId: number; content: string }) => {
      const response = await api.put<AuditComment>(`/audits/${auditId}/comments/${commentId}/`, { content });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audits", auditId, "comments"] });
      queryClient.invalidateQueries({ queryKey: ["audits", auditId] });
    },
    onError: () => toast.error("Failed to update comment"),
  });
}

export function useDeleteComment(auditId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (commentId: number) => {
      await api.delete(`/audits/${auditId}/comments/${commentId}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audits", auditId, "comments"] });
      queryClient.invalidateQueries({ queryKey: ["audits", auditId] });
      toast.success("Comment deleted");
    },
    onError: () => toast.error("Failed to delete comment"),
  });
}
```

**Step 2: Commit**

```bash
git add frontend/src/hooks/use-comments.ts
git commit -m "feat: add comment React Query hooks"
```

---

### Task 9: Frontend — TagBadge Component

**Files:**
- Create: `frontend/src/components/tag-badge.tsx`

**Step 1: Create TagBadge component with auto-assigned colors**

```typescript
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

const TAG_COLORS = [
  "bg-blue-500/20 text-blue-300",
  "bg-green-500/20 text-green-300",
  "bg-yellow-500/20 text-yellow-300",
  "bg-red-500/20 text-red-300",
  "bg-purple-500/20 text-purple-300",
  "bg-pink-500/20 text-pink-300",
  "bg-indigo-500/20 text-indigo-300",
  "bg-orange-500/20 text-orange-300",
  "bg-teal-500/20 text-teal-300",
  "bg-cyan-500/20 text-cyan-300",
];

function hashTagName(name: string): number {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = ((hash << 5) - hash + name.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

export function getTagColorClass(name: string): string {
  return TAG_COLORS[hashTagName(name) % TAG_COLORS.length];
}

interface TagBadgeProps {
  name: string;
  onRemove?: () => void;
  className?: string;
}

export function TagBadge({ name, onRemove, className }: TagBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold",
        getTagColorClass(name),
        className
      )}
    >
      {name}
      {onRemove && (
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          className="hover:opacity-70 -mr-1"
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </span>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/tag-badge.tsx
git commit -m "feat: add TagBadge component with auto-assigned colors"
```

---

### Task 10: Frontend — Install react-markdown + Tag Selector Component

**Files:**
- Create: `frontend/src/components/tag-selector.tsx`

**Step 1: Install react-markdown**

Run: `cd frontend && npm install react-markdown`

**Step 2: Create TagSelector combobox component**

This uses the existing Command and Popover UI components from shadcn/ui.

```typescript
import { useState } from "react";
import { Check, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";
import { cn } from "@/lib/utils";
import type { Tag } from "@/types";

interface TagSelectorProps {
  allTags: Tag[];
  selectedTagIds: number[];
  onAddTag: (data: { tag_id?: number; name?: string }) => void;
  isPending?: boolean;
}

export function TagSelector({ allTags, selectedTagIds, onAddTag, isPending }: TagSelectorProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const availableTags = allTags.filter((t) => !selectedTagIds.includes(t.id));
  const exactMatch = allTags.some((t) => t.name.toLowerCase() === search.toLowerCase());

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" disabled={isPending}>
          <Plus className="h-3 w-3 mr-1" />
          Add tag
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-56 p-0" align="start">
        <Command>
          <CommandInput placeholder="Search or create..." value={search} onValueChange={setSearch} />
          <CommandList>
            <CommandEmpty>
              {search.trim() && !exactMatch ? (
                <button
                  className="w-full px-2 py-1.5 text-sm text-left hover:bg-accent"
                  onClick={() => {
                    onAddTag({ name: search.trim() });
                    setSearch("");
                    setOpen(false);
                  }}
                >
                  Create "{search.trim()}"
                </button>
              ) : (
                "No tags found."
              )}
            </CommandEmpty>
            <CommandGroup>
              {availableTags.map((tag) => (
                <CommandItem
                  key={tag.id}
                  value={tag.name}
                  onSelect={() => {
                    onAddTag({ tag_id: tag.id });
                    setOpen(false);
                  }}
                >
                  {tag.name}
                </CommandItem>
              ))}
              {search.trim() && !exactMatch && availableTags.length > 0 && (
                <CommandItem
                  value={`create-${search}`}
                  onSelect={() => {
                    onAddTag({ name: search.trim() });
                    setSearch("");
                    setOpen(false);
                  }}
                >
                  <Plus className="h-3 w-3 mr-1" />
                  Create "{search.trim()}"
                </CommandItem>
              )}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
```

**Step 3: Commit**

```bash
git add frontend/src/components/tag-selector.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat: add TagSelector component and install react-markdown"
```

---

### Task 11: Frontend — Comment Section Component

**Files:**
- Create: `frontend/src/components/comment-section.tsx`

**Step 1: Create CommentSection component**

```typescript
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Pencil, Trash2, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuditComments, useCreateComment, useUpdateComment, useDeleteComment } from "@/hooks/use-comments";
import { useAuth } from "@/hooks/use-auth";

function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

interface CommentSectionProps {
  auditId: number;
}

export function CommentSection({ auditId }: CommentSectionProps) {
  const { user } = useAuth();
  const { data: comments = [] } = useAuditComments(auditId);
  const createComment = useCreateComment(auditId);
  const updateComment = useUpdateComment(auditId);
  const deleteComment = useDeleteComment(auditId);

  const [newContent, setNewContent] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState("");
  const [showPreview, setShowPreview] = useState(false);

  const handleSubmit = async () => {
    if (!newContent.trim()) return;
    await createComment.mutateAsync(newContent);
    setNewContent("");
  };

  const handleUpdate = async (commentId: number) => {
    if (!editContent.trim()) return;
    await updateComment.mutateAsync({ commentId, content: editContent });
    setEditingId(null);
    setEditContent("");
  };

  const startEdit = (commentId: number, content: string) => {
    setEditingId(commentId);
    setEditContent(content);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          Comments ({comments.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Comment list */}
        {comments.map((comment) => (
          <div key={comment.id} className="border border-border rounded-lg p-4 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm">
                <span className="font-semibold">{comment.author_name}</span>
                <span className="text-muted-foreground">{timeAgo(comment.created_at)}</span>
                {comment.created_at !== comment.updated_at && (
                  <span className="text-muted-foreground text-xs">(edited)</span>
                )}
              </div>
              {user && comment.author === user.id && (
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => startEdit(comment.id, comment.content)}
                  >
                    <Pencil className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-destructive"
                    onClick={() => deleteComment.mutate(comment.id)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              )}
            </div>
            {editingId === comment.id ? (
              <div className="space-y-2">
                <Textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  rows={3}
                />
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => handleUpdate(comment.id)} disabled={updateComment.isPending}>
                    Save
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="prose prose-sm prose-invert max-w-none">
                <ReactMarkdown>{comment.content}</ReactMarkdown>
              </div>
            )}
          </div>
        ))}

        {/* New comment form */}
        <div className="border-t border-border pt-4 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">New comment</span>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs"
              onClick={() => setShowPreview(!showPreview)}
            >
              {showPreview ? "Edit" : "Preview"}
            </Button>
          </div>
          {showPreview ? (
            <div className="prose prose-sm prose-invert max-w-none border border-border rounded-md p-3 min-h-[80px]">
              <ReactMarkdown>{newContent || "*Nothing to preview*"}</ReactMarkdown>
            </div>
          ) : (
            <Textarea
              placeholder="Write a comment... (supports markdown)"
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              rows={3}
            />
          )}
          <Button
            size="sm"
            onClick={handleSubmit}
            disabled={!newContent.trim() || createComment.isPending}
          >
            {createComment.isPending ? "Posting..." : "Post comment"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/comment-section.tsx
git commit -m "feat: add CommentSection component with markdown support"
```

---

### Task 12: Frontend — Update Audit Detail Page

**Files:**
- Modify: `frontend/src/pages/audits/detail.tsx`

**Step 1: Add tags and comments sections to the audit detail page**

Add imports:
```typescript
import { TagBadge } from "@/components/tag-badge";
import { TagSelector } from "@/components/tag-selector";
import { CommentSection } from "@/components/comment-section";
import { useTags, useAddAuditTag, useRemoveAuditTag } from "@/hooks/use-tags";
```

Inside `AuditDetailPage`, after `useAuditConfig`, add:
```typescript
  const { data: allTags = [] } = useTags();
  const addTag = useAddAuditTag(Number(id));
  const removeTag = useRemoveAuditTag(Number(id));
```

Add a Tags section after the Details `<Card>` and before the error message section:

```tsx
      {/* Tags */}
      <Card>
        <CardHeader>
          <CardTitle>Tags</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-2">
            {audit.tags?.map((tag) => (
              <TagBadge
                key={tag.id}
                name={tag.name}
                onRemove={() => removeTag.mutate(tag.id)}
              />
            ))}
            <TagSelector
              allTags={allTags}
              selectedTagIds={audit.tags?.map((t) => t.id) ?? []}
              onAddTag={(data) => addTag.mutate(data)}
              isPending={addTag.isPending}
            />
          </div>
        </CardContent>
      </Card>
```

Add `<CommentSection auditId={Number(id)} />` before the Config Snapshot `<Card>`.

**Step 2: Verify the build compiles**

Run: `cd frontend && npx tsc --noEmit`

Expected: No errors.

**Step 3: Commit**

```bash
git add frontend/src/pages/audits/detail.tsx
git commit -m "feat: add tags and comments sections to audit detail page"
```

---

### Task 13: Frontend — Update Settings Page with Tag Management

**Files:**
- Modify: `frontend/src/pages/settings.tsx`

**Step 1: Add tag management card to settings page**

Add imports:
```typescript
import { Plus, X } from "lucide-react";
import { useTags, useCreateTag, useDeleteTag } from "@/hooks/use-tags";
import { TagBadge } from "@/components/tag-badge";
```

Inside `SettingsPage`, add hooks:
```typescript
  const { data: tags = [] } = useTags();
  const createTag = useCreateTag();
  const deleteTag = useDeleteTag();
  const [newTagName, setNewTagName] = useState("");

  const handleAddTag = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTagName.trim()) return;
    await createTag.mutateAsync(newTagName.trim());
    setNewTagName("");
  };
```

Add a new `<Card>` after the existing Site Settings card:

```tsx
      <Card>
        <CardHeader>
          <CardTitle>Tags</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {tags.length === 0 && (
              <p className="text-sm text-muted-foreground">No tags configured yet.</p>
            )}
            {tags.map((tag) => (
              <TagBadge
                key={tag.id}
                name={tag.name}
                onRemove={() => deleteTag.mutate(tag.id)}
              />
            ))}
          </div>
          <form onSubmit={handleAddTag} className="flex gap-2">
            <Input
              placeholder="New tag name"
              value={newTagName}
              onChange={(e) => setNewTagName(e.target.value)}
              className="max-w-xs"
            />
            <Button type="submit" size="sm" disabled={!newTagName.trim() || createTag.isPending}>
              <Plus className="h-4 w-4 mr-1" />
              Add
            </Button>
          </form>
        </CardContent>
      </Card>
```

**Step 2: Verify the build compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 3: Commit**

```bash
git add frontend/src/pages/settings.tsx
git commit -m "feat: add tag management to settings page"
```

---

### Task 14: Frontend — Update Audit List Page with Tags Column and Filter

**Files:**
- Modify: `frontend/src/pages/audits/list.tsx`

**Step 1: Add tags column to audit list table**

Add imports:
```typescript
import { useState } from "react";
import { TagBadge } from "@/components/tag-badge";
import { useTags } from "@/hooks/use-tags";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
```

Add a tags column to the `columns` array (before the `created_at` column):

```typescript
  {
    id: "tags",
    header: "Tags",
    cell: ({ row }) => (
      <div className="flex flex-wrap gap-1">
        {row.original.tags?.map((tag) => (
          <TagBadge key={tag.id} name={tag.name} className="text-[10px] px-1.5 py-0" />
        ))}
      </div>
    ),
  },
```

Update `AuditListPage` to add tag filter state and pass to `useAuditRuns`:

```typescript
export function AuditListPage() {
  const [tagFilter, setTagFilter] = useState<string>("");
  const { data: allTags = [] } = useTags();
  const params: Record<string, string> = {};
  if (tagFilter) params.tags = tagFilter;
  const { data, isLoading } = useAuditRuns(params);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Audits</h1>

      <div className="flex gap-2">
        <Select value={tagFilter} onValueChange={(v) => setTagFilter(v === "all" ? "" : v)}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Filter by tag" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All tags</SelectItem>
            {allTags.map((tag) => (
              <SelectItem key={tag.id} value={String(tag.id)}>
                {tag.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent>
          {isLoading ? (
            <div className="text-center text-muted-foreground py-8">Loading...</div>
          ) : (
            <DataTable columns={columns} data={data?.results ?? []} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

**Step 2: Verify the build compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 3: Commit**

```bash
git add frontend/src/pages/audits/list.tsx
git commit -m "feat: add tags column and tag filter to audit list page"
```

---

### Task 15: Update Existing Tests for New Serializer Fields

**Files:**
- Modify: `backend/audits/tests.py`

**Step 1: Update expected field sets in existing API tests**

In `AuditRunAPITests.test_list_serializer_fields`, update `expected_fields` to include `"tags"`:

```python
        expected_fields = {
            "id", "device", "device_name", "status", "trigger",
            "summary", "started_at", "completed_at", "created_at", "tags",
        }
```

In `AuditRunAPITests.test_retrieve_audit_run_detail_serializer_fields`, update `expected_fields` to include `"tags"` and `"comments"`:

```python
        expected_fields = {
            "id", "device", "device_name", "status", "trigger",
            "summary", "started_at", "completed_at", "created_at",
            "results", "error_message", "config_fetched_at", "tags", "comments",
        }
```

**Step 2: Run full test suite**

Run: `cd backend && python manage.py test audits -v2`

Expected: All tests pass.

**Step 3: Commit**

```bash
git add backend/audits/tests.py
git commit -m "fix: update existing API tests for new tags and comments fields"
```

---

### Task 16: Final Build Verification

**Step 1: Run backend tests**

Run: `cd backend && python manage.py test audits -v2`

Expected: All tests pass.

**Step 2: Run frontend type check**

Run: `cd frontend && npx tsc --noEmit`

Expected: No type errors.

**Step 3: Run frontend build**

Run: `cd frontend && npm run build`

Expected: Build succeeds.

**Step 4: Final commit (if any remaining changes)**

```bash
git add -A
git commit -m "chore: final build verification for tags and comments feature"
```
