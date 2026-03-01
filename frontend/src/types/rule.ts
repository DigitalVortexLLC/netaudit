export type RuleType = "must_contain" | "must_not_contain" | "regex_match" | "regex_no_match";
export type Severity = "critical" | "high" | "medium" | "low" | "info";

export interface SimpleRule {
  id: number;
  name: string;
  description: string;
  rule_type: RuleType;
  pattern: string;
  severity: Severity;
  enabled: boolean;
  device: number | null;
  group: number | null;
  created_at: string;
  updated_at: string;
}

export interface CustomRule {
  id: number;
  name: string;
  description: string;
  filename: string;
  content: string;
  severity: Severity;
  enabled: boolean;
  device: number | null;
  group: number | null;
  created_at: string;
  updated_at: string;
}

export interface SimpleRuleFormData {
  name: string;
  description: string;
  rule_type: RuleType;
  pattern: string;
  severity: Severity;
  enabled: boolean;
  device: number | null;
  group: number | null;
}

export interface CustomRuleFormData {
  name: string;
  description: string;
  filename: string;
  content: string;
  severity: Severity;
  enabled: boolean;
  device: number | null;
  group: number | null;
}
