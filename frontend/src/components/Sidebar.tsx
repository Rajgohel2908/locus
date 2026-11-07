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

export function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { name: "Sources & Data", href: "/sources", icon: Database },
    { name: "Chat & Ask", href: "/ask", icon: MessageSquare },
    { name: "Strategy Compare", href: "/compare", icon: GitCompare },
    { name: "Pipeline Architecture", href: "/pipeline", icon: Cpu },
    { name: "Evaluation", href: "/evaluation", icon: CheckSquare },
    { name: "RAG Doctor", href: "/doctor", icon: Activity },
  ];

  return (
    <aside className="w-64 bg-carbon border-r border-graphite flex flex-col min-h-screen select-none">
      {/* Brand Wordmark */}
      <div className="h-16 px-6 flex items-center gap-3 border-b border-graphite">
        <div className="w-8 h-8 rounded-lg bg-electric/15 border border-electric/40 flex items-center justify-center text-electric">
          <Filter className="w-4 h-4" />
        </div>
        <div className="flex flex-col">
          <span className="font-heading font-bold text-lg text-fg tracking-tight">
            Sift
          </span>
          <span className="text-[10px] text-muted -mt-1 font-mono">
            Verifiable Studio
          </span>
        </div>
      </div>

      {/* Main Navigation */}
      <div className="flex-1 px-3 py-6 space-y-6 overflow-y-auto">
        <div className="space-y-1">
          <div className="px-3 pb-2 text-[11px] font-medium tracking-wider text-muted/70 uppercase">
            Studio Navigation
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
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-graphite text-xs text-muted/70 flex flex-col gap-1 font-mono">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald"></span>
          <span>Engine Active</span>
        </div>
        <div className="text-[10px] text-muted/50">Evidence Gate Enforced</div>
      </div>
    </aside>
  );
}

export default Sidebar;

