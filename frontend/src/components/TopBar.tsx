"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api, ModelsHealth } from "@/lib/api";
import { Activity, Menu, Sparkles, ExternalLink } from "lucide-react";

interface TopBarProps {
  onOpenMobileNav?: () => void;
}

export function TopBar({ onOpenMobileNav }: TopBarProps) {
  const [health, setHealth] = useState<ModelsHealth | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<boolean>(false);

  useEffect(() => {
    let mounted = true;

    async function checkHealth() {
      try {
        const data = await api.getHealth();
        if (mounted) {
          setHealth(data);
          setError(false);
          setLoading(false);
        }
      } catch {
        if (mounted) {
          setError(true);
          setLoading(false);
        }
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const isHealthy = !loading && !error && health?.status === "ok";

  return (
    <header className="h-16 border-b border-graphite/80 bg-carbon/80 backdrop-blur-md px-4 sm:px-6 lg:px-8 flex items-center justify-between z-20 sticky top-0">
      {/* Left: Mobile Menu Trigger + Breadcrumb */}
      <div className="flex items-center gap-3">
        {/* Mobile Hamburger Button */}
        <button
          onClick={onOpenMobileNav}
          aria-label="Open Navigation Drawer"
          className="lg:hidden p-2 -ml-2 rounded-xl text-white/70 hover:text-white hover:bg-white/[0.08] transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Mobile Brand Display */}
        <div className="flex lg:hidden items-center gap-2">
          <img src="/locus-icon.svg" className="w-6 h-6" alt="LOCUS" />
          <span className="inline-flex items-baseline leading-none">
            <span
              style={{ fontFamily: 'var(--font-locus-l, "Niconne", cursive)' }}
              className="text-[22px] font-normal text-white -translate-y-[1px]"
            >
              L
            </span>
            <span
              style={{
                fontFamily: 'var(--font-locus-sans, "Satoshi", sans-serif)',
                fontWeight: 300,
                letterSpacing: "0.22em",
              }}
              className="text-[14px] ml-[2px] uppercase text-white/95 font-light"
            >
              OCUS
            </span>
          </span>
        </div>

        {/* Desktop Breadcrumb */}
        <div className="hidden lg:flex items-center gap-2.5 text-xs text-muted font-mono">
          <span className="text-white font-medium">LOCUS Platform</span>
          <span className="text-white/30">/</span>
          <span className="text-white/70">Studio Console</span>
          <span className="text-white/30">/</span>
          <span className="text-[#C8F432]/90">Train • Embed • Retrieve</span>
        </div>
      </div>

      {/* Right: API Health & Landing Link */}
      <div className="flex items-center gap-3">
        {/* Model & API Health Badge */}
        <div className="flex items-center gap-2 px-2.5 sm:px-3 py-1.5 rounded-xl bg-slate border border-graphite text-xs font-mono shadow-sm">
          <Activity className="w-3.5 h-3.5 text-muted" />
          <span className="text-muted hidden sm:inline">Engine:</span>
          {loading ? (
            <span className="flex items-center gap-1.5 text-amber">
              <span className="w-2 h-2 rounded-full bg-amber animate-pulse" />
              <span className="hidden sm:inline">checking</span>
            </span>
          ) : isHealthy ? (
            <span className="flex items-center gap-1.5 text-[#C8F432]">
              <span className="w-2 h-2 rounded-full bg-[#C8F432] shadow-[0_0_8px_#C8F432]" />
              <span className="font-semibold">online</span>
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-crimson">
              <span className="w-2 h-2 rounded-full bg-crimson" />
              <span className="font-semibold">offline</span>
            </span>
          )}

          {health?.models && (
            <div className="hidden md:flex items-center gap-2 pl-2 border-l border-graphite text-[11px] text-muted">
              <span title="Sentence Transformer Embedder" className="text-white/70">
                Emb: <span className="text-[#C8F432] font-semibold">{health.models.embedder ? "✓" : "✗"}</span>
              </span>
              <span title="Cross-Encoder Reranker" className="text-white/70">
                Rerank: <span className="text-[#C8F432] font-semibold">{health.models.cross_encoder ? "✓" : "✗"}</span>
              </span>
              <span title="LLM Client" className="text-white/70">
                LLM: <span className="text-[#C8F432] font-semibold">{health.models.llm ? "✓" : "✗"}</span>
              </span>
            </div>
          )}
        </div>

        {/* Quick Portal Switch */}
        <Link
          href="/landing"
          className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono font-medium text-white/70 hover:text-white bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 hover:border-white/20 transition-all"
        >
          <Sparkles className="w-3.5 h-3.5 text-[#C8F432]" />
          <span>Exit to Landing</span>
        </Link>
      </div>
    </header>
  );
}

export default TopBar;
