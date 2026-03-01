export interface DeviceHeader {
  id?: number;
  key: string;
  value: string;
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
