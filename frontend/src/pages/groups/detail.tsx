import { Link, useParams, useNavigate } from "react-router-dom";
import { Pencil, Trash2, Play, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useGroup, useDeleteGroup, useRunGroupAudit } from "@/hooks/use-groups";
import { useDevices } from "@/hooks/use-devices";

export function GroupDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const groupId = Number(id);
  const { data: group, isLoading } = useGroup(groupId);
  const { data: devicesData } = useDevices();
  const deleteGroup = useDeleteGroup();
  const runAudit = useRunGroupAudit(groupId);

  if (isLoading) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (!group) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Group not found.</p>
      </div>
    );
  }

  const memberDevices = devicesData?.results.filter((d) =>
    group.devices.includes(d.id)
  ) ?? [];

  const handleDelete = () => {
    deleteGroup.mutate(groupId, {
      onSuccess: () => navigate("/groups"),
    });
  };

  const handleRunAudit = () => {
    runAudit.mutate();
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/groups">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <h1 className="text-2xl font-bold flex-1">{group.name}</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to={`/groups/${group.id}/edit`}>
              <Pencil className="h-4 w-4" />
              Edit
            </Link>
          </Button>
          <Button
            variant="default"
            onClick={handleRunAudit}
            disabled={runAudit.isPending}
          >
            <Play className="h-4 w-4" />
            {runAudit.isPending ? "Running..." : "Run Audit"}
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={deleteGroup.isPending}
          >
            <Trash2 className="h-4 w-4" />
            {deleteGroup.isPending ? "Deleting..." : "Delete"}
          </Button>
        </div>
      </div>

      {/* Info Card */}
      <Card>
        <CardHeader>
          <CardTitle>Group Information</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Name</dt>
              <dd className="mt-1">{group.name}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Device Count</dt>
              <dd className="mt-1">{group.device_count}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-sm font-medium text-muted-foreground">Description</dt>
              <dd className="mt-1">{group.description || "\u2014"}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Created</dt>
              <dd className="mt-1">{new Date(group.created_at).toLocaleString()}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Updated</dt>
              <dd className="mt-1">{new Date(group.updated_at).toLocaleString()}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {/* Member Devices Card */}
      <Card>
        <CardHeader>
          <CardTitle>Member Devices</CardTitle>
        </CardHeader>
        <CardContent>
          {memberDevices.length === 0 ? (
            <p className="text-muted-foreground">No devices in this group.</p>
          ) : (
            <ul className="space-y-2">
              {memberDevices.map((device) => (
                <li key={device.id}>
                  <Link
                    to={`/devices/${device.id}`}
                    className="text-primary hover:underline"
                  >
                    {device.name}
                  </Link>
                  <span className="ml-2 text-sm text-muted-foreground">
                    ({device.hostname})
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
