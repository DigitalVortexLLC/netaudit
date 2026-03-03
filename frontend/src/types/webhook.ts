export interface WebhookHeader {
  id?: number;
  key: string;
  value: string;
}

export interface WebhookProvider {
  id: number;
  name: string;
  url: string;
  enabled: boolean;
  trigger_mode: "per_audit" | "per_rule";
  headers: WebhookHeader[];
  created_at: string;
  updated_at: string;
}

export interface WebhookProviderFormData {
  name: string;
  url: string;
  enabled: boolean;
  trigger_mode: "per_audit" | "per_rule";
  headers: WebhookHeader[];
}

export interface WebhookTestResult {
  success: boolean;
  status_code?: number;
  error?: string;
}
