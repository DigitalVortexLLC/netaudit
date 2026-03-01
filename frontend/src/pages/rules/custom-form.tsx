import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  useCustomRule,
  useCreateCustomRule,
  useUpdateCustomRule,
  useValidateCustomRule,
} from "@/hooks/use-rules";
import { useDevices } from "@/hooks/use-devices";
import { useGroups } from "@/hooks/use-groups";
import type { CustomRuleFormData, Severity } from "@/types";

export function CustomRuleFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = !!id;

  const { data: rule, isLoading: ruleLoading } = useCustomRule(Number(id));
  const { data: devicesData } = useDevices();
  const { data: groupsData } = useGroups();
  const createRule = useCreateCustomRule();
  const updateRule = useUpdateCustomRule(Number(id));
  const validateRule = useValidateCustomRule(Number(id));

  const [formData, setFormData] = useState<CustomRuleFormData>({
    name: "",
    description: "",
    filename: "",
    content: "",
    severity: "medium",
    enabled: true,
    device: null,
    group: null,
  });

  const [validateResult, setValidateResult] = useState<string | null>(null);

  useEffect(() => {
    if (rule) {
      setFormData({
        name: rule.name,
        description: rule.description,
        filename: rule.filename,
        content: rule.content,
        severity: rule.severity,
        enabled: rule.enabled,
        device: rule.device,
        group: rule.group,
      });
    }
  }, [rule]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const mutation = isEdit ? updateRule : createRule;
    mutation.mutate(formData, {
      onSuccess: () => navigate("/rules/custom"),
    });
  }

  function handleValidate() {
    setValidateResult(null);
    validateRule.mutate(undefined, {
      onSuccess: () => setValidateResult("Validation passed."),
      onError: (error) =>
        setValidateResult(`Validation failed: ${error.message}`),
    });
  }

  if (isEdit && ruleLoading) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="outline" size="sm" asChild>
          <Link to="/rules/custom">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Link>
        </Button>
        <h1 className="text-2xl font-bold">
          {isEdit ? "Edit Custom Rule" : "New Custom Rule"}
        </h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{isEdit ? "Edit Rule" : "Create Rule"}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="filename">Filename</Label>
              <Input
                id="filename"
                value={formData.filename}
                onChange={(e) =>
                  setFormData({ ...formData, filename: e.target.value })
                }
                required
              />
              <p className="text-sm text-muted-foreground">
                Must start with test_ and end with .py
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="content">Content</Label>
              <Textarea
                id="content"
                className="font-mono"
                rows={15}
                value={formData.content}
                onChange={(e) =>
                  setFormData({ ...formData, content: e.target.value })
                }
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="severity">Severity</Label>
              <select
                id="severity"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={formData.severity}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    severity: e.target.value as Severity,
                  })
                }
              >
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
                <option value="info">Info</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <Checkbox
                id="enabled"
                checked={formData.enabled}
                onCheckedChange={(checked) =>
                  setFormData({ ...formData, enabled: checked === true })
                }
              />
              <Label htmlFor="enabled">Enabled</Label>
            </div>

            <div className="space-y-2">
              <Label htmlFor="device">Device</Label>
              <select
                id="device"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={formData.device ?? ""}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    device: e.target.value ? Number(e.target.value) : null,
                  })
                }
              >
                <option value="">None</option>
                {devicesData?.results.map((device) => (
                  <option key={device.id} value={device.id}>
                    {device.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="group">Group</Label>
              <select
                id="group"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={formData.group ?? ""}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    group: e.target.value ? Number(e.target.value) : null,
                  })
                }
              >
                <option value="">None</option>
                {groupsData?.results.map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex gap-2 pt-4">
              <Button
                type="submit"
                disabled={createRule.isPending || updateRule.isPending}
              >
                {createRule.isPending || updateRule.isPending
                  ? "Saving..."
                  : isEdit
                    ? "Update Rule"
                    : "Create Rule"}
              </Button>
              {isEdit && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleValidate}
                  disabled={validateRule.isPending}
                >
                  {validateRule.isPending ? "Validating..." : "Validate"}
                </Button>
              )}
              <Button variant="outline" type="button" asChild>
                <Link to="/rules/custom">Cancel</Link>
              </Button>
            </div>

            {validateResult && (
              <p
                className={`text-sm ${
                  validateResult.startsWith("Validation passed")
                    ? "text-green-500"
                    : "text-red-500"
                }`}
              >
                {validateResult}
              </p>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
