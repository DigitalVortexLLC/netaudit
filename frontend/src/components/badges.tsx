import { cn } from "@/lib/utils";
import type { AuditStatus, AuditTrigger, RuleOutcome, Severity } from "@/types";

interface StatusBadgeProps {
  status: AuditStatus;
  className?: string;
}

const statusStyles: Record<AuditStatus, string> = {
  pending: "bg-[#4a148c] text-[#ce93d8]",
  fetching_config: "bg-[#0d47a1] text-[#90caf9]",
  running_rules: "bg-[#0d47a1] text-[#90caf9]",
  completed: "bg-[#1b5e20] text-[#a5d6a7]",
  failed: "bg-[#b71c1c] text-[#ef9a9a]",
};

const statusLabels: Record<AuditStatus, string> = {
  pending: "Pending",
  fetching_config: "Fetching Config",
  running_rules: "Running Rules",
  completed: "Completed",
  failed: "Failed",
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span className={cn(
      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide",
      statusStyles[status],
      className
    )}>
      {statusLabels[status]}
    </span>
  );
}

interface TriggerBadgeProps {
  trigger: AuditTrigger;
  className?: string;
}

const triggerStyles: Record<AuditTrigger, string> = {
  manual: "bg-[#37474f] text-[#b0bec5]",
  scheduled: "bg-[#1a237e] text-[#9fa8da]",
};

export function TriggerBadge({ trigger, className }: TriggerBadgeProps) {
  return (
    <span className={cn(
      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide",
      triggerStyles[trigger],
      className
    )}>
      {trigger}
    </span>
  );
}

interface SeverityBadgeProps {
  severity: Severity;
  className?: string;
}

const severityStyles: Record<Severity, string> = {
  critical: "bg-[#b71c1c] text-[#ef9a9a]",
  high: "bg-[#e65100] text-[#ffcc80]",
  medium: "bg-[#f57f17] text-[#fff9c4]",
  low: "bg-[#1565c0] text-[#90caf9]",
  info: "bg-[#37474f] text-[#b0bec5]",
};

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  return (
    <span className={cn(
      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide",
      severityStyles[severity],
      className
    )}>
      {severity}
    </span>
  );
}

interface OutcomeBadgeProps {
  outcome: RuleOutcome;
  className?: string;
}

const outcomeStyles: Record<RuleOutcome, string> = {
  passed: "bg-[#1b5e20] text-[#a5d6a7]",
  failed: "bg-[#b71c1c] text-[#ef9a9a]",
  error: "bg-[#e65100] text-[#ffcc80]",
  skipped: "bg-[#37474f] text-[#b0bec5]",
};

export function OutcomeBadge({ outcome, className }: OutcomeBadgeProps) {
  return (
    <span className={cn(
      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide",
      outcomeStyles[outcome],
      className
    )}>
      {outcome}
    </span>
  );
}

interface EnabledBadgeProps {
  enabled: boolean;
  className?: string;
}

export function EnabledBadge({ enabled, className }: EnabledBadgeProps) {
  return (
    <span className={cn(
      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide",
      enabled ? "bg-[#1b5e20] text-[#a5d6a7]" : "bg-[#616161] text-[#bdbdbd]",
      className
    )}>
      {enabled ? "Enabled" : "Disabled"}
    </span>
  );
}
