import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ArrowLeft, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSchedule, useCreateSchedule, useUpdateSchedule } from "@/hooks/use-schedules";
import { useDevices } from "@/hooks/use-devices";

export function ScheduleFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = !!id;

  const { data: schedule, isLoading: scheduleLoading } = useSchedule(Number(id));
  const { data: devicesData, isLoading: devicesLoading } = useDevices();
  const createMutation = useCreateSchedule();
  const updateMutation = useUpdateSchedule(Number(id));

  const [name, setName] = useState("");
  const [device, setDevice] = useState("");
  const [cronExpression, setCronExpression] = useState("");
  const [enabled, setEnabled] = useState(true);

  useEffect(() => {
    if (schedule) {
      setName(schedule.name);
      setDevice(String(schedule.device));
      setCronExpression(schedule.cron_expression);
      setEnabled(schedule.enabled);
    }
  }, [schedule]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = {
      name,
      device: Number(device),
      cron_expression: cronExpression,
      enabled,
    };

    if (isEdit) {
      await updateMutation.mutateAsync(formData);
    } else {
      await createMutation.mutateAsync(formData);
    }
    navigate("/schedules");
  };

  const isLoading = scheduleLoading || devicesLoading;
  const isSaving = createMutation.isPending || updateMutation.isPending;

  if (isEdit && isLoading) {
    return <div className="p-6 text-center text-muted-foreground">Loading...</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" asChild>
          <Link to="/schedules">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <h1 className="text-2xl font-bold">
          {isEdit ? "Edit Schedule" : "New Schedule"}
        </h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{isEdit ? "Edit Schedule" : "Create Schedule"}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
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
              <Label htmlFor="device">Device</Label>
              <select
                id="device"
                value={device}
                onChange={(e) => setDevice(e.target.value)}
                required
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                <option value="">Select a device</option>
                {devicesData?.results.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="cron_expression">Cron Expression</Label>
              <Input
                id="cron_expression"
                value={cronExpression}
                onChange={(e) => setCronExpression(e.target.value)}
                required
                className="font-mono"
              />
              <p className="text-sm text-muted-foreground">
                Cron format: minute hour day month weekday
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Checkbox
                id="enabled"
                checked={enabled}
                onCheckedChange={(checked) => setEnabled(checked === true)}
              />
              <Label htmlFor="enabled">Enabled</Label>
            </div>

            <Button type="submit" disabled={isSaving}>
              <Save className="h-4 w-4" />
              {isSaving ? "Saving..." : "Save"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
