import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type {
  WebhookProvider,
  WebhookProviderFormData,
  WebhookTestResult,
  PaginatedResponse,
} from "@/types";

export function useWebhooks() {
  return useQuery({
    queryKey: ["webhooks"],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<WebhookProvider>>(
        "/notifications/webhooks/"
      );
      return response.data;
    },
  });
}

export function useWebhook(id: number) {
  return useQuery({
    queryKey: ["webhooks", id],
    queryFn: async () => {
      const response = await api.get<WebhookProvider>(
        `/notifications/webhooks/${id}/`
      );
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateWebhook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: WebhookProviderFormData) => {
      const response = await api.post<WebhookProvider>(
        "/notifications/webhooks/",
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
      toast.success("Webhook created");
    },
    onError: () => toast.error("Failed to create webhook"),
  });
}

export function useUpdateWebhook(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: WebhookProviderFormData) => {
      const response = await api.put<WebhookProvider>(
        `/notifications/webhooks/${id}/`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
      toast.success("Webhook updated");
    },
    onError: () => toast.error("Failed to update webhook"),
  });
}

export function useDeleteWebhook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/notifications/webhooks/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
      toast.success("Webhook deleted");
    },
    onError: () => toast.error("Failed to delete webhook"),
  });
}

export function useTestWebhook() {
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.post<WebhookTestResult>(
        `/notifications/webhooks/${id}/test/`
      );
      return response.data;
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success(`Test successful (status ${data.status_code})`);
      } else {
        toast.error(`Test failed: ${data.error}`);
      }
    },
    onError: () => toast.error("Test request failed"),
  });
}
