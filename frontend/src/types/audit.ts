export type AuditStatus = "pending" | "fetching_config" | "running_rules" | "completed" | "failed";
export type AuditTrigger = "manual" | "scheduled";
export type RuleOutcome = "passed" | "failed" | "error" | "skipped";

export interface AuditSummary {
  passed: number;
  failed: number;
  error: number;
  skipped?: number;
}

export interface RuleResult {
  id: number;
  audit_run: number;
  simple_rule: number | null;
  custom_rule: number | null;
  test_node_id: string;
  outcome: RuleOutcome;
  message: string;
  duration: number | null;
  severity: string;
  rule_name: string | null;
}

export interface Tag {
  id: number;
  name: string;
  created_at: string;
}

export interface AuditComment {
  id: number;
  audit_run: number;
  author: number | null;
  author_name: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface AuditRun {
  id: number;
  device: number;
  device_name: string;
  status: AuditStatus;
  trigger: AuditTrigger;
  summary: AuditSummary | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  tags: Tag[];
}

export interface AuditRunDetail extends AuditRun {
  results: RuleResult[];
  error_message: string;
  config_fetched_at: string | null;
  comments: AuditComment[];
}

export interface DashboardSummary {
  device_count: number;
  recent_audit_count: number;
  pass_rate: number;
  failed_rule_count_24h: number;
}
