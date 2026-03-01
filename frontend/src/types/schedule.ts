export interface AuditSchedule {
  id: number;
  device: number;
  name: string;
  cron_expression: string;
  enabled: boolean;
  django_q_schedule_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface AuditScheduleFormData {
  device: number;
  name: string;
  cron_expression: string;
  enabled: boolean;
}
