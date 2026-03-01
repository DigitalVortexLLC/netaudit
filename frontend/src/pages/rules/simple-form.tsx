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
  useSimpleRule,
  useCreateSimpleRule,
  useUpdateSimpleRule,
} from "@/hooks/use-rules";
import { useDevices } from "@/hooks/use-devices";
import { useGroups } from "@/hooks/use-groups";
import type { SimpleRuleFormData, RuleType, Severity } from "@/types";

export function SimpleRuleFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = !!id;

  const { data: rule, isLoading: ruleLoading } = useSimpleRule(Number(id));
  const { data: devicesData } = useDevices();
  const { data: groupsData } = useGroups();
  const createRule = useCreateSimpleRule();
  const updateRule = useUpdateSimpleRule(Number(id));

  const [formData, setFormData] = useState<SimpleRuleFormData>({
    name: "",
    description: "",
    rule_type: "must_contain",
    pattern: "",
    severity: "medium",
    enabled: true,
    device: null,
    group: null,
  });

  useEffect(() => {
    if (rule) {
      setFormData({
        name: rule.name,
        description: rule.description,
        rule_type: rule.rule_type,
        pattern: rule.pattern,
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
      onSuccess: () => navigate("/rules/simple"),
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
          <Link to="/rules/simple">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Link>
        </Button>
        <h1 className="text-2xl font-bold">
          {isEdit ? "Edit Simple Rule" : "New Simple Rule"}
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
              <Label htmlFor="rule_type">Rule Type</Label>
              <select
                id="rule_type"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={formData.rule_type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    rule_type: e.target.value as RuleType,
                  })
                }
              >
                <option value="must_contain">Must Contain</option>
                <option value="must_not_contain">Must Not Contain</option>
                <option value="regex_match">Regex Match</option>
                <option value="regex_no_match">Regex No Match</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="pattern">Pattern</Label>
              <Textarea
                id="pattern"
                value={formData.pattern}
                onChange={(e) =>
                  setFormData({ ...formData, pattern: e.target.value })
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
              <Button variant="outline" type="button" asChild>
                <Link to="/rules/simple">Cancel</Link>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
