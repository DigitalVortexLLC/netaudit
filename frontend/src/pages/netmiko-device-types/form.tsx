import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  useNetmikoDeviceType,
  useCreateNetmikoDeviceType,
  useUpdateNetmikoDeviceType,
} from "@/hooks/use-netmiko-device-types";

export function NetmikoDeviceTypeFormPage() {
  const { id } = useParams();
  const isEditing = !!id;
  const deviceTypeId = Number(id);
  const navigate = useNavigate();

  const { data: deviceType, isLoading: deviceTypeLoading } = useNetmikoDeviceType(
    isEditing ? deviceTypeId : 0
  );
  const createMutation = useCreateNetmikoDeviceType();
  const updateMutation = useUpdateNetmikoDeviceType(isEditing ? deviceTypeId : 0);

  const [name, setName] = useState("");
  const [driver, setDriver] = useState("");
  const [defaultCommand, setDefaultCommand] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    if (isEditing && deviceType) {
      setName(deviceType.name);
      setDriver(deviceType.driver);
      setDefaultCommand(deviceType.default_command);
      setDescription(deviceType.description ?? "");
    }
  }, [isEditing, deviceType]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const formData = {
      name,
      driver,
      default_command: defaultCommand,
      description: description || undefined,
    };

    const mutation = isEditing ? updateMutation : createMutation;
    mutation.mutate(formData, {
      onSuccess: () => navigate("/netmiko-device-types"),
    });
  };

  if (isEditing && deviceTypeLoading) {
    return (
      <div className="p-6">
        <div className="text-center text-muted-foreground py-8">Loading...</div>
      </div>
    );
  }

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/netmiko-device-types">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <h1 className="text-2xl font-bold">
          {isEditing ? "Edit Device Type" : "New Device Type"}
        </h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle>Device Type Information</CardTitle>
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
              <Label htmlFor="driver">Driver</Label>
              <Input
                id="driver"
                value={driver}
                onChange={(e) => setDriver(e.target.value)}
                required
              />
              <p className="text-sm text-muted-foreground">
                Common drivers: cisco_ios, cisco_nxos, arista_eos, juniper_junos, hp_procurve, linux
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="default_command">Default Command</Label>
              <Input
                id="default_command"
                value={defaultCommand}
                onChange={(e) => setDefaultCommand(e.target.value)}
                placeholder="show running-config"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        {/* Submit */}
        <div className="flex items-center gap-4">
          <Button type="submit" disabled={isPending}>
            {isPending ? "Saving..." : isEditing ? "Update Device Type" : "Create Device Type"}
          </Button>
          <Button type="button" variant="outline" asChild>
            <Link to="/netmiko-device-types">Cancel</Link>
          </Button>
        </div>
      </form>
    </div>
  );
}
