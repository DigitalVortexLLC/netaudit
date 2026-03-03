import { useState, useEffect } from "react";
import { Plus, Save, Pencil, Trash2, Zap, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useSiteSettings, useUpdateSiteSettings } from "@/hooks/use-settings";
import { useTags, useCreateTag, useDeleteTag } from "@/hooks/use-tags";
import {
  useWebhooks,
  useCreateWebhook,
  useUpdateWebhook,
  useDeleteWebhook,
  useTestWebhook,
} from "@/hooks/use-webhooks";
import { TagBadge } from "@/components/tag-badge";
import { DeleteDialog } from "@/components/delete-dialog";
import type { WebhookProvider, WebhookHeader, WebhookProviderFormData } from "@/types";

function WebhookFormDialog({
  webhook,
  open,
  onOpenChange,
}: {
  webhook?: WebhookProvider;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const createMutation = useCreateWebhook();
  const updateMutation = useUpdateWebhook(webhook?.id ?? 0);
  const isEdit = !!webhook;

  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [triggerMode, setTriggerMode] = useState<"per_audit" | "per_rule">("per_audit");
  const [headers, setHeaders] = useState<WebhookHeader[]>([]);

  useEffect(() => {
    if (webhook) {
      setName(webhook.name);
      setUrl(webhook.url);
      setEnabled(webhook.enabled);
      setTriggerMode(webhook.trigger_mode);
      setHeaders(webhook.headers.map((h) => ({ key: h.key, value: h.value })));
    } else {
      setName("");
      setUrl("");
      setEnabled(true);
      setTriggerMode("per_audit");
      setHeaders([]);
    }
  }, [webhook, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const data: WebhookProviderFormData = {
      name,
      url,
      enabled,
      trigger_mode: triggerMode,
      headers,
    };
    if (isEdit) {
      await updateMutation.mutateAsync(data);
    } else {
      await createMutation.mutateAsync(data);
    }
    onOpenChange(false);
  };

  const addHeader = () => setHeaders([...headers, { key: "", value: "" }]);
  const removeHeader = (index: number) =>
    setHeaders(headers.filter((_, i) => i !== index));
  const updateHeader = (index: number, field: "key" | "value", val: string) =>
    setHeaders(headers.map((h, i) => (i === index ? { ...h, [field]: val } : h)));

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit Webhook" : "Add Webhook"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="webhook-name">Name</Label>
            <Input
              id="webhook-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Remediation API"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="webhook-url">URL</Label>
            <Input
              id="webhook-url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/webhook"
              required
            />
          </div>
          <div className="flex items-center gap-4">
            <div className="space-y-2 flex-1">
              <Label>Trigger Mode</Label>
              <Select value={triggerMode} onValueChange={(v) => setTriggerMode(v as "per_audit" | "per_rule")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="per_audit">Per Audit</SelectItem>
                  <SelectItem value="per_rule">Per Rule</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2 pt-6">
              <Checkbox
                id="webhook-enabled"
                checked={enabled}
                onCheckedChange={(checked) => setEnabled(checked === true)}
              />
              <Label htmlFor="webhook-enabled">Enabled</Label>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Headers</Label>
              <Button type="button" variant="outline" size="sm" onClick={addHeader}>
                <Plus className="h-3 w-3 mr-1" />
                Add Header
              </Button>
            </div>
            {headers.map((header, i) => (
              <div key={i} className="flex gap-2">
                <Input
                  placeholder="Header name"
                  value={header.key}
                  onChange={(e) => updateHeader(i, "key", e.target.value)}
                  className="flex-1"
                />
                <Input
                  placeholder="Header value"
                  value={header.value}
                  onChange={(e) => updateHeader(i, "value", e.target.value)}
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeHeader(i)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
          <Button type="submit" disabled={isPending} className="w-full">
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {isEdit ? "Update" : "Create"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function WebhooksCard() {
  const { data: webhooksData } = useWebhooks();
  const deleteMutation = useDeleteWebhook();
  const testMutation = useTestWebhook();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingWebhook, setEditingWebhook] = useState<WebhookProvider | undefined>();

  const webhooks = webhooksData?.results ?? [];

  const handleEdit = (webhook: WebhookProvider) => {
    setEditingWebhook(webhook);
    setDialogOpen(true);
  };

  const handleAdd = () => {
    setEditingWebhook(undefined);
    setDialogOpen(true);
  };

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Webhooks</CardTitle>
          <Button size="sm" onClick={handleAdd}>
            <Plus className="h-4 w-4" />
            Add Webhook
          </Button>
        </CardHeader>
        <CardContent>
          {webhooks.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No webhooks configured. Add a webhook to receive notifications when audit rules fail.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>URL</TableHead>
                  <TableHead>Trigger</TableHead>
                  <TableHead>Enabled</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {webhooks.map((webhook) => (
                  <TableRow key={webhook.id}>
                    <TableCell className="font-medium">{webhook.name}</TableCell>
                    <TableCell className="max-w-[200px] truncate text-sm text-muted-foreground">
                      {webhook.url}
                    </TableCell>
                    <TableCell className="text-sm">
                      {webhook.trigger_mode === "per_audit" ? "Per Audit" : "Per Rule"}
                    </TableCell>
                    <TableCell>
                      <span
                        className={`inline-block h-2 w-2 rounded-full ${
                          webhook.enabled ? "bg-green-500" : "bg-gray-300"
                        }`}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => testMutation.mutate(webhook.id)}
                          disabled={testMutation.isPending}
                          title="Test webhook"
                        >
                          <Zap className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEdit(webhook)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <DeleteDialog
                          name={webhook.name}
                          onConfirm={() => deleteMutation.mutate(webhook.id)}
                          loading={deleteMutation.isPending}
                        />
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      <WebhookFormDialog
        webhook={editingWebhook}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </>
  );
}

export function SettingsPage() {
  const { data: settings, isLoading } = useSiteSettings();
  const updateMutation = useUpdateSiteSettings();

  const { data: tags = [] } = useTags();
  const createTag = useCreateTag();
  const deleteTag = useDeleteTag();

  const [defaultApiEndpoint, setDefaultApiEndpoint] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [newTagName, setNewTagName] = useState("");

  const handleAddTag = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTagName.trim()) return;
    await createTag.mutateAsync(newTagName.trim());
    setNewTagName("");
  };

  useEffect(() => {
    if (settings) {
      setDefaultApiEndpoint(settings.default_api_endpoint);
    }
  }, [settings]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMessage("");
    await updateMutation.mutateAsync({
      default_api_endpoint: defaultApiEndpoint,
    });
    setSuccessMessage("Settings saved successfully.");
  };

  if (isLoading) {
    return <div className="p-6 text-center text-muted-foreground">Loading...</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Site Settings</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="default_api_endpoint">Default API Endpoint</Label>
              <Input
                id="default_api_endpoint"
                type="url"
                value={defaultApiEndpoint}
                onChange={(e) => setDefaultApiEndpoint(e.target.value)}
              />
              <p className="text-sm text-muted-foreground">
                Base URL for device API endpoints
              </p>
            </div>

            {successMessage && (
              <p className="text-sm text-green-500">{successMessage}</p>
            )}

            {updateMutation.isError && (
              <p className="text-sm text-destructive">
                Failed to save settings. Please try again.
              </p>
            )}

            <Button type="submit" disabled={updateMutation.isPending}>
              <Save className="h-4 w-4" />
              {updateMutation.isPending ? "Saving..." : "Save"}
            </Button>
          </form>
        </CardContent>
      </Card>
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
      <WebhooksCard />
    </div>
  );
}
