export interface NetmikoDeviceType {
  id: number;
  name: string;
  driver: string;
  default_command: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface NetmikoDeviceTypeFormData {
  name: string;
  driver: string;
  default_command: string;
  description?: string;
}
