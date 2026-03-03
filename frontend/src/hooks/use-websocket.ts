import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getAccessToken } from "@/lib/api";
import type { AuditRunDetail, RuleResult } from "@/types";

type MessageHandler = (data: Record<string, unknown>) => void;

function getWsBaseUrl(): string {
  const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
  // Derive WebSocket URL from API URL
  const url = new URL(apiUrl);
  const wsProtocol = url.protocol === "https:" ? "wss:" : "ws:";
  // In dev with Vite proxy, connect to same origin
  if (import.meta.env.DEV) {
    return `${wsProtocol}//${window.location.host}`;
  }
  return `${wsProtocol}//${url.host}`;
}

/**
 * Core WebSocket hook with auto-reconnect.
 *
 * Connects to the given path, appends JWT token as query param,
 * and calls `onMessage` for each incoming message.
 */
export function useWebSocket(path: string, onMessage: MessageHandler) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    const token = getAccessToken();
    if (!token) return;

    const baseUrl = getWsBaseUrl();
    const url = `${baseUrl}/${path}?token=${encodeURIComponent(token)}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessageRef.current(data);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
      // Reconnect after 3 seconds
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [path]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);
}

/**
 * WebSocket hook for the dashboard.
 *
 * Listens to audit status changes and invalidates dashboard-related
 * queries so the UI updates in real time.
 */
export function useDashboardWebSocket() {
  const queryClient = useQueryClient();

  useWebSocket("ws/dashboard/", useCallback((data: Record<string, unknown>) => {
    if (data.type === "audit_status") {
      // Invalidate dashboard summary so stats refresh
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      // Invalidate the audit list so the recent audits table refreshes
      queryClient.invalidateQueries({ queryKey: ["audits"] });
      // Invalidate recent issues on completion
      if (data.status === "completed" || data.status === "failed") {
        queryClient.invalidateQueries({ queryKey: ["recent-issues"] });
      }
    }
  }, [queryClient]));
}

/**
 * WebSocket hook for a specific audit's detail page.
 *
 * Receives status transitions and individual rule results,
 * patching the React Query cache directly for instant updates.
 */
export function useAuditWebSocket(auditId: number) {
  const queryClient = useQueryClient();

  useWebSocket(`ws/audits/${auditId}/`, useCallback((data: Record<string, unknown>) => {
    if (data.type === "audit_status") {
      // Patch the cached audit detail with new status info
      queryClient.setQueryData<AuditRunDetail>(
        ["audits", auditId],
        (old) => {
          if (!old) return old;
          return {
            ...old,
            status: data.status as AuditRunDetail["status"],
            started_at: (data.started_at as string) ?? old.started_at,
            completed_at: (data.completed_at as string) ?? old.completed_at,
            summary: (data.summary as AuditRunDetail["summary"]) ?? old.summary,
            error_message: (data.error_message as string) ?? old.error_message,
          };
        }
      );
    }

    if (data.type === "audit_result") {
      const result = data.result as RuleResult;
      // Append new rule result to the cached audit detail
      queryClient.setQueryData<AuditRunDetail>(
        ["audits", auditId],
        (old) => {
          if (!old) return old;
          // Avoid duplicates
          if (old.results.some((r) => r.id === result.id)) return old;
          return {
            ...old,
            results: [...old.results, result],
          };
        }
      );
    }
  }, [queryClient, auditId]));
}
