import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ArrowLeft, Play, CheckCircle2, XCircle } from "lucide-react";
import Editor, { type OnMount } from "@monaco-editor/react";
import type { editor as monacoEditor } from "monaco-editor";
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
  useValidateCustomRuleContent,
} from "@/hooks/use-rules";
import { useDevices } from "@/hooks/use-devices";
import { useGroups } from "@/hooks/use-groups";
import type { CustomRuleFormData, Severity } from "@/types";

const DEFAULT_CONTENT = `import pytest


def test_example(device_config):
    """Check that the device config contains expected configuration."""
    assert "hostname" in device_config
`;

export function CustomRuleFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = !!id;

  const { data: rule, isLoading: ruleLoading } = useCustomRule(Number(id));
  const { data: devicesData } = useDevices();
  const { data: groupsData } = useGroups();
  const createRule = useCreateCustomRule();
  const updateRule = useUpdateCustomRule(Number(id));
  const validateContent = useValidateCustomRuleContent();

  const [formData, setFormData] = useState<CustomRuleFormData>({
    name: "",
    description: "",
    filename: "",
    content: DEFAULT_CONTENT,
    severity: "medium",
    enabled: true,
    device: null,
    group: null,
  });

  const [validationState, setValidationState] = useState<
    "idle" | "valid" | "invalid"
  >("idle");
  const [validationErrors, setValidationErrors] = useState<
    Array<{ line: number; message: string }>
  >([]);

  const editorRef = useRef<monacoEditor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<typeof import("monaco-editor") | null>(null);

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

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco as unknown as typeof import("monaco-editor");
  };

  function setEditorMarkers(
    errors: Array<{ line: number; message: string }>
  ) {
    if (!editorRef.current || !monacoRef.current) return;
    const model = editorRef.current.getModel();
    if (!model) return;

    const markers: monacoEditor.IMarkerData[] = errors.map((err) => ({
      severity: monacoRef.current!.MarkerSeverity.Error,
      startLineNumber: err.line,
      startColumn: 1,
      endLineNumber: err.line,
      endColumn: model.getLineMaxColumn(err.line),
      message: err.message,
    }));

    monacoRef.current.editor.setModelMarkers(model, "ast-validator", markers);
  }

  function clearEditorMarkers() {
    if (!editorRef.current || !monacoRef.current) return;
    const model = editorRef.current.getModel();
    if (!model) return;
    monacoRef.current.editor.setModelMarkers(model, "ast-validator", []);
  }

  function handleValidate() {
    setValidationState("idle");
    setValidationErrors([]);
    clearEditorMarkers();

    validateContent.mutate(formData.content, {
      onSuccess: (data) => {
        if (data.valid) {
          setValidationState("valid");
          setValidationErrors([]);
          clearEditorMarkers();
        } else {
          setValidationState("invalid");
          setValidationErrors(data.errors);
          setEditorMarkers(data.errors);
        }
      },
      onError: () => {
        setValidationState("invalid");
        setValidationErrors([{ line: 1, message: "Validation request failed" }]);
      },
    });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const mutation = isEdit ? updateRule : createRule;
    mutation.mutate(formData, {
      onSuccess: () => navigate("/rules/custom"),
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
    <div className="p-6 flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex items-center gap-4 mb-4">
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
                <Label htmlFor="filename">Filename</Label>
                <Input
                  id="filename"
                  value={formData.filename}
                  onChange={(e) =>
                    setFormData({ ...formData, filename: e.target.value })
                  }
                  required
                />
                <p className="text-xs text-muted-foreground">
                  Must start with test_ and end with .py
                </p>
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
                  <Link to="/rules/custom">Cancel</Link>
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Right Panel — Editor */}
        <Card className="flex-1 flex flex-col min-h-[500px]">
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-base font-mono">
              {formData.filename || "test_rule.py"}
            </CardTitle>
            <div className="flex items-center gap-2">
              {validationState === "valid" && (
                <span className="flex items-center gap-1 text-sm text-green-500">
                  <CheckCircle2 className="h-4 w-4" />
                  Valid
                </span>
              )}
              {validationState === "invalid" && (
                <span className="flex items-center gap-1 text-sm text-red-500">
                  <XCircle className="h-4 w-4" />
                  {validationErrors.length} error{validationErrors.length !== 1 ? "s" : ""}
                </span>
              )}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleValidate}
                disabled={validateContent.isPending}
              >
                <Play className="mr-1 h-3 w-3" />
                {validateContent.isPending ? "Validating..." : "Validate"}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="flex-1 p-0 overflow-hidden">
            <Editor
              defaultLanguage="python"
              theme="vs-dark"
              value={formData.content}
              onChange={(value) =>
                setFormData({ ...formData, content: value ?? "" })
              }
              onMount={handleEditorDidMount}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: "on",
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 4,
                insertSpaces: true,
                wordWrap: "off",
                padding: { top: 8 },
              }}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
