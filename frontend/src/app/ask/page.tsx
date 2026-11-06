"use client";

import React, { useState, useEffect } from "react";
import {
  Send,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  Clock,
  Shield,
  Layers,
  FileText,
  X,
  AlertTriangle,
  History,
  Info,
  CheckCircle2,
} from "lucide-react";
import {
  api,
  SourceItem,
  PipelineConfigItem,
  QueryResult,
  QueryTrace,
  CitationItem,
} from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";

export default function AskPage() {
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [configs, setConfigs] = useState<PipelineConfigItem[]>([]);
  const [history, setHistory] = useState<any[]>([]);

  // Form State
  const [question, setQuestion] = useState<string>("");
  const [selectedSourceIds, setSelectedSourceIds] = useState<number[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<number | undefined>(undefined);
  const [selectedStrategy, setSelectedStrategy] = useState<string>("auto");
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false);

  // Filters State
  const [freshnessFilter, setFreshnessFilter] = useState<string>("");
  const [modalityFilter, setModalityFilter] = useState<string>("");
  const [minConfidence, setMinConfidence] = useState<number | "">("");

  // Execution State
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [trace, setTrace] = useState<QueryTrace | null>(null);
  const [showTrace, setShowTrace] = useState<boolean>(false);
  const [activeCitationDrawer, setActiveCitationDrawer] = useState<CitationItem | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    async function loadInitial() {
      try {
        const sList = await api.getSources();
        setSources(sList);
        setSelectedSourceIds(sList.map((s) => s.id));

        const cList = await api.getPipelineConfigs();
        setConfigs(cList);

        const hList = await api.getQueryHistory(15);
        setHistory(hList);
      } catch {}
    }
    loadInitial();
  }, []);

  async function handleQuerySubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;

    try {
      setSubmitting(true);
      setErrorMsg(null);
      setResult(null);
      setTrace(null);
      setShowTrace(false);

      const filters: Record<string, any> = {};
      if (freshnessFilter) filters.freshness = [freshnessFilter];
      if (modalityFilter) filters.modality = [modalityFilter];
      if (minConfidence !== "") filters.min_extraction_confidence = Number(minConfidence);

      // Ensure at least one source is scoped if no pipeline_config_id is selected
      let effectiveSourceIds = selectedSourceIds;
      if (effectiveSourceIds.length === 0 && !selectedConfigId) {
        effectiveSourceIds = sources.map((s) => s.id);
      }

      if (effectiveSourceIds.length === 0 && !selectedConfigId) {
        setErrorMsg("Please select at least one source from the sources scope filter.");
        setSubmitting(false);
        return;
      }

      const res = await api.submitQuery({
        question: question.trim(),
        source_ids: effectiveSourceIds.length > 0 ? effectiveSourceIds : undefined,
        pipeline_config_id: selectedConfigId,
        strategy: selectedStrategy,
        filters: Object.keys(filters).length > 0 ? filters : undefined,
      });

      setResult(res);

      // Refresh query history
      const hList = await api.getQueryHistory(15);
      setHistory(hList);
    } catch (err: any) {
      setErrorMsg(err.message || "Query execution failed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLoadTrace(queryId: number) {
    try {
      if (!trace) {
        const t = await api.getQueryTrace(queryId);
        setTrace(t);
      }
      setShowTrace((prev) => !prev);
    } catch (err: any) {
      alert(err.message);
    }
  }

  return (
    <div className="space-y-8">
      {/* Page Title */}
      <div>
        <h1 className="font-heading font-bold text-3xl text-fg tracking-tight">
          Ask &amp; Verify
        </h1>
        <p className="text-sm text-muted mt-1">
          Evidence-gated query pipeline with router introspection, citations drawer, and trace verification.
        </p>
      </div>

      {/* Query Form Panel */}
      <div className="p-6 rounded-card border border-graphite bg-carbon space-y-5">
        <form onSubmit={handleQuerySubmit} className="space-y-5">
          {/* Main Question Input */}
          <div className="flex gap-3">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. How many annual leaves are employees entitled to? or What is the average salary in Mumbai?"
              required
              className="flex-1 px-4 py-3 rounded-lg bg-obsidian border border-graphite text-sm text-fg placeholder-muted/50 focus:border-electric focus:outline-none"
            />
            <button
              type="submit"
              disabled={submitting || !question.trim()}
              className="px-6 py-3 rounded-lg bg-electric hover:bg-electric/90 text-white font-semibold text-sm transition-colors disabled:opacity-50 flex items-center gap-2 shadow-subtle flex-shrink-0"
            >
              {submitting ? (
                <span>Routing...</span>
              ) : (
                <>
                  <span>Ask</span>
                  <Send className="w-4 h-4" />
                </>
              )}
            </button>
          </div>

          {/* Quick Configuration Selectors */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
            {/* Pipeline Config Selector */}
            <div>
              <label className="block text-xs font-mono text-muted mb-1.5">
                Pipeline Config
              </label>
              <select
                value={selectedConfigId ?? ""}
                onChange={(e) =>
                  setSelectedConfigId(e.target.value ? parseInt(e.target.value) : undefined)
                }
                className="w-full px-3 py-2 rounded-lg bg-obsidian border border-graphite text-xs text-fg focus:border-electric focus:outline-none"
              >
                <option value="">Default (No Config ID)</option>
                {configs.map((c) => (
                  <option key={c.id} value={c.id}>
                    #{c.id} - {c.name} ({c.kind})
                  </option>
                ))}
              </select>
            </div>

            {/* Retrieval Strategy Selector */}
            <div>
              <label className="block text-xs font-mono text-muted mb-1.5">
                Retrieval Strategy
              </label>
              <select
                value={selectedStrategy}
                onChange={(e) => setSelectedStrategy(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-obsidian border border-graphite text-xs text-fg focus:border-electric focus:outline-none font-mono"
              >
                <option value="auto">auto (Rule-Based Router)</option>
                <option value="dense">dense (Vector Only)</option>
                <option value="lexical">lexical (BM25 Only)</option>
                <option value="hybrid">hybrid (Vector + BM25)</option>
                <option value="hybrid_rerank">hybrid_rerank (Hybrid + Cross-Encoder)</option>
              </select>
            </div>

            {/* Source Multi-Select Filter */}
            <div>
              <label className="block text-xs font-mono text-muted mb-1.5">
                Sources Scope ({selectedSourceIds.length} of {sources.length})
              </label>
              <button
                type="button"
                onClick={() => {
                  if (selectedSourceIds.length === sources.length) {
                    setSelectedSourceIds([]);
                  } else {
                    setSelectedSourceIds(sources.map((s) => s.id));
                  }
                }}
                className="w-full px-3 py-2 rounded-lg bg-obsidian border border-graphite text-xs text-muted hover:text-fg text-left font-mono"
              >
                {selectedSourceIds.length === sources.length
                  ? "All sources active"
                  : `${selectedSourceIds.length} source(s) selected`}
              </button>
            </div>
          </div>

          {/* Advanced Collapsible Filters */}
          <div className="pt-2 border-t border-graphite/60">
            <button
              type="button"
              onClick={() => setShowAdvanced((prev) => !prev)}
              className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-fg font-mono transition-colors"
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Advanced Filters</span>
              {showAdvanced ? (
                <ChevronUp className="w-3.5 h-3.5" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" />
              )}
            </button>

            {showAdvanced && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-3 p-4 rounded-lg bg-slate/40 border border-graphite">
                <div>
                  <label className="block text-[11px] font-mono text-muted mb-1">
                    Freshness Filter
                  </label>
                  <select
                    value={freshnessFilter}
                    onChange={(e) => setFreshnessFilter(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-obsidian border border-graphite text-xs text-fg focus:border-electric focus:outline-none"
                  >
                    <option value="">Any Freshness</option>
                    <option value="fresh">Fresh (&le; 90 days)</option>
                    <option value="aging">Aging (91-365 days)</option>
                    <option value="stale">Stale (&gt; 365 days)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-mono text-muted mb-1">
                    Modality Filter
                  </label>
                  <select
                    value={modalityFilter}
                    onChange={(e) => setModalityFilter(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-obsidian border border-graphite text-xs text-fg focus:border-electric focus:outline-none"
                  >
                    <option value="">All Modalities</option>
                    <option value="text">Clean Text / DOCX</option>
                    <option value="ocr">OCR Extracted</option>
                    <option value="web">Web Scraped</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-mono text-muted mb-1">
                    Min Extraction Confidence (%)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={minConfidence}
                    onChange={(e) => setMinConfidence(e.target.value === "" ? "" : Number(e.target.value))}
                    placeholder="e.g. 60"
                    className="w-full px-2.5 py-1.5 rounded bg-obsidian border border-graphite text-xs text-fg focus:border-electric focus:outline-none font-mono"
                  />
                </div>
              </div>
            )}
          </div>
        </form>
      </div>

      {/* Error Message */}
      {errorMsg && (
        <div className="p-4 rounded-card border border-crimson/30 bg-crimson/10 text-crimson text-sm flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Result Card */}
      {result && (
        <div className="rounded-card border border-graphite bg-carbon overflow-hidden space-y-6 p-6">
          {/* Mock LLM Banner */}
          {result.llm?.mock && (
            <div className="p-3 rounded-lg bg-amber/10 border border-amber/30 text-amber text-xs font-mono flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>
                <strong>MOCK LLM:</strong> Running in offline mock mode with scripted validation responses.
              </span>
            </div>
          )}

          {/* Top Result Metadata Strip */}
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-graphite">
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge status={result.status} label={result.status} />

              {/* Answer Type Chip */}
              <span
                className={`px-2.5 py-0.5 rounded-chip text-xs font-mono font-medium border ${
                  result.answer_type === "computed"
                    ? "bg-electric/15 text-electric border-electric/30"
                    : "bg-slate text-fg border-graphite"
                }`}
              >
                {result.answer_type === "computed" ? "Computed SQL Aggregation" : "Generated LLM Answer"}
              </span>

              {/* Route Chip */}
              {result.route && (
                <span className="px-2.5 py-0.5 rounded-chip text-xs font-mono bg-slate text-muted border border-graphite">
                  Route: {result.route.route || "rag"} &bull; {result.config?.strategy || "auto"}
                </span>
              )}
            </div>

            {/* Evidence Gate Badge */}
            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="text-muted">Evidence Gate:</span>
              {result.evidence?.passed ? (
                <span className="text-emerald flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Passed
                </span>
              ) : (
                <span className="text-electric flex items-center gap-1">
                  <Shield className="w-3.5 h-3.5" /> Insufficient Evidence
                </span>
              )}
            </div>
          </div>

          {/* Answer Body */}
          <div className="space-y-3">
            <h3 className="text-xs font-mono uppercase tracking-wider text-muted">
              Answer Output
            </h3>
            {result.answer ? (
              <div className="text-base text-fg leading-relaxed whitespace-pre-wrap font-body">
                {result.answer}
              </div>
            ) : (
              <div className="p-4 rounded-lg bg-obsidian border border-graphite text-sm text-muted italic">
                No answer generated. The evidence gate determined insufficient grounded evidence in the knowledge base.
              </div>
            )}
          </div>

          {/* Citations / Grounding Chunks */}
          {result.citations && result.citations.length > 0 && (
            <div className="space-y-2 pt-2 border-t border-graphite/60">
              <span className="text-xs font-mono uppercase tracking-wider text-muted">
                Citations ({result.citations.length})
              </span>
              <div className="flex flex-wrap gap-2">
                {result.citations.map((c, i) => (
                  <button
                    key={i}
                    onClick={() => setActiveCitationDrawer(c)}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate hover:bg-slate/80 text-xs font-mono text-electric border border-graphite transition-colors"
                  >
                    <span>[{c.chunk_id ?? i + 1}]</span>
                    <span className="text-fg max-w-[140px] truncate">
                      {c.source_name || `Source #${c.source_id}`}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Latency Breakdown */}
          {result.latency_ms && (
            <div className="pt-3 border-t border-graphite/60 flex flex-wrap items-center gap-4 text-xs font-mono text-muted">
              <span>Total Latency: {result.latency_ms.total ?? "n/a"} ms</span>
              {result.latency_ms.dense && <span>Dense: {result.latency_ms.dense} ms</span>}
              {result.latency_ms.lexical && <span>Lexical: {result.latency_ms.lexical} ms</span>}
              {result.latency_ms.rerank && <span>Rerank: {result.latency_ms.rerank} ms</span>}
              {result.latency_ms.generate && <span>Gen: {result.latency_ms.generate} ms</span>}
              {result.latency_ms.route && <span>Route: {result.latency_ms.route} ms</span>}
              {result.latency_ms.execute && <span>Exec: {result.latency_ms.execute} ms</span>}
            </div>
          )}

          {/* Expandable Trace Timeline */}
          <div className="pt-4 border-t border-graphite">
            <button
              onClick={() => handleLoadTrace(result.query_id)}
              className="inline-flex items-center gap-2 text-xs font-mono text-electric hover:underline"
            >
              <Info className="w-4 h-4" />
              <span>{showTrace ? "Hide Trace Timeline" : "Why this answer? (Introspect Trace)"}</span>
              {showTrace ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            {showTrace && trace && (
              <div className="mt-4 p-5 rounded-lg bg-obsidian border border-graphite space-y-4 font-mono text-xs">
                {/* Route Reasons */}
                {trace.route?.reasons && (
                  <div className="space-y-1">
                    <span className="text-muted uppercase text-[11px] block">
                      Router Decision Trail:
                    </span>
                    <ul className="list-disc list-inside space-y-0.5 text-fg">
                      {trace.route.reasons.map((r: string, idx: number) => (
                        <li key={idx}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Candidate Chunks Signals Table */}
                {trace.retrieved_candidates && trace.retrieved_candidates.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-graphite">
                    <span className="text-muted uppercase text-[11px] block">
                      Candidate Retrieval Signals:
                    </span>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left">
                        <thead className="bg-slate text-[10px] text-muted uppercase">
                          <tr>
                            <th className="py-1 px-2">Chunk ID</th>
                            <th className="py-1 px-2">Source</th>
                            <th className="py-1 px-2">Dense Rank/Score</th>
                            <th className="py-1 px-2">Lexical Rank/Score</th>
                            <th className="py-1 px-2">RRF Score</th>
                            <th className="py-1 px-2">Rerank Score</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-graphite/40">
                          {trace.retrieved_candidates.map((cand) => (
                            <tr key={cand.chunk_id}>
                              <td className="py-1.5 px-2 text-electric">#{cand.chunk_id}</td>
                              <td className="py-1.5 px-2 text-fg truncate max-w-[120px]">{cand.source_name}</td>
                              <td className="py-1.5 px-2 text-muted">
                                {cand.dense_rank ? `#${cand.dense_rank} (${cand.dense_score?.toFixed(3)})` : "n/a"}
                              </td>
                              <td className="py-1.5 px-2 text-muted">
                                {cand.lexical_rank ? `#${cand.lexical_rank} (${cand.lexical_score?.toFixed(3)})` : "n/a"}
                              </td>
                              <td className="py-1.5 px-2 text-muted">
                                {cand.rrf_score?.toFixed(4) ?? "n/a"}
                              </td>
                              <td className="py-1.5 px-2 text-muted">
                                {cand.rerank_score?.toFixed(4) ?? "n/a"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Citation Side Drawer Modal */}
      {activeCitationDrawer && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-end p-0">
          <div className="bg-carbon border-l border-graphite h-full max-w-lg w-full p-6 space-y-4 overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-graphite">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-electric" />
                <h3 className="font-heading font-bold text-base text-fg">
                  Citation Inspector
                </h3>
              </div>
              <button
                onClick={() => setActiveCitationDrawer(null)}
                className="p-1 rounded text-muted hover:text-fg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 font-mono text-xs">
              <div>
                <span className="text-muted block text-[11px]">Chunk ID:</span>
                <span className="text-fg font-semibold">#{activeCitationDrawer.chunk_id ?? "computed"}</span>
              </div>
              <div>
                <span className="text-muted block text-[11px]">Origin Source:</span>
                <span className="text-fg">{activeCitationDrawer.source_name || "n/a"}</span>
              </div>
              {activeCitationDrawer.page_number && (
                <div>
                  <span className="text-muted block text-[11px]">Page Number:</span>
                  <span className="text-fg">{activeCitationDrawer.page_number}</span>
                </div>
              )}
              {activeCitationDrawer.score !== undefined && (
                <div>
                  <span className="text-muted block text-[11px]">Retrieval Score:</span>
                  <span className="text-fg">{activeCitationDrawer.score}</span>
                </div>
              )}
            </div>

            <div className="space-y-2 pt-2 border-t border-graphite">
              <span className="text-xs font-mono uppercase text-muted block">
                Evidence Content:
              </span>
              <div className="p-4 rounded-lg bg-obsidian border border-graphite text-xs text-fg leading-relaxed whitespace-pre-wrap font-mono">
                {activeCitationDrawer.snippet || "(No snippet available)"}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Query History */}
      {history.length > 0 && (
        <div className="rounded-card border border-graphite bg-carbon overflow-hidden">
          <div className="px-6 py-4 border-b border-graphite flex items-center gap-2">
            <History className="w-4 h-4 text-electric" />
            <h3 className="font-heading font-semibold text-base text-fg">
              Recent Queries
            </h3>
          </div>
          <div className="divide-y divide-graphite/60">
            {history.map((h) => (
              <div
                key={h.id}
                onClick={async () => {
                  try {
                    const qDetail = await api.getQueryDetail(h.id);
                    setResult(qDetail);
                    setQuestion(qDetail.question || "");
                  } catch {}
                }}
                className="p-4 hover:bg-slate/40 cursor-pointer transition-colors flex items-center justify-between gap-4"
              >
                <div className="space-y-0.5">
                  <span className="text-sm font-medium text-fg block">
                    {h.question}
                  </span>
                  <span className="text-xs font-mono text-muted">
                    Query #{h.id} &bull; {h.created_at ? new Date(h.created_at).toLocaleTimeString() : ""}
                  </span>
                </div>
                <StatusBadge status={h.status} label={h.status} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

