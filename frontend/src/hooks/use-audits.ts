import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  AuditRun, AuditRunDetail, AuditStatus,
  DashboardSummary, PaginatedResponse, RuleResult,
} from "@/types";

const IN_PROGRESS_STATUSES: AuditStatus[] = ["pending", "fetching_config", "running_rules"];

export function useAuditRuns(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["audits", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<AuditRun>>("/audits/", { params });
      return response.data;
    },
  });
}

export function useAuditRun(id: number) {
  return useQuery({
    queryKey: ["audits", id],
    queryFn: async () => {
      const response = await api.get<AuditRunDetail>(`/audits/${id}/`);
      return response.data;
    },
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && IN_PROGRESS_STATUSES.includes(data.status)) {
        return 3000;
      }
      return false;
    },
  });
}

export function useAuditConfig(id: number) {
  return useQuery({
    queryKey: ["audits", id, "config"],
    queryFn: async () => {
      const response = await api.get(`/audits/${id}/config/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateAudit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (deviceId: number) => {
      const response = await api.post<AuditRun>("/audits/", { device: deviceId });
      return response.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["audits"] }),
  });
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: async () => {
      const response = await api.get<DashboardSummary>("/dashboard/summary/");
      return response.data;
    },
  });
}

export function useCompletedAudits(days: number) {
  return useQuery({
    queryKey: ["audits", "completed", days],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<AuditRun>>("/audits/", {
        params: {
          status: "completed",
          ordering: "-completed_at",
          page_size: "500",
        },
      });
      return response.data;
    },
  });
}

export type IssueRow = RuleResult & { device_name: string; audit_id: number; audit_date: string };

export function useRecentIssues() {
  return useQuery({
    queryKey: ["recent-issues"],
    queryFn: async () => {
      const auditsRes = await api.get<PaginatedResponse<AuditRun>>("/audits/", {
        params: { status: "completed", ordering: "-completed_at", page_size: "5" },
      });
      const details = await Promise.all(
        auditsRes.data.results.map((a) =>
          api.get<AuditRunDetail>(`/audits/${a.id}/`).then((r) => r.data)
        )
      );
      const issues: IssueRow[] = [];
      for (const audit of details) {
        for (const result of audit.results) {
          if (result.outcome === "failed" || result.outcome === "error") {
            issues.push({
              ...result,
              device_name: audit.device_name,
              audit_id: audit.id,
              audit_date: audit.created_at,
            });
          }
        }
      }
      return issues.slice(0, 20);
    },
  });
}
