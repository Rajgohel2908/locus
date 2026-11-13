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
  Sparkles,
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
      <div className="h-16 px-5 flex items-center gap-3 border-b border-graphite">
        <img src="/locus-icon.svg" className="w-8 h-8 shrink-0" alt="LOCUS" />
        <div className="flex flex-col">
          <span className="inline-flex items-baseline leading-none">
            <span
              style={{ fontFamily: 'var(--font-locus-l, "Niconne", cursive)' }}
              className="text-[26px] font-normal text-white -translate-y-[1px]"
            >
              L
            </span>
            <span
              style={{
                fontFamily: 'var(--font-locus-sans, "Satoshi", sans-serif)',
                fontWeight: 300,
                letterSpacing: "0.22em",
              }}
              className="text-[16px] ml-[2.5px] uppercase text-white/95 font-light"
            >
              OCUS
            </span>
          </span>
          <span className="text-[9px] text-muted -mt-0.5 font-mono tracking-wider">
            TRAIN &bull; EMBED &bull; RETRIEVE
          </span>
        </div>
      </div>

      {/* Main Navigation */}
      <div className="flex-1 px-3 py-6 space-y-6 overflow-y-auto">
        <div className="space-y-1">
          <div className="px-3 pb-2 text-[11px] font-medium tracking-wider text-muted/70 uppercase">
            Product
          </div>
          <Link
            href="/landing"
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all text-[#C8F432] bg-[#C8F432]/10 border border-[#C8F432]/30 hover:bg-[#C8F432]/20"
          >
            <Sparkles className="w-4 h-4 flex-shrink-0 text-[#C8F432]" />
            <span>Product Landing</span>
          </Link>
        </div>

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

