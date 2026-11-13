"use client";

import React, { useEffect, useState } from "react";
import { api, ModelsHealth } from "@/lib/api";
import { Activity } from "lucide-react";

export function TopBar() {
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
    <header className="h-16 border-b border-graphite bg-carbon/60 backdrop-blur-md px-8 flex items-center justify-between z-10 sticky top-0">
      <div className="flex items-center gap-3 text-xs text-muted font-mono">
        <span className="text-fg font-medium">LOCUS Platform</span>
        <span>/</span>
        <span>Train &bull; Embed &bull; Retrieve</span>
      </div>

      <div className="flex items-center gap-4">
        {/* Model & API Health Dot */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate border border-graphite text-xs font-mono">
          <Activity className="w-3.5 h-3.5 text-muted" />
          <span className="text-muted">API:</span>
          {loading ? (
            <span className="flex items-center gap-1.5 text-amber">
              <span className="w-2 h-2 rounded-full bg-amber animate-pulse" />
              checking
            </span>
          ) : isHealthy ? (
            <span className="flex items-center gap-1.5 text-emerald">
              <span className="w-2 h-2 rounded-full bg-emerald" />
              online
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-crimson">
              <span className="w-2 h-2 rounded-full bg-crimson" />
              offline
            </span>
          )}

          {health?.models && (
            <div className="hidden md:flex items-center gap-2 pl-2 border-l border-graphite text-[11px] text-muted">
              <span title="Sentence Transformer Embedder">
                Emb: {health.models.embedder ? "✓" : "✗"}
              </span>
              <span title="Cross-Encoder Reranker">
                Rerank: {health.models.cross_encoder ? "✓" : "✗"}
              </span>
              <span title="LLM Client">
                LLM: {health.models.llm ? "✓" : "✗"}
              </span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

export default TopBar;

