import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { useDevice, useCreateDevice, useUpdateDevice } from "@/hooks/use-devices";
import { useGroups } from "@/hooks/use-groups";
import { useNetmikoDeviceTypes } from "@/hooks/use-netmiko-device-types";
import type { ConfigSourceData } from "@/types";

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

  const { data: deviceTypesData } = useNetmikoDeviceTypes();

  const [name, setName] = useState("");
  const [hostname, setHostname] = useState("");
  const [apiEndpoint, setApiEndpoint] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [headers, setHeaders] = useState<HeaderEntry[]>([]);
  const [selectedGroups, setSelectedGroups] = useState<number[]>([]);

  // Config source state
  const [sourceType, setSourceType] = useState<"none" | "ssh">("none");
  const [sshNetmikoDeviceType, setSshNetmikoDeviceType] = useState<number>(0);
  const [sshHostname, setSshHostname] = useState("");
  const [sshPort, setSshPort] = useState(22);
  const [sshUsername, setSshUsername] = useState("");
  const [sshPassword, setSshPassword] = useState("");
  const [sshKey, setSshKey] = useState("");
  const [sshCommandOverride, setSshCommandOverride] = useState("");
  const [sshPromptOverrides, setSshPromptOverrides] = useState("");
  const [sshTimeout, setSshTimeout] = useState(30);

  useEffect(() => {
    if (isEditing && device) {
      setName(device.name);
      setHostname(device.hostname);
      setApiEndpoint(device.api_endpoint ?? "");
      setEnabled(device.enabled);
      setHeaders(device.headers.map((h) => ({ key: h.key, value: h.value })));
      setSelectedGroups(device.groups);

      if (device.config_source?.source_type === "ssh") {
        setSourceType("ssh");
        setSshNetmikoDeviceType(device.config_source.netmiko_device_type ?? 0);
        setSshHostname(device.config_source.hostname ?? "");
        setSshPort(device.config_source.port ?? 22);
        setSshUsername(device.config_source.username ?? "");
        setSshCommandOverride(device.config_source.command_override ?? "");
        setSshPromptOverrides(
          device.config_source.prompt_overrides
            ? JSON.stringify(device.config_source.prompt_overrides, null, 2)
            : ""
        );
        setSshTimeout(device.config_source.timeout ?? 30);
      }
    }
  }, [isEditing, device]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    let config_source: ConfigSourceData = null;
    if (sourceType === "ssh") {
      config_source = {
        source_type: "ssh",
        netmiko_device_type: sshNetmikoDeviceType,
        hostname: sshHostname || undefined,
        port: sshPort,
        username: sshUsername,
        password: sshPassword || undefined,
        ssh_key: sshKey || undefined,
        command_override: sshCommandOverride || undefined,
        prompt_overrides: sshPromptOverrides ? JSON.parse(sshPromptOverrides) : undefined,
        timeout: sshTimeout,
      };
    }

    const formData = {
      name,
      hostname,
      api_endpoint: apiEndpoint || undefined,
      enabled,
      headers: headers.filter((h) => h.key.trim() !== ""),
      groups: selectedGroups,
      config_source,
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

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Left Column */}
          <div className="space-y-6">
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
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            {/* Configuration Source */}
            <Card>
              <CardHeader>
                <CardTitle>Configuration Source</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-6">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="sourceType"
                      value="none"
                      checked={sourceType === "none"}
                      onChange={() => setSourceType("none")}
                      className="accent-primary"
                    />
                    <span className="text-sm">None</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="sourceType"
                      value="ssh"
                      checked={sourceType === "ssh"}
                      onChange={() => setSourceType("ssh")}
                      className="accent-primary"
                    />
                    <span className="text-sm">SSH</span>
                  </label>
                </div>

                {sourceType === "ssh" && (
                  <div className="space-y-4 pt-2">
                    <div className="space-y-2">
                      <Label htmlFor="ssh_device_type">Netmiko Device Type</Label>
                      <select
                        id="ssh_device_type"
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        value={sshNetmikoDeviceType}
                        onChange={(e) => setSshNetmikoDeviceType(Number(e.target.value))}
                      >
                        <option value={0}>Select a device type...</option>
                        {deviceTypesData?.results.map((dt) => (
                          <option key={dt.id} value={dt.id}>
                            {dt.name} ({dt.driver})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="ssh_hostname">SSH Hostname (optional)</Label>
                      <Input
                        id="ssh_hostname"
                        value={sshHostname}
                        onChange={(e) => setSshHostname(e.target.value)}
                        placeholder="Defaults to device hostname"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="ssh_port">Port</Label>
                      <Input
                        id="ssh_port"
                        type="number"
                        value={sshPort}
                        onChange={(e) => setSshPort(Number(e.target.value))}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="ssh_username">Username</Label>
                      <Input
                        id="ssh_username"
                        value={sshUsername}
                        onChange={(e) => setSshUsername(e.target.value)}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="ssh_password">Password</Label>
                      <Input
                        id="ssh_password"
                        type="password"
                        value={sshPassword}
                        onChange={(e) => setSshPassword(e.target.value)}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="ssh_key">SSH Key</Label>
                      <Textarea
                        id="ssh_key"
                        value={sshKey}
                        onChange={(e) => setSshKey(e.target.value)}
                        rows={4}
                        placeholder="Paste private key here"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="ssh_command_override">Command Override (optional)</Label>
                      <Input
                        id="ssh_command_override"
                        value={sshCommandOverride}
                        onChange={(e) => setSshCommandOverride(e.target.value)}
                        placeholder="Overrides the device type default command"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="ssh_prompt_overrides">Prompt Overrides (optional, JSON)</Label>
                      <Textarea
                        id="ssh_prompt_overrides"
                        value={sshPromptOverrides}
                        onChange={(e) => setSshPromptOverrides(e.target.value)}
                        rows={3}
                        placeholder='{"expect_string": "#"}'
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="ssh_timeout">Timeout (seconds)</Label>
                      <Input
                        id="ssh_timeout"
                        type="number"
                        value={sshTimeout}
                        onChange={(e) => setSshTimeout(Number(e.target.value))}
                      />
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

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
