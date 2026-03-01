import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { AuditSchedule, AuditScheduleFormData, PaginatedResponse } from "@/types";

export function useSchedules(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["schedules", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<AuditSchedule>>("/schedules/", { params });
      return response.data;
    },
  });
}

export function useSchedule(id: number) {
  return useQuery({
    queryKey: ["schedules", id],
    queryFn: async () => {
      const response = await api.get<AuditSchedule>(`/schedules/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: AuditScheduleFormData) => {
      const response = await api.post<AuditSchedule>("/schedules/", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schedules"] });
      toast.success("Schedule created");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useUpdateSchedule(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: AuditScheduleFormData) => {
      const response = await api.put<AuditSchedule>(`/schedules/${id}/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schedules"] });
      queryClient.invalidateQueries({ queryKey: ["schedules", id] });
      toast.success("Schedule updated");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useDeleteSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/schedules/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schedules"] });
      toast.success("Schedule deleted");
    },
    onError: () => toast.error("Operation failed"),
  });
}
