import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { Tag } from "@/types";

export function useTags() {
  return useQuery({
    queryKey: ["tags"],
    queryFn: async () => {
      const response = await api.get<Tag[]>("/tags/");
      return response.data;
    },
  });
}

export function useCreateTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      const response = await api.post<Tag>("/tags/", { name });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      toast.success("Tag created");
    },
    onError: () => toast.error("Failed to create tag"),
  });
}

export function useDeleteTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/tags/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      queryClient.invalidateQueries({ queryKey: ["audits"] });
      toast.success("Tag deleted");
    },
    onError: () => toast.error("Failed to delete tag"),
  });
}

export function useAddAuditTag(auditId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { tag_id?: number; name?: string }) => {
      const response = await api.post<Tag>(`/audits/${auditId}/tags/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audits", auditId] });
      queryClient.invalidateQueries({ queryKey: ["audits"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
    },
    onError: () => toast.error("Failed to add tag"),
  });
}

export function useRemoveAuditTag(auditId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (tagId: number) => {
      await api.delete(`/audits/${auditId}/tags/${tagId}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audits", auditId] });
      queryClient.invalidateQueries({ queryKey: ["audits"] });
    },
    onError: () => toast.error("Failed to remove tag"),
  });
}
