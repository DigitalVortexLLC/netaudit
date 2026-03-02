import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type {
  SimpleRule, SimpleRuleFormData,
  CustomRule, CustomRuleFormData,
  PaginatedResponse,
} from "@/types";

// Simple Rules
export function useSimpleRules(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["simple-rules", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<SimpleRule>>("/rules/simple/", { params });
      return response.data;
    },
  });
}

export function useSimpleRule(id: number) {
  return useQuery({
    queryKey: ["simple-rules", id],
    queryFn: async () => {
      const response = await api.get<SimpleRule>(`/rules/simple/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateSimpleRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: SimpleRuleFormData) => {
      const response = await api.post<SimpleRule>("/rules/simple/", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["simple-rules"] });
      toast.success("Simple rule created");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useUpdateSimpleRule(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: SimpleRuleFormData) => {
      const response = await api.put<SimpleRule>(`/rules/simple/${id}/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["simple-rules"] });
      queryClient.invalidateQueries({ queryKey: ["simple-rules", id] });
      toast.success("Simple rule updated");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useDeleteSimpleRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/rules/simple/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["simple-rules"] });
      toast.success("Simple rule deleted");
    },
    onError: () => toast.error("Operation failed"),
  });
}

// Custom Rules
export function useCustomRules(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["custom-rules", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<CustomRule>>("/rules/custom/", { params });
      return response.data;
    },
  });
}

export function useCustomRule(id: number) {
  return useQuery({
    queryKey: ["custom-rules", id],
    queryFn: async () => {
      const response = await api.get<CustomRule>(`/rules/custom/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateCustomRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CustomRuleFormData) => {
      const response = await api.post<CustomRule>("/rules/custom/", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-rules"] });
      toast.success("Custom rule created");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useUpdateCustomRule(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CustomRuleFormData) => {
      const response = await api.put<CustomRule>(`/rules/custom/${id}/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-rules"] });
      queryClient.invalidateQueries({ queryKey: ["custom-rules", id] });
      toast.success("Custom rule updated");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useDeleteCustomRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/rules/custom/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-rules"] });
      toast.success("Custom rule deleted");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useValidateCustomRule(id: number) {
  return useMutation({
    mutationFn: async () => {
      const response = await api.post(`/rules/custom/${id}/validate/`);
      return response.data;
    },
  });
}

export function useValidateCustomRuleContent() {
  return useMutation({
    mutationFn: async (content: string) => {
      const response = await api.post<{
        valid: boolean;
        errors: Array<{ line: number; message: string }>;
      }>("/rules/custom/validate-content/", { content });
      return response.data;
    },
  });
}
