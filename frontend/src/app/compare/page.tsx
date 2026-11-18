"use client";

import React, { useState, useEffect } from "react";
import {
  GitCompare,
  Search,
  Clock,
  Shield,
  Layers,
  ArrowRight,
  Info,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { api, SourceItem, CompareRetrievalResult } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";

export default function ComparePage() {
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [question, setQuestion] = useState<string>(
    "How many annual leaves are employees entitled to?"
  );
  const [selectedSourceIds, setSelectedSourceIds] = useState<number[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<CompareRetrievalResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    async function loadSources() {
      try {
        const sList = await api.getSources();
        setSources(sList);
        setSelectedSourceIds(sList.map((s) => s.id));
      } catch {}
    }
    loadSources();
  }, []);

  async function handleCompare(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;

    try {
      setLoading(true);
      setErrorMsg(null);
      setResult(null);

      const res = await api.compareRetrieval({
        question: question.trim(),
        source_ids: selectedSourceIds,
      });
      setResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to compare retrieval strategies.");
    } finally {
      setLoading(false);
    }
  }

  const STRATEGIES = ["dense", "lexical", "hybrid", "hybrid_rerank"];

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="font-heading font-bold text-3xl text-fg tracking-tight">
          Retrieval Strategy Comparison
        </h1>
        <p className="text-sm text-muted mt-1">
          Inspect and compare top retrieved chunks, ranking behaviors, and evidence gates side-by-side.
        </p>
      </div>

      {/* Query Form */}
      <div className="p-6 rounded-card border border-graphite bg-carbon space-y-4">
        <form onSubmit={handleCompare} className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Enter comparison question..."
              required
              className="flex-1 px-4 py-3 rounded-lg bg-obsidian border border-graphite text-sm text-fg placeholder-muted/50 focus:border-electric focus:outline-none"
            />
            <button
              type="submit"
              disabled={loading || !question.trim()}
              className="px-6 py-3 rounded-lg bg-electric hover:brightness-110 active:brightness-95 text-black font-bold text-sm transition-all disabled:opacity-50 flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(200,244,50,0.2)] flex-shrink-0 cursor-pointer"
            >
              {loading ? (
                <span>Comparing...</span>
              ) : (
                <>
                  <span>Compare</span>
                  <GitCompare className="w-4 h-4" />
                </>
              )}
            </button>
          </div>

          <div className="flex items-center justify-between text-xs text-muted font-mono">
            <span>Sources active: {selectedSourceIds.length} of {sources.length}</span>
            <span className="italic text-muted/70">
              Qualitative inspection, not an accuracy measurement.
            </span>
          </div>
        </form>
      </div>

      {/* Error */}
      {errorMsg && (
        <div className="p-4 rounded-card border border-crimson/30 bg-crimson/10 text-crimson text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* 4-Column Strategy Grid */}
      {result && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {STRATEGIES.map((strat) => {
              const stratData =
                result.results?.[strat] ||
                ((result as any).strategies && (result as any).strategies[strat]);
              const chunks = stratData?.chunks || [];
              const passedGate = stratData?.evidence?.passed;

              const latencyVal = stratData?.latency_ms;
              const totalLatency =
                typeof latencyVal === "number"
                  ? latencyVal
                  : latencyVal && typeof latencyVal === "object"
                  ? Object.values(latencyVal).reduce(
                      (acc: number, v: any) =>
                        acc + (typeof v === "number" ? v : 0),
                      0
                    )
                  : null;

              return (
                <div
                  key={strat}
                  className="rounded-card border border-graphite bg-carbon flex flex-col overflow-hidden"
                >
                  {/* Column Header */}
                  <div className="p-4 border-b border-graphite bg-slate/40 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-heading font-bold text-sm text-fg uppercase tracking-wide">
                        {strat}
                      </span>
                      <span className="text-[11px] font-mono text-muted">
                        {totalLatency != null ? totalLatency.toFixed(1) : "n/a"} ms
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-muted">Evidence:</span>
                      {passedGate ? (
                        <span className="text-emerald flex items-center gap-1 font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Passed
                        </span>
                      ) : (
                        <span className="text-amber-400 flex items-center gap-1 font-semibold">
                          <Shield className="w-3.5 h-3.5" /> Gate Hold
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Chunks List */}
                  <div className="p-3 space-y-3 flex-1 overflow-y-auto max-h-[600px] divide-y divide-graphite/40">
                    {chunks.length === 0 ? (
                      <div className="p-6 text-center text-xs text-muted italic">
                        No chunks retrieved
                      </div>
                    ) : (
                      chunks.map((c: any, i: number) => (
                        <div key={c.chunk_id} className="pt-2.5 first:pt-0 space-y-1">
                          <div className="flex items-center justify-between text-[11px] font-mono">
                            <span className="text-electric font-semibold">
                              #{i + 1} (Chunk #{c.chunk_id})
                            </span>
                            <span className="text-muted">
                              score: {c.score != null ? c.score.toFixed(3) : "n/a"}
                            </span>
                          </div>

                          <div className="text-[10px] text-muted font-mono truncate">
                            {c.source_name ||
                              c.metadata?.source_name ||
                              c.metadata?.filename ||
                              "Source document"}
                          </div>

                          <p className="text-xs text-fg/90 line-clamp-4 font-mono leading-relaxed bg-obsidian p-2 rounded border border-graphite">
                            {c.snippet || c.content || "(No preview text)"}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Overlap Summary Footer */}
          {result.overlap_summary && (
            <div className="p-5 rounded-card border border-graphite bg-carbon space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-heading font-semibold text-sm text-fg flex items-center gap-2">
                  <Layers className="w-4 h-4 text-electric" />
                  Overlap &amp; Strategy Agreement
                </h3>
                <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-obsidian border border-graphite text-muted">
                  Unique Chunks Across Strategies:{" "}
                  <strong className="text-fg">
                    {result.overlap_summary.unique_chunk_count ??
                      Object.keys(result.overlap_summary.chunk_strategies || {}).length}
                  </strong>
                </span>
              </div>

              {/* Chunk Agreement Chips */}
              {result.overlap_summary.chunk_strategies && (
                <div className="space-y-2">
                  <span className="text-xs font-mono text-muted">
                    Chunk Strategy Presence:
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(result.overlap_summary.chunk_strategies).map(
                      ([cid, strats]) => {
                        const count = strats.length;
                        const isConsensus = count >= 3;
                        return (
                          <div
                            key={cid}
                            className={`px-2.5 py-1 rounded text-xs font-mono border flex items-center gap-1.5 ${
                              isConsensus
                                ? "bg-emerald/10 border-emerald/40 text-emerald"
                                : "bg-obsidian border-graphite text-fg/80"
                            }`}
                          >
                            <span className="font-semibold">Chunk #{cid}</span>
                            <span className="text-[10px] opacity-75">
                              ({strats.join(", ")})
                            </span>
                          </div>
                        );
                      }
                    )}
                  </div>
                </div>
              )}

              {/* Collapsible Raw Inspector */}
              <details className="text-xs font-mono text-muted">
                <summary className="cursor-pointer hover:text-fg transition-colors">
                  View Full Rank Changes Trace (JSON)
                </summary>
                <pre className="mt-2 p-3 rounded bg-obsidian border border-graphite overflow-x-auto text-[11px] leading-relaxed text-muted/80">
                  {JSON.stringify(result.overlap_summary, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

