import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Pencil, Wifi } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EnabledBadge } from "@/components/badges";
import { DeleteDialog } from "@/components/delete-dialog";
import { useDevice, useDeleteDevice, useTestConnection } from "@/hooks/use-devices";

export function DeviceDetailPage() {
  const { id } = useParams();
  const deviceId = Number(id);
  const navigate = useNavigate();
  const { data: device, isLoading } = useDevice(deviceId);
  const deleteMutation = useDeleteDevice();
  const testMutation = useTestConnection(deviceId);
  const [testResult, setTestResult] = useState<{ status_code: number; content_length: number } | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  const handleDelete = () => {
    deleteMutation.mutate(deviceId, {
      onSuccess: () => navigate("/devices"),
    });
  };

  const handleTestConnection = () => {
    setTestResult(null);
    setTestError(null);
    testMutation.mutate(undefined, {
      onSuccess: (data) => setTestResult(data),
      onError: (err) => setTestError(err instanceof Error ? err.message : "Connection test failed"),
    });
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="text-center text-muted-foreground py-8">Loading...</div>
      </div>
    );
  }

  if (!device) {
    return (
      <div className="p-6">
        <div className="text-center text-muted-foreground py-8">Device not found.</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/devices">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <h1 className="text-2xl font-bold flex-1">{device.name}</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleTestConnection} disabled={testMutation.isPending}>
            <Wifi className="h-4 w-4" />
            {testMutation.isPending ? "Testing..." : "Test Connection"}
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link to={`/devices/${deviceId}/edit`}>
              <Pencil className="h-4 w-4" />
              Edit
            </Link>
          </Button>
          <DeleteDialog
            name={device.name}
            onConfirm={handleDelete}
            loading={deleteMutation.isPending}
          />
        </div>
      </div>

      {/* Test Connection Result */}
      {testResult && (
        <div className="rounded-md border border-green-800 bg-green-950 p-4 text-green-300">
          Connection successful — Status: {testResult.status_code}, Content Length: {testResult.content_length} bytes
        </div>
      )}
      {testError && (
        <div className="rounded-md border border-red-800 bg-red-950 p-4 text-red-300">
          Connection failed — {testError}
        </div>
      )}

      {/* Device Details Card */}
      <Card>
        <CardHeader>
          <CardTitle>Device Details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Name</dt>
              <dd className="mt-1 text-sm">{device.name}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Hostname</dt>
              <dd className="mt-1 text-sm">{device.hostname}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">API Endpoint</dt>
              <dd className="mt-1 text-sm">{device.api_endpoint || "\u2014"}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Effective Endpoint</dt>
              <dd className="mt-1 text-sm">{device.effective_api_endpoint}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Enabled</dt>
              <dd className="mt-1">
                <EnabledBadge enabled={device.enabled} />
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Created</dt>
              <dd className="mt-1 text-sm">{new Date(device.created_at).toLocaleString()}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Updated</dt>
              <dd className="mt-1 text-sm">{new Date(device.updated_at).toLocaleString()}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {/* Headers Card */}
      {device.headers.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Headers</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Key</TableHead>
                  <TableHead>Value</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {device.headers.map((header, index) => (
                  <TableRow key={header.id ?? index}>
                    <TableCell className="font-mono text-sm">{header.key}</TableCell>
                    <TableCell className="font-mono text-sm">{header.value}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
