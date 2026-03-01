import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { Device, DeviceFormData, PaginatedResponse, TestConnectionResult } from "@/types";

export function useDevices(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["devices", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<Device>>("/devices/", { params });
      return response.data;
    },
  });
}

export function useDevice(id: number) {
  return useQuery({
    queryKey: ["devices", id],
    queryFn: async () => {
      const response = await api.get<Device>(`/devices/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateDevice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: DeviceFormData) => {
      const response = await api.post<Device>("/devices/", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
      toast.success("Device created");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useUpdateDevice(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: DeviceFormData) => {
      const response = await api.put<Device>(`/devices/${id}/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
      queryClient.invalidateQueries({ queryKey: ["devices", id] });
      toast.success("Device updated");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useDeleteDevice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/devices/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
      toast.success("Device deleted");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useTestConnection(id: number) {
  return useMutation({
    mutationFn: async () => {
      const response = await api.post<TestConnectionResult>(`/devices/${id}/test_connection/`);
      return response.data;
    },
  });
}
