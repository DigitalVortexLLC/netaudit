import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { AuditComment } from "@/types";

export function useAuditComments(auditId: number) {
  return useQuery({
    queryKey: ["audits", auditId, "comments"],
    queryFn: async () => {
      const response = await api.get<AuditComment[]>(`/audits/${auditId}/comments/`);
      return response.data;
    },
    enabled: !!auditId,
  });
}

export function useCreateComment(auditId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (content: string) => {
      const response = await api.post<AuditComment>(`/audits/${auditId}/comments/`, { content });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audits", auditId, "comments"] });
      queryClient.invalidateQueries({ queryKey: ["audits", auditId] });
    },
    onError: () => toast.error("Failed to add comment"),
  });
}

export function useUpdateComment(auditId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ commentId, content }: { commentId: number; content: string }) => {
      const response = await api.put<AuditComment>(`/audits/${auditId}/comments/${commentId}/`, { content });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audits", auditId, "comments"] });
      queryClient.invalidateQueries({ queryKey: ["audits", auditId] });
    },
    onError: () => toast.error("Failed to update comment"),
  });
}

export function useDeleteComment(auditId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (commentId: number) => {
      await api.delete(`/audits/${auditId}/comments/${commentId}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audits", auditId, "comments"] });
      queryClient.invalidateQueries({ queryKey: ["audits", auditId] });
      toast.success("Comment deleted");
    },
    onError: () => toast.error("Failed to delete comment"),
  });
}
