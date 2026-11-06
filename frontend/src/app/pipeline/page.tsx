"use client";

import React, { useState, useEffect } from "react";
import {
  Cpu,
  Layers,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  FileCode,
  Eye,
  GitBranch,
  Shield,
  Activity,
  ArrowRight,
} from "lucide-react";
import {
  api,
  SourceItem,
  KBProfile,
  RecommendationItem,
  PipelineConfigItem,
  ConfigComparison,
} from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import MermaidRenderer from "@/components/MermaidRenderer";

export default function PipelinePage() {
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [selectedSourceIds, setSelectedSourceIds] = useState<number[]>([]);
  const [selectedGoal, setSelectedGoal] = useState<string>("qa");
  const [analyzing, setAnalyzing] = useState<boolean>(false);

  // Recommendation State
  const [recommendation, setRecommendation] = useState<RecommendationItem | null>(null);
  const [showNotFired, setShowNotFired] = useState<boolean>(false);
  const [buildIndexChecked, setBuildIndexChecked] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  // Pipeline Configs State
  const [configs, setConfigs] = useState<PipelineConfigItem[]>([]);
  const [comparison, setComparison] = useState<ConfigComparison | null>(null);

  // Graph State
  const [selectedConfigForGraph, setSelectedConfigForGraph] = useState<number | null>(null);
  const [graphFormat, setGraphFormat] = useState<"mermaid" | "json">("mermaid");
  const [mermaidText, setMermaidText] = useState<string>("");
  const [jsonGraphData, setJsonGraphData] = useState<any>(null);

  useEffect(() => {
    async function loadInitial() {
      try {
        const sList = await api.getSources();
        setSources(sList);
        setSelectedSourceIds(sList.map((s) => s.id));

        const cList = await api.getPipelineConfigs();
        setConfigs(cList);

        // Load existing recommendations if any
        const recList = await api.getRecommendations();
        if (recList.length > 0) {
          const latest = recList[0];
          setRecommendation(latest);
        }

        // Compare first baseline and recommended if available
        const base = cList.find((c) => c.kind === "baseline");
        const rec = cList.find((c) => c.kind === "recommended");
        if (base && rec) {
          loadComparison(base.id, rec.id);
          loadGraph(rec.id);
        } else if (cList.length > 0) {
          loadGraph(cList[0].id);
        }
      } catch {}
    }
    loadInitial();
  }, []);

  async function handleAnalyze(e: React.FormEvent) {
    e.preventDefault();
    if (selectedSourceIds.length === 0) {
      alert("Please select at least one source.");
      return;
    }

    try {
      setAnalyzing(true);
      const rec = await api.createRecommendation(selectedSourceIds, selectedGoal);
      setRecommendation(rec);

      // Refresh configs list
      const cList = await api.getPipelineConfigs();
      setConfigs(cList);
    } catch (err: any) {
      alert(err.message || "Failed to generate recommendation.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleApprove() {
    if (!recommendation) return;
    try {
      setActionLoading(true);
      const updated = await api.approveRecommendation(recommendation.id);
      setRecommendation(updated);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleReject() {
    if (!recommendation) return;
    try {
      setActionLoading(true);
      const updated = await api.rejectRecommendation(recommendation.id);
      setRecommendation(updated);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleApply() {
    if (!recommendation) return;
    try {
      setActionLoading(true);
      const res = await api.applyRecommendation(recommendation.id, buildIndexChecked);
      const updated = await api.getRecommendation(recommendation.id);
      setRecommendation(updated);

      const cList = await api.getPipelineConfigs();
      setConfigs(cList);

      if (res.baseline_config && res.recommended_config) {
        await loadComparison(res.baseline_config.id, res.recommended_config.id);
        await loadGraph(res.recommended_config.id);
      }
      alert("Applied recommendation and generated dual pipeline configurations!");
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  async function loadComparison(baseId: number, recId: number) {
    try {
      const comp = await api.comparePipelineConfigs(baseId, recId);
      setComparison(comp);
    } catch {}
  }

  async function loadGraph(configId: number) {
    setSelectedConfigForGraph(configId);
    try {
      const mText = await api.getPipelineGraphMermaid(configId);
      setMermaidText(mText);

      const jData = await api.getPipelineGraphJson(configId);
      setJsonGraphData(jData);
    } catch {}
  }

  const p = recommendation?.data_profile;

  return (
    <div className="space-y-8">
      {/* Title */}
      <div>
        <h1 className="font-heading font-bold text-3xl text-fg tracking-tight">
          Strategy Recommender &amp; Architecture
        </h1>
        <p className="text-sm text-muted mt-1">
          Evaluate corpus profiles against heuristic priors, approve configurations, and inspect visual pipeline graphs.
        </p>
        <span className="inline-block mt-2 text-xs font-mono text-muted/70 italic">
          Rule-based priors, not validated; evaluation comes in Phase 7.
        </span>
      </div>

      {/* Recommender Form Panel */}
      <div className="p-6 rounded-card border border-graphite bg-carbon space-y-5">
        <form onSubmit={handleAnalyze} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Goal Selector */}
            <div>
              <label className="block text-xs font-mono text-muted mb-1.5">
                Optimization Goal
              </label>
              <select
                value={selectedGoal}
                onChange={(e) => setSelectedGoal(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-obsidian border border-graphite text-xs text-fg focus:border-electric focus:outline-none"
              >
                <option value="qa">qa (Exact extraction &amp; low hallucination)</option>
                <option value="search">search (Broad retrieval recall)</option>
                <option value="comparison">comparison (Multi-source comparison)</option>
                <option value="analysis">analysis (Structured quantitative queries)</option>
              </select>
            </div>

            {/* Scope of Sources */}
            <div>
              <label className="block text-xs font-mono text-muted mb-1.5">
                Target Sources ({selectedSourceIds.length} of {sources.length})
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

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={analyzing || selectedSourceIds.length === 0}
              className="px-6 py-2.5 rounded-lg bg-electric hover:bg-electric/90 text-white font-semibold text-xs transition-colors disabled:opacity-50 flex items-center gap-2 shadow-subtle"
            >
              <Sparkles className="w-4 h-4" />
              <span>{analyzing ? "Evaluating Priors..." : "Analyze & Recommend"}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Recommendation Results */}
      {recommendation && (
        <div className="space-y-6">
          {/* Status & Lifecycle Actions */}
          <div className="p-5 rounded-card border border-graphite bg-carbon flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-muted">
                Recommendation #{recommendation.id}
              </span>
              <StatusBadge status={recommendation.status} label={recommendation.status} />
              <span className="text-xs font-mono text-muted">
                Goal: <strong className="text-fg">{recommendation.goal}</strong>
              </span>
            </div>

            <div className="flex items-center gap-3">
              {recommendation.status === "proposed" && (
                <>
                  <button
                    onClick={handleApprove}
                    disabled={actionLoading}
                    className="px-4 py-1.5 rounded-lg bg-emerald/15 hover:bg-emerald/25 text-emerald border border-emerald/30 text-xs font-medium"
                  >
                    Approve
                  </button>
                  <button
                    onClick={handleReject}
                    disabled={actionLoading}
                    className="px-4 py-1.5 rounded-lg bg-carbon hover:bg-slate text-muted border border-graphite text-xs font-medium"
                  >
                    Reject
                  </button>
                </>
              )}

              {recommendation.status === "approved" && (
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-2 text-xs font-mono text-muted">
                    <input
                      type="checkbox"
                      checked={buildIndexChecked}
                      onChange={(e) => setBuildIndexChecked(e.target.checked)}
                      className="rounded bg-obsidian border-graphite text-electric focus:ring-0"
                    />
                    <span>Re-index KB</span>
                  </label>
                  <button
                    onClick={handleApply}
                    disabled={actionLoading}
                    className="px-5 py-2 rounded-lg bg-electric hover:bg-electric/90 text-white text-xs font-semibold shadow-subtle"
                  >
                    Apply Recommendation
                  </button>
                </div>
              )}

              {recommendation.status === "applied" && (
                <span className="text-xs font-mono text-emerald flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" /> Configs Active
                </span>
              )}
            </div>
          </div>

          {/* Warnings Banner */}
          {recommendation.warnings && recommendation.warnings.length > 0 && (
            <div className="p-4 rounded-card border border-amber/30 bg-amber/10 space-y-1">
              <div className="flex items-center gap-2 text-xs font-mono font-semibold text-amber">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>Advisory Warnings</span>
              </div>
              <ul className="list-disc list-inside text-xs text-fg/90 space-y-0.5 font-body">
                {recommendation.warnings.map((w, idx) => (
                  <li key={idx}>{typeof w === "string" ? w : JSON.stringify(w)}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Knowledge Base Profile Cards */}
          {p && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-4 rounded-card border border-graphite bg-carbon">
                <span className="text-[11px] font-mono uppercase text-muted">Documents &amp; Chunks</span>
                <div className="mt-1 font-heading font-bold text-lg text-fg">
                  {p.documents.total} docs / {p.documents.total_chunks} chunks
                </div>
                <span className="text-xs text-muted font-mono">{p.documents.avg_words_per_doc.toFixed(0)} words/doc</span>
              </div>

              <div className="p-4 rounded-card border border-graphite bg-carbon">
                <span className="text-[11px] font-mono uppercase text-muted">Structured Rows</span>
                <div className="mt-1 font-heading font-bold text-lg text-fg">
                  {p.structured.active_row_count} active
                </div>
                <span className="text-xs text-muted font-mono">{p.structured.numeric_columns_count} numeric cols</span>
              </div>

              <div className="p-4 rounded-card border border-graphite bg-carbon">
                <span className="text-[11px] font-mono uppercase text-muted">Freshness Share</span>
                <div className="mt-1 font-heading font-bold text-lg text-fg">
                  {(p.text.stale_share * 100).toFixed(0)}% stale
                </div>
                <span className="text-xs text-muted font-mono">{(p.text.undated_share * 100).toFixed(0)}% undated</span>
              </div>

              <div className="p-4 rounded-card border border-graphite bg-carbon">
                <span className="text-[11px] font-mono uppercase text-muted">Script Distribution</span>
                <div className="mt-1 font-heading font-bold text-lg text-fg capitalize">
                  {p.scripts.dominant_script}
                </div>
                <span className="text-xs text-muted font-mono">{(p.scripts.latin_share * 100).toFixed(1)}% Latin</span>
              </div>
            </div>
          )}

          {/* Rules Fired (with real numbers) */}
          <div className="rounded-card border border-graphite bg-carbon p-6 space-y-4">
            <h3 className="font-heading font-semibold text-base text-fg">
              Recommender Rules Fired ({recommendation.rules_fired.length})
            </h3>
            <div className="space-y-2">
              {recommendation.rules_fired.map((rf) => (
                <div
                  key={rf.id}
                  className="p-3.5 rounded-lg bg-slate/40 border border-graphite flex items-start gap-3"
                >
                  <span className="px-2 py-0.5 rounded bg-emerald/15 text-emerald font-mono font-bold text-xs border border-emerald/30 flex-shrink-0">
                    {rf.id}
                  </span>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-heading font-semibold text-xs text-fg">
                        {rf.name}
                      </span>
                      <span className="text-xs font-mono text-electric">
                        &rarr; {rf.effect}
                      </span>
                    </div>
                    <p className="text-xs text-muted leading-relaxed font-mono">
                      {rf.reason}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Collapsible Rules Not Fired */}
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setShowNotFired((prev) => !prev)}
                className="inline-flex items-center gap-1.5 text-xs font-mono text-muted hover:text-fg"
              >
                <span>Rules Not Fired ({recommendation.rules_not_fired.length})</span>
                {showNotFired ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>

              {showNotFired && (
                <div className="mt-3 space-y-2">
                  {recommendation.rules_not_fired.map((rnf) => (
                    <div
                      key={rnf.id}
                      className="p-3 rounded-lg bg-obsidian border border-graphite/60 flex items-start gap-3 text-xs font-mono"
                    >
                      <span className="px-2 py-0.5 rounded bg-carbon text-muted border border-graphite flex-shrink-0">
                        {rnf.id}
                      </span>
                      <div className="space-y-0.5">
                        <span className="text-muted font-medium">{rnf.name}</span>
                        <p className="text-muted/60">{rnf.reason}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Field-by-Field Config Comparison Diff */}
      {comparison && (
        <div className="rounded-card border border-graphite bg-carbon overflow-hidden space-y-4">
          <div className="px-6 py-4 border-b border-graphite flex items-center justify-between">
            <h3 className="font-heading font-semibold text-base text-fg">
              Configuration Diff (Baseline vs Recommended)
            </h3>
            <span className="text-xs font-mono text-muted">
              {comparison.differences.length} differences detected
            </span>
          </div>

          <div className="overflow-x-auto px-6 pb-6">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate border-b border-graphite uppercase text-muted">
                <tr>
                  <th className="py-2.5 px-4">Field</th>
                  <th className="py-2.5 px-4">Baseline ({comparison.config_a.name})</th>
                  <th className="py-2.5 px-4">Recommended ({comparison.config_b.name})</th>
                  <th className="py-2.5 px-4">Rule Attribution</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-graphite/60">
                {comparison.differences.map((d) => (
                  <tr key={d.field} className="hover:bg-slate/30">
                    <td className="py-3 px-4 text-fg font-medium">{d.field}</td>
                    <td className="py-3 px-4 text-muted">{JSON.stringify(d.a)}</td>
                    <td className="py-3 px-4 text-electric font-semibold">{JSON.stringify(d.b)}</td>
                    <td className="py-3 px-4 text-amber">{d.rules.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Visual Pipeline Architecture Graph */}
      {selectedConfigForGraph && (
        <div className="rounded-card border border-graphite bg-carbon p-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-electric" />
              <h3 className="font-heading font-semibold text-base text-fg">
                Architecture Graph (Config #{selectedConfigForGraph})
              </h3>
            </div>

            <div className="flex items-center gap-3">
              {/* Select config to display */}
              <div className="flex items-center gap-1.5 text-xs font-mono text-muted">
                <span>View Config:</span>
                {configs.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => loadGraph(c.id)}
                    className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
                      selectedConfigForGraph === c.id
                        ? "bg-electric text-white"
                        : "bg-slate text-muted hover:text-fg"
                    }`}
                  >
                    #{c.id} ({c.kind})
                  </button>
                ))}
              </div>

              {/* Toggle Format */}
              <div className="flex rounded bg-obsidian border border-graphite p-0.5 text-xs font-mono">
                <button
                  onClick={() => setGraphFormat("mermaid")}
                  className={`px-2.5 py-1 rounded ${
                    graphFormat === "mermaid" ? "bg-slate text-fg" : "text-muted hover:text-fg"
                  }`}
                >
                  Visual
                </button>
                <button
                  onClick={() => setGraphFormat("json")}
                  className={`px-2.5 py-1 rounded ${
                    graphFormat === "json" ? "bg-slate text-fg" : "text-muted hover:text-fg"
                  }`}
                >
                  JSON
                </button>
              </div>
            </div>
          </div>

          {/* Graph Renderer */}
          {graphFormat === "mermaid" ? (
            <MermaidRenderer chart={mermaidText} />
          ) : (
            <pre className="p-4 rounded-lg bg-obsidian border border-graphite text-xs font-mono text-fg overflow-x-auto max-h-[500px]">
              {JSON.stringify(jsonGraphData, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

