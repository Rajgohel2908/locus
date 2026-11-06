"use client";

import React from "react";
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  Flag,
  AlertOctagon,
  Shield,
  Info,
  XCircle,
  MinusCircle,
  HelpCircle,
} from "lucide-react";

export type StatusType =
  // Green
  | "cited"
  | "applied"
  | "active"
  | "fresh"
  | "passed"
  | "completed"
  // Amber
  | "proposed"
  | "pending"
  | "aging"
  | "unverified"
  | "warning"
  | "stale"
  | "unknown"
  | "running"
  // Red
  | "quarantined"
  | "critical"
  | "failed"
  | "llm_error"
  // Blue
  | "insufficient_evidence"
  | "computed"
  | "approved"
  | "planned"
  // Gray
  | "rejected"
  | "excluded"
  | "disabled"
  | string;

interface StatusBadgeProps {
  status: StatusType;
  label?: string;
  className?: string;
}

export function StatusBadge({ status, label, className = "" }: StatusBadgeProps) {
  const norm = (status || "").toLowerCase().trim();

  // Green group: cited, applied, active, fresh, passed, completed
  if (["cited", "applied", "active", "fresh", "passed", "completed"].includes(norm)) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-chip text-xs font-medium font-body bg-emerald/10 text-emerald border border-emerald/30 ${className}`}
      >
        <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
        <span>{label || norm}</span>
      </span>
    );
  }

  // Amber group: proposed, pending, aging, unverified, warning, stale, unknown, running
  if (
    [
      "proposed",
      "pending",
      "aging",
      "unverified",
      "warning",
      "stale",
      "unknown",
      "running",
    ].includes(norm)
  ) {
    const Icon = ["aging", "pending", "running"].includes(norm) ? Clock : AlertTriangle;
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-chip text-xs font-medium font-body bg-amber/10 text-amber border border-amber/30 ${className}`}
      >
        <Icon className="w-3.5 h-3.5 flex-shrink-0" />
        <span>{label || norm}</span>
      </span>
    );
  }

  // Red group: quarantined, critical, failed, llm_error
  if (["quarantined", "critical", "failed", "llm_error"].includes(norm)) {
    const Icon = norm === "quarantined" ? Flag : AlertOctagon;
    const displayText = norm === "llm_error" ? "LLM Error" : (label || norm);
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-chip text-xs font-medium font-body bg-crimson/10 text-crimson border border-crimson/30 ${className}`}
      >
        <Icon className="w-3.5 h-3.5 flex-shrink-0" />
        <span>{displayText}</span>
      </span>
    );
  }

  // Blue group: insufficient_evidence, computed, approved, planned
  if (["insufficient_evidence", "computed", "approved", "planned"].includes(norm)) {
    const Icon = norm === "insufficient_evidence" ? Shield : Info;
    const displayText =
      norm === "insufficient_evidence"
        ? "Not enough evidence"
        : (label || norm);
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-chip text-xs font-medium font-body bg-electric/10 text-electric border border-electric/30 ${className}`}
      >
        <Icon className="w-3.5 h-3.5 flex-shrink-0" />
        <span>{displayText}</span>
      </span>
    );
  }

  // Gray group: rejected, excluded, disabled
  if (["rejected", "excluded", "disabled"].includes(norm)) {
    const Icon = norm === "rejected" ? XCircle : MinusCircle;
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-chip text-xs font-medium font-body bg-carbon text-muted border border-graphite ${className}`}
      >
        <Icon className="w-3.5 h-3.5 flex-shrink-0" />
        <span>{label || norm}</span>
      </span>
    );
  }

  // Fallback
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-chip text-xs font-medium font-body bg-carbon text-muted border border-graphite ${className}`}
    >
      <HelpCircle className="w-3.5 h-3.5 flex-shrink-0" />
      <span>{label || norm || "n/a"}</span>
    </span>
  );
}

export default StatusBadge;

