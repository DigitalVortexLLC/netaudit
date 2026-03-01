import { useState, useEffect } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { useGroup, useCreateGroup, useUpdateGroup } from "@/hooks/use-groups";
import { useDevices } from "@/hooks/use-devices";

export function GroupFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = !!id;
  const groupId = Number(id);

  const { data: group, isLoading: groupLoading } = useGroup(isEdit ? groupId : 0);
  const { data: devicesData } = useDevices();
  const createGroup = useCreateGroup();
  const updateGroup = useUpdateGroup(isEdit ? groupId : 0);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedDevices, setSelectedDevices] = useState<number[]>([]);

  useEffect(() => {
    if (isEdit && group) {
      setName(group.name);
      setDescription(group.description);
      setSelectedDevices(group.devices);
    }
  }, [isEdit, group]);

  const handleToggleDevice = (deviceId: number, checked: boolean) => {
    setSelectedDevices((prev) =>
      checked ? [...prev, deviceId] : prev.filter((d) => d !== deviceId)
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const formData = { name, description, devices: selectedDevices };

    if (isEdit) {
      updateGroup.mutate(formData, {
        onSuccess: () => navigate("/groups"),
      });
    } else {
      createGroup.mutate(formData, {
        onSuccess: () => navigate("/groups"),
      });
    }
  };

  const isPending = createGroup.isPending || updateGroup.isPending;

  if (isEdit && groupLoading) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/groups">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <h1 className="text-2xl font-bold">
          {isEdit ? "Edit Group" : "New Group"}
        </h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Group Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Group name"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Devices</CardTitle>
          </CardHeader>
          <CardContent>
            {!devicesData?.results.length ? (
              <p className="text-muted-foreground">No devices available.</p>
            ) : (
              <div className="space-y-3">
                {devicesData.results.map((device) => (
                  <div key={device.id} className="flex items-center gap-3">
                    <Checkbox
                      id={`device-${device.id}`}
                      checked={selectedDevices.includes(device.id)}
                      onCheckedChange={(checked) =>
                        handleToggleDevice(device.id, !!checked)
                      }
                    />
                    <Label htmlFor={`device-${device.id}`} className="font-normal">
                      {device.name}
                      <span className="ml-2 text-muted-foreground text-sm">
                        ({device.hostname})
                      </span>
                    </Label>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="flex items-center gap-4">
          <Button type="submit" disabled={isPending}>
            {isPending
              ? "Saving..."
              : isEdit
                ? "Update Group"
                : "Create Group"}
          </Button>
          <Button variant="outline" asChild>
            <Link to="/groups">Cancel</Link>
          </Button>
        </div>
      </form>
    </div>
  );
}
