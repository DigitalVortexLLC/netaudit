import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { User, PaginatedResponse } from "@/types";

export function useUsers(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["users", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<User>>("/auth/users/", { params });
      return response.data;
    },
  });
}

export function useUser(id: number) {
  return useQuery({
    queryKey: ["users", id],
    queryFn: async () => {
      const response = await api.get<User>(`/auth/users/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useUpdateUser(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<User>) => {
      const response = await api.patch<User>(`/auth/users/${id}/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      queryClient.invalidateQueries({ queryKey: ["users", id] });
      toast.success("User updated");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useToggleUserActive() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.patch<User>(`/auth/users/${id}/toggle_active/`);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast.success(`User ${data.is_active ? "enabled" : "disabled"}`);
    },
    onError: () => toast.error("Operation failed"),
  });
}
