export interface DeviceHeader {
  id?: number;
  key: string;
  value: string;
}

export interface SshConfigSourceData {
  source_type: "ssh";
  netmiko_device_type: number;
  hostname?: string;
  port?: number;
  username: string;
  password?: string;
  ssh_key?: string;
  command_override?: string;
  extra_commands?: string[];
  prompt_overrides?: Record<string, unknown>;
  timeout?: number;
}

export type ConfigSourceData = SshConfigSourceData | null;

export interface ConfigSourceResponse {
  source_type: string;
  netmiko_device_type?: number;
  hostname?: string;
  port?: number;
  username?: string;
  command_override?: string;
  extra_commands?: string[];
  prompt_overrides?: Record<string, unknown>;
  timeout?: number;
}

export interface Device {
  id: number;
  name: string;
  hostname: string;
  api_endpoint: string;
  effective_api_endpoint: string;
  enabled: boolean;
  headers: DeviceHeader[];
  groups: number[];
  config_source: ConfigSourceResponse | null;
  last_fetched_config: string;
  config_fetched_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DeviceGroup {
  id: number;
  name: string;
  description: string;
  devices: number[];
  device_count: number;
  created_at: string;
  updated_at: string;
}

export interface DeviceFormData {
  name: string;
  hostname: string;
  api_endpoint?: string;
  enabled: boolean;
  headers: DeviceHeader[];
  groups: number[];
  config_source?: ConfigSourceData;
}

export interface DeviceGroupFormData {
  name: string;
  description: string;
  devices: number[];
}

export interface TestConnectionResult {
  status_code: number;
  content_length: number;
}
