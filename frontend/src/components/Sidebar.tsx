"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Filter,
  Database,
  MessageSquare,
  GitCompare,
  Cpu,
  CheckSquare,
  Activity,
} from "lucide-react";
import StatusBadge from "./StatusBadge";

export function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { name: "Sources", href: "/sources", icon: Database },
    { name: "Ask", href: "/ask", icon: MessageSquare },
    { name: "Compare", href: "/compare", icon: GitCompare },
    { name: "Pipeline", href: "/pipeline", icon: Cpu },
  ];

  const plannedItems = [
    { name: "Evaluation", icon: CheckSquare, phase: "Phase 7" },
    { name: "RAG Doctor", icon: Activity, phase: "Phase 8" },
  ];

  return (
    <aside className="w-64 bg-carbon border-r border-graphite flex flex-col min-h-screen select-none">
      {/* Brand Wordmark */}
      <div className="h-16 px-6 flex items-center gap-3 border-b border-graphite">
        <div className="w-9 h-9 rounded-lg bg-electric/15 border border-electric/40 flex items-center justify-center text-electric">
          <Filter className="w-5 h-5" />
        </div>
        <div className="flex flex-col">
          <span className="font-heading font-bold text-xl text-fg tracking-tight">
            Sift
          </span>
          <span className="text-[11px] text-muted -mt-1 font-mono">
            Audited Data Studio
          </span>
        </div>
      </div>

      {/* Main Navigation */}
      <div className="flex-1 px-3 py-6 space-y-6 overflow-y-auto">
        <div className="space-y-1">
          <div className="px-3 pb-2 text-[11px] font-semibold tracking-wider text-muted/70 uppercase">
            Workspace
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              pathname === item.href ||
              (item.href !== "/" && pathname?.startsWith(item.href));

            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-electric/15 text-electric font-semibold border border-electric/30"
                    : "text-muted hover:text-fg hover:bg-slate"
                }`}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </div>

        {/* Planned Phases */}
        <div className="space-y-1 pt-4 border-t border-graphite/60">
          <div className="px-3 pb-2 text-[11px] font-semibold tracking-wider text-muted/70 uppercase">
            Future Capabilities
          </div>
          {plannedItems.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.name}
                className="flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium text-muted/50 cursor-not-allowed"
                title={`${item.name} is planned for ${item.phase}`}
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span>{item.name}</span>
                </div>
                <StatusBadge status="planned" label={item.phase} />
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-graphite text-xs text-muted/70 flex flex-col gap-1 font-mono">
        <div>Trust Invariants Active</div>
        <div className="text-[10px] text-muted/50">Zero Silent Fallbacks</div>
      </div>
    </aside>
  );
}

export default Sidebar;

