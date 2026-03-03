import { useState, useEffect } from "react";
import { Plus, Save, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSiteSettings, useUpdateSiteSettings, useTestSlackWebhook } from "@/hooks/use-settings";
import { useTags, useCreateTag, useDeleteTag } from "@/hooks/use-tags";
import { TagBadge } from "@/components/tag-badge";

export function SettingsPage() {
  const { data: settings, isLoading } = useSiteSettings();
  const updateMutation = useUpdateSiteSettings();

  const { data: tags = [] } = useTags();
  const createTag = useCreateTag();
  const deleteTag = useDeleteTag();

  const [defaultApiEndpoint, setDefaultApiEndpoint] = useState("");
  const [slackWebhookUrl, setSlackWebhookUrl] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [newTagName, setNewTagName] = useState("");
  const testSlack = useTestSlackWebhook();

  const handleAddTag = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTagName.trim()) return;
    await createTag.mutateAsync(newTagName.trim());
    setNewTagName("");
  };

  useEffect(() => {
    if (settings) {
      setDefaultApiEndpoint(settings.default_api_endpoint);
      setSlackWebhookUrl(settings.slack_webhook_url);
    }
  }, [settings]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMessage("");
    await updateMutation.mutateAsync({
      default_api_endpoint: defaultApiEndpoint,
      slack_webhook_url: slackWebhookUrl,
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
      <Card>
        <CardHeader>
          <CardTitle>Notifications</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="slack_webhook_url">Slack Webhook URL</Label>
            <div className="flex gap-2">
              <Input
                id="slack_webhook_url"
                type="url"
                placeholder="https://hooks.slack.com/services/..."
                value={slackWebhookUrl}
                onChange={(e) => setSlackWebhookUrl(e.target.value)}
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!slackWebhookUrl.trim() || testSlack.isPending}
                onClick={() => testSlack.mutate(slackWebhookUrl)}
              >
                <Send className="h-4 w-4 mr-1" />
                Test
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              Receive a notification when an audit has failed rules.
              Paste an incoming webhook URL from your Slack workspace.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
