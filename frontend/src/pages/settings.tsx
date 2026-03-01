import { useState, useEffect } from "react";
import { Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSiteSettings, useUpdateSiteSettings } from "@/hooks/use-settings";

export function SettingsPage() {
  const { data: settings, isLoading } = useSiteSettings();
  const updateMutation = useUpdateSiteSettings();

  const [defaultApiEndpoint, setDefaultApiEndpoint] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

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
    </div>
  );
}
