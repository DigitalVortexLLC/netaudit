import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ArrowLeft, Play, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
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
import { useDevices, useDevice } from "@/hooks/use-devices";
import { useGroups } from "@/hooks/use-groups";
import type { SimpleRuleFormData, RuleType, Severity } from "@/types";

interface TestResult {
  status: "pass" | "fail";
  matchedLines: number[];
  message: string;
}

function runRuleTest(
  config: string,
  pattern: string,
  ruleType: RuleType
): TestResult {
  const lines = config.split("\n");

  if (ruleType === "must_contain" || ruleType === "must_not_contain") {
    const matchedLines: number[] = [];
    lines.forEach((line, i) => {
      if (line.includes(pattern)) {
        matchedLines.push(i);
      }
    });

    if (ruleType === "must_contain") {
      return matchedLines.length > 0
        ? { status: "pass", matchedLines, message: `${matchedLines.length} line${matchedLines.length !== 1 ? "s" : ""} matched` }
        : { status: "fail", matchedLines: [], message: "Pattern not found \u2014 rule would FAIL" };
    } else {
      return matchedLines.length > 0
        ? { status: "fail", matchedLines, message: `Pattern found on ${matchedLines.length} line${matchedLines.length !== 1 ? "s" : ""} \u2014 rule would FAIL` }
        : { status: "pass", matchedLines: [], message: "Pattern not found \u2014 rule would PASS" };
    }
  }

  // regex types
  let regex: RegExp;
  try {
    regex = new RegExp(pattern);
  } catch {
    return { status: "fail", matchedLines: [], message: "Invalid regex pattern" };
  }

  const matchedLines: number[] = [];
  lines.forEach((line, i) => {
    if (regex.test(line)) {
      matchedLines.push(i);
    }
  });

  if (ruleType === "regex_match") {
    return matchedLines.length > 0
      ? { status: "pass", matchedLines, message: `${matchedLines.length} line${matchedLines.length !== 1 ? "s" : ""} matched` }
      : { status: "fail", matchedLines: [], message: "No regex match \u2014 rule would FAIL" };
  } else {
    // regex_no_match
    return matchedLines.length > 0
      ? { status: "fail", matchedLines, message: `Regex matched ${matchedLines.length} line${matchedLines.length !== 1 ? "s" : ""} \u2014 rule would FAIL` }
      : { status: "pass", matchedLines: [], message: "No regex match \u2014 rule would PASS" };
  }
}

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

  // Test panel state
  const [testDeviceId, setTestDeviceId] = useState<number | null>(null);
  const { isLoading: testDeviceLoading, refetch: refetchTestDevice } = useDevice(testDeviceId ?? 0);
  const [configText, setConfigText] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

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

  // Clear test results when pattern or rule_type changes
  useEffect(() => {
    setTestResult(null);
  }, [formData.pattern, formData.rule_type]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const mutation = isEdit ? updateRule : createRule;
    mutation.mutate(formData, {
      onSuccess: () => navigate("/rules/simple"),
    });
  }

  function handleTest() {
    if (!testDeviceId) return;

    setTestResult(null);
    setFetchError(null);

    if (configText !== null) {
      // Reuse already-fetched config
      const result = runRuleTest(configText, formData.pattern, formData.rule_type);
      setTestResult(result);
      return;
    }

    refetchTestDevice().then(({ data: device }) => {
      const config = device?.last_fetched_config ?? "";
      if (!config) {
        setFetchError("No config available for this device. Fetch config from the device detail page first.");
        return;
      }
      setConfigText(config);
      const result = runRuleTest(config, formData.pattern, formData.rule_type);
      setTestResult(result);
    }).catch((err) => {
      setFetchError(err instanceof Error ? err.message : "Failed to fetch device config");
    });
  }

  // When test device changes, clear cached config and results
  function handleTestDeviceChange(deviceId: number | null) {
    setTestDeviceId(deviceId);
    setConfigText(null);
    setTestResult(null);
    setFetchError(null);
  }

  // Build highlighted config lines
  const configLines = useMemo(() => {
    if (configText === null) return [];
    return configText.split("\n");
  }, [configText]);

  const matchedLineSet = useMemo(() => {
    if (!testResult) return new Set<number>();
    return new Set(testResult.matchedLines);
  }, [testResult]);

  if (isEdit && ruleLoading) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="p-6 flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex items-center gap-4 mb-4">
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

      {/* Split Layout */}
      <div className="flex flex-col lg:flex-row gap-4 flex-1 min-h-0">
        {/* Left Panel — Form */}
        <Card className="lg:w-[380px] lg:shrink-0 overflow-y-auto">
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Rule Settings</CardTitle>
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
                  rows={2}
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

        {/* Right Panel — Test Rule */}
        <Card className="flex-1 flex flex-col min-h-[500px]">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Test Rule</CardTitle>
            <div className="flex items-center gap-2 pt-2">
              <select
                className="flex h-9 flex-1 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={testDeviceId ?? ""}
                onChange={(e) =>
                  handleTestDeviceChange(
                    e.target.value ? Number(e.target.value) : null
                  )
                }
              >
                <option value="">Select a device...</option>
                {devicesData?.results.map((device) => (
                  <option key={device.id} value={device.id}>
                    {device.name}
                  </option>
                ))}
              </select>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleTest}
                disabled={!testDeviceId || !formData.pattern || testDeviceLoading}
              >
                <Play className="mr-1 h-3 w-3" />
                {testDeviceLoading ? "Fetching..." : "Test"}
              </Button>
            </div>
          </CardHeader>

          <CardContent className="flex-1 flex flex-col min-h-0 gap-2">
            {/* Result summary */}
            {testResult && (
              <div
                className={`flex items-center gap-2 text-sm px-3 py-2 rounded-md ${
                  testResult.status === "pass"
                    ? "bg-green-500/10 text-green-500"
                    : "bg-red-500/10 text-red-500"
                }`}
              >
                {testResult.status === "pass" ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 shrink-0" />
                )}
                {testResult.message}
              </div>
            )}

            {fetchError && (
              <div className="flex items-center gap-2 text-sm px-3 py-2 rounded-md bg-yellow-500/10 text-yellow-600">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                {fetchError}
              </div>
            )}

            {/* Config display */}
            {configText !== null ? (
              <div className="flex-1 overflow-auto rounded-md border bg-muted/30 font-mono text-sm">
                <table className="w-full border-collapse">
                  <tbody>
                    {configLines.map((line, i) => {
                      const isMatched = matchedLineSet.has(i);
                      const highlightClass = isMatched
                        ? testResult?.status === "pass"
                          ? "bg-green-500/20"
                          : "bg-red-500/20"
                        : "";
                      return (
                        <tr key={i} className={highlightClass}>
                          <td className="px-3 py-0 text-right text-muted-foreground select-none w-[1%] whitespace-nowrap border-r border-border/50">
                            {i + 1}
                          </td>
                          <td className="px-3 py-0 whitespace-pre">{line}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
                Select a device and click Test to preview rule matches
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
