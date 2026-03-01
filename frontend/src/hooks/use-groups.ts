import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { DeviceGroup, DeviceGroupFormData, PaginatedResponse } from "@/types";

export function useGroups(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["groups", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<DeviceGroup>>("/groups/", { params });
      return response.data;
    },
  });
}

export function useGroup(id: number) {
  return useQuery({
    queryKey: ["groups", id],
    queryFn: async () => {
      const response = await api.get<DeviceGroup>(`/groups/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: DeviceGroupFormData) => {
      const response = await api.post<DeviceGroup>("/groups/", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["groups"] });
      toast.success("Group created");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useUpdateGroup(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: DeviceGroupFormData) => {
      const response = await api.put<DeviceGroup>(`/groups/${id}/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["groups"] });
      queryClient.invalidateQueries({ queryKey: ["groups", id] });
      toast.success("Group updated");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useDeleteGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/groups/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["groups"] });
      toast.success("Group deleted");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useRunGroupAudit(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const response = await api.post(`/groups/${id}/run_audit/`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audits"] });
      toast.success("Group audit started");
    },
    onError: () => toast.error("Operation failed"),
  });
}
