import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { NetmikoDeviceType, NetmikoDeviceTypeFormData, PaginatedResponse } from "@/types";

export function useNetmikoDeviceTypes(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["netmiko-device-types", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<NetmikoDeviceType>>("/netmiko-device-types/", { params });
      return response.data;
    },
  });
}

export function useNetmikoDeviceType(id: number) {
  return useQuery({
    queryKey: ["netmiko-device-types", id],
    queryFn: async () => {
      const response = await api.get<NetmikoDeviceType>(`/netmiko-device-types/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateNetmikoDeviceType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: NetmikoDeviceTypeFormData) => {
      const response = await api.post<NetmikoDeviceType>("/netmiko-device-types/", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["netmiko-device-types"] });
      toast.success("Device type created");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useUpdateNetmikoDeviceType(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: NetmikoDeviceTypeFormData) => {
      const response = await api.put<NetmikoDeviceType>(`/netmiko-device-types/${id}/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["netmiko-device-types"] });
      queryClient.invalidateQueries({ queryKey: ["netmiko-device-types", id] });
      toast.success("Device type updated");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useDeleteNetmikoDeviceType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/netmiko-device-types/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["netmiko-device-types"] });
      toast.success("Device type deleted");
    },
    onError: () => toast.error("Operation failed"),
  });
}
