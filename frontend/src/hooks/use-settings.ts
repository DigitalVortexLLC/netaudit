import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { SiteSettings } from "@/types";

export function useSiteSettings() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: async () => {
      const response = await api.get<SiteSettings>("/settings/");
      return response.data;
    },
  });
}

export function useUpdateSiteSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: SiteSettings) => {
      const response = await api.patch<SiteSettings>("/settings/", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      toast.success("Settings updated");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useTestSlackWebhook() {
  return useMutation({
    mutationFn: async (webhookUrl: string) => {
      const response = await api.post("/settings/test-slack/", {
        webhook_url: webhookUrl,
      });
      return response.data;
    },
    onSuccess: () => toast.success("Test message sent to Slack"),
    onError: () => toast.error("Failed to send test message"),
  });
}
