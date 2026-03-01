import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { useDevice, useCreateDevice, useUpdateDevice } from "@/hooks/use-devices";
import { useGroups } from "@/hooks/use-groups";

interface HeaderEntry {
  key: string;
  value: string;
}

export function DeviceFormPage() {
  const { id } = useParams();
  const isEditing = !!id;
  const deviceId = Number(id);
  const navigate = useNavigate();

  const { data: device, isLoading: deviceLoading } = useDevice(isEditing ? deviceId : 0);
  const { data: groupsData } = useGroups();
  const createMutation = useCreateDevice();
  const updateMutation = useUpdateDevice(isEditing ? deviceId : 0);

  const [name, setName] = useState("");
  const [hostname, setHostname] = useState("");
  const [apiEndpoint, setApiEndpoint] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [headers, setHeaders] = useState<HeaderEntry[]>([]);
  const [selectedGroups, setSelectedGroups] = useState<number[]>([]);

  useEffect(() => {
    if (isEditing && device) {
      setName(device.name);
      setHostname(device.hostname);
      setApiEndpoint(device.api_endpoint ?? "");
      setEnabled(device.enabled);
      setHeaders(device.headers.map((h) => ({ key: h.key, value: h.value })));
      setSelectedGroups(device.groups);
    }
  }, [isEditing, device]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const formData = {
      name,
      hostname,
      api_endpoint: apiEndpoint || undefined,
      enabled,
      headers: headers.filter((h) => h.key.trim() !== ""),
      groups: selectedGroups,
    };

    const mutation = isEditing ? updateMutation : createMutation;
    mutation.mutate(formData, {
      onSuccess: () => navigate("/devices"),
    });
  };

  const addHeader = () => {
    setHeaders([...headers, { key: "", value: "" }]);
  };

  const removeHeader = (index: number) => {
    setHeaders(headers.filter((_, i) => i !== index));
  };

  const updateHeader = (index: number, field: "key" | "value", val: string) => {
    setHeaders(headers.map((h, i) => (i === index ? { ...h, [field]: val } : h)));
  };

  const toggleGroup = (groupId: number) => {
    setSelectedGroups((prev) =>
      prev.includes(groupId) ? prev.filter((g) => g !== groupId) : [...prev, groupId]
    );
  };

  if (isEditing && deviceLoading) {
    return (
      <div className="p-6">
        <div className="text-center text-muted-foreground py-8">Loading...</div>
      </div>
    );
  }

  const isPending = createMutation.isPending || updateMutation.isPending;
  const groups = groupsData?.results ?? [];

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/devices">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <h1 className="text-2xl font-bold">{isEditing ? "Edit Device" : "New Device"}</h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 max-w-2xl">
        {/* Basic Info */}
        <Card>
          <CardHeader>
            <CardTitle>Device Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="hostname">Hostname</Label>
              <Input
                id="hostname"
                value={hostname}
                onChange={(e) => setHostname(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="api_endpoint">API Endpoint (optional)</Label>
              <Input
                id="api_endpoint"
                value={apiEndpoint}
                onChange={(e) => setApiEndpoint(e.target.value)}
              />
            </div>

            <div className="flex items-center gap-2">
              <Checkbox
                id="enabled"
                checked={enabled}
                onCheckedChange={(checked) => setEnabled(checked === true)}
              />
              <Label htmlFor="enabled">Enabled</Label>
            </div>
          </CardContent>
        </Card>

        {/* Headers */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Headers</CardTitle>
            <Button type="button" variant="outline" size="sm" onClick={addHeader}>
              <Plus className="h-4 w-4" />
              Add Header
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {headers.length === 0 && (
              <p className="text-sm text-muted-foreground">No headers configured.</p>
            )}
            {headers.map((header, index) => (
              <div key={index} className="flex items-center gap-2">
                <Input
                  placeholder="Key"
                  value={header.key}
                  onChange={(e) => updateHeader(index, "key", e.target.value)}
                  className="flex-1"
                />
                <Input
                  placeholder="Value"
                  value={header.value}
                  onChange={(e) => updateHeader(index, "value", e.target.value)}
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={() => removeHeader(index)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Groups */}
        {groups.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Groups</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {groups.map((group) => (
                <div key={group.id} className="flex items-center gap-2">
                  <Checkbox
                    id={`group-${group.id}`}
                    checked={selectedGroups.includes(group.id)}
                    onCheckedChange={() => toggleGroup(group.id)}
                  />
                  <Label htmlFor={`group-${group.id}`}>{group.name}</Label>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Submit */}
        <div className="flex items-center gap-4">
          <Button type="submit" disabled={isPending}>
            {isPending ? "Saving..." : isEditing ? "Update Device" : "Create Device"}
          </Button>
          <Button type="button" variant="outline" asChild>
            <Link to="/devices">Cancel</Link>
          </Button>
        </div>
      </form>
    </div>
  );
}
