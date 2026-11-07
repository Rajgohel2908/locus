"use client";

import React, { useState, useEffect } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Play,
  RotateCcw,
  Check,
  X,
  Shield,
  Layers,
  ChevronDown,
  ChevronRight,
  TrendingUp,
  Clock,
  Sparkles,
  Info,
  RefreshCw,
  Sliders,
  GitCommit,
} from "lucide-react";
import {
  api,
  EvalRunItem,
  DoctorReportItem,
  DoctorFindingItem,
} from "@/lib/api";

export default function DoctorPage() {
  const [runs, setRuns] = useState<EvalRunItem[]>([]);
  const [selectedRunIds, setSelectedRunIds] = useState<number[]>([]);
  const [reports, setReports] = useState<DoctorReportItem[]>([]);
  const [activeReport, setActiveReport] = useState<DoctorReportItem | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [analyzing, setAnalyzing] = useState<boolean>(false);

  // Rejection modal state
  const [rejectModalFindingId, setRejectModalFindingId] = useState<number | null>(null);
  const [rejectionNote, setRejectionNote] = useState<string>("");

  // Action loading state
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

  // Collapsed not fired rules section
  const [showNotFired, setShowNotFired] = useState<boolean>(false);

  // Notification
  const [notification, setNotification] = useState<{ type: "success" | "error" | "info"; msg: string } | null>(null);

  useEffect(() => {
    loadInitial();
  }, []);

  async function loadInitial() {
    setLoading(true);
    try {
      const [rList, repList] = await Promise.all([
        api.getEvalRuns(),
        api.getDoctorReports(),
      ]);
      setRuns(rList);
      setReports(repList);

      if (rList.length > 0) {
        setSelectedRunIds([rList[0].id]);
      }

      if (repList.length > 0) {
        // Load the most recent report with findings
        const fullReport = await api.getDoctorReport(repList[0].id);
        setActiveReport(fullReport);
      }
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message || "Failed to load doctor data" });
    } finally {
      setLoading(false);
    }
  }

  async function handleAnalyze() {
    if (selectedRunIds.length === 0) return;
    setAnalyzing(true);
    try {
      setNotification({ type: "info", msg: "Diagnosing evaluation runs with rules D1-D9..." });
      const rep = await api.createDoctorReport(selectedRunIds);
      setActiveReport(rep);
      const repList = await api.getDoctorReports();
      setReports(repList);
      setNotification({
        type: "success",
        msg: `Diagnostic analysis complete: ${rep.findings?.length || 0} finding(s) generated.`,
      });
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message });
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleSelectReport(reportId: number) {
    try {
      const rep = await api.getDoctorReport(reportId);
      setActiveReport(rep);
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message });
    }
  }

  async function handleApprove(findingId: number) {
    setActionLoadingId(findingId);
    try {
      const updated = await api.approveDoctorFinding(findingId);
      updateFindingInState(updated);
      setNotification({ type: "success", msg: `Finding #${findingId} approved.` });
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleRejectConfirm() {
    if (!rejectModalFindingId) return;
    setActionLoadingId(rejectModalFindingId);
    try {
      const updated = await api.rejectDoctorFinding(rejectModalFindingId, rejectionNote);
      updateFindingInState(updated);
      setNotification({ type: "info", msg: `Finding #${rejectModalFindingId} rejected.` });
      setRejectModalFindingId(null);
      setRejectionNote("");
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleApply(findingId: number) {
    setActionLoadingId(findingId);
    try {
      const res = await api.applyDoctorFinding(findingId);
      updateFindingInState(res.finding);
      setNotification({
        type: "success",
        msg: `Applied patch! Created PipelineConfig #${res.pipeline_config.id} (kind='doctor').`,
      });
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message });
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleVerify(findingId: number) {
    setActionLoadingId(findingId);
    try {
      setNotification({ type: "info", msg: "Running automated verification evaluation against patched configuration..." });
      const res = await api.verifyDoctorFinding(findingId);
      updateFindingInState(res.finding);
      setNotification({
        type: "success",
        msg: `Verification run completed (Run #${res.verification_run.id}). Status: ${res.finding.status}`,
      });
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message });
    } finally {
      setActionLoadingId(null);
    }
  }

  function updateFindingInState(updated: DoctorFindingItem) {
    if (!activeReport || !activeReport.findings) return;
    setActiveReport({
      ...activeReport,
      findings: activeReport.findings.map((f) => (f.id === updated.id ? updated : f)),
    });
  }

  const notFiredReasons = activeReport?.summary?.not_fired_reasons || {};
  const notFiredCount = Object.keys(notFiredReasons).length;

  return (
    <div className="flex-1 bg-obsidian text-fg min-h-screen flex flex-col font-mono text-xs">
      {/* Top Bar */}
      <div className="h-16 px-6 border-b border-graphite bg-carbon flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-electric/10 border border-electric/30 flex items-center justify-center text-electric">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-fg font-heading tracking-tight">RAG Doctor v1</h1>
            <p className="text-[11px] text-muted">Automated failure diagnosis, counterfactual threshold sweeps & verified configuration patches</p>
          </div>
        </div>

        {/* Existing Reports Dropdown */}
        {reports.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-muted text-[11px]">Report:</span>
            <select
              value={activeReport?.id || ""}
              onChange={(e) => handleSelectReport(Number(e.target.value))}
              className="bg-slate border border-graphite rounded px-3 py-1.5 text-fg text-xs focus:outline-none focus:border-electric"
            >
              {reports.map((rep) => (
                <option key={rep.id} value={rep.id}>
                  Report #{rep.id} ({rep.findings_count || rep.summary?.findings_count || 0} findings)
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Notification Banner */}
      {notification && (
        <div
          className={`px-6 py-2 border-b flex items-center justify-between text-xs ${
            notification.type === "error"
              ? "bg-crimson/10 border-crimson/30 text-crimson"
              : notification.type === "success"
              ? "bg-emerald/10 border-emerald/30 text-emerald"
              : "bg-electric/10 border-electric/30 text-electric"
          }`}
        >
          <span>{notification.msg}</span>
          <button onClick={() => setNotification(null)} className="text-muted hover:text-fg">
            ✕
          </button>
        </div>
      )}

      {/* Workspace Body */}
      <div className="flex-1 p-6 space-y-6 overflow-y-auto">
        {/* Run Selector & Trigger Panel */}
        <div className="bg-carbon rounded-lg border border-graphite p-4 space-y-3">
          <div className="text-[11px] font-bold text-fg uppercase tracking-wider text-muted/70">
            Select Completed Evaluation Runs for Diagnostic Analysis
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {runs.map((r) => {
              const isSelected = selectedRunIds.includes(r.id);
              return (
                <button
                  key={r.id}
                  onClick={() => {
                    if (isSelected) setSelectedRunIds(selectedRunIds.filter((id) => id !== r.id));
                    else setSelectedRunIds([...selectedRunIds, r.id]);
                  }}
                  className={`px-3 py-1.5 rounded text-xs flex items-center gap-2 transition-colors ${
                    isSelected
                      ? "bg-electric/20 text-electric border border-electric/50 font-bold"
                      : "bg-slate border border-graphite text-muted hover:text-fg"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    readOnly
                    className="accent-electric pointer-events-none"
                  />
                  <span>Run #{r.id}: {r.name}</span>
                  <span className="text-[10px] text-muted">({r.variant.strategy})</span>
                </button>
              );
            })}

            <button
              onClick={handleAnalyze}
              disabled={analyzing || selectedRunIds.length === 0}
              className="ml-auto px-4 py-2 bg-electric hover:bg-electric/90 text-obsidian font-bold rounded flex items-center gap-2 transition-colors disabled:opacity-50 text-xs"
            >
              {analyzing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              <span>{analyzing ? "Running Doctor Engine..." : `Diagnose Selected (${selectedRunIds.length})`}</span>
            </button>
          </div>
        </div>

        {/* Diagnostic Findings List */}
        {activeReport && activeReport.findings && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-fg flex items-center gap-2">
                <span>Active Doctor Findings</span>
                <span className="text-xs text-muted font-normal">({activeReport.findings.length} findings across runs [{activeReport.run_ids.join(", ")}])</span>
              </h2>

              <div className="flex items-center gap-2 text-[11px] text-muted">
                <span>Evidence Levels:</span>
                <span className="px-2 py-0.5 rounded bg-blue-600 text-white font-bold">observed</span>
                <span className="px-2 py-0.5 rounded border border-electric text-electric">counterfactual</span>
                <span className="px-2 py-0.5 rounded bg-emerald text-obsidian font-bold">measured_effect</span>
                <span className="px-2 py-0.5 rounded bg-amber/20 text-amber border border-amber/40">hypothesis</span>
              </div>
            </div>

            {activeReport.findings.length === 0 ? (
              <div className="p-8 text-center bg-carbon rounded-lg border border-graphite text-muted">
                No diagnostic failures detected on selected runs. All evaluated rules satisfied thresholds cleanly.
              </div>
            ) : (
              activeReport.findings.map((f) => {
                const isLoading = actionLoadingId === f.id;
                const hasCounterfactual = !!f.counterfactual?.sweep_table;
                const sweep = f.counterfactual?.sweep_table || [];
                const optT = f.counterfactual?.optimal_threshold;

                return (
                  <div key={f.id} className="bg-carbon rounded-lg border border-graphite p-6 space-y-4">
                    {/* Header: Severity, Rule ID, Title, Status & Evidence Level */}
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-graphite pb-3">
                      <div className="flex items-center gap-2.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            f.severity === "critical"
                              ? "bg-crimson/20 text-crimson border border-crimson/40"
                              : f.severity === "warning"
                              ? "bg-amber/20 text-amber border border-amber/40"
                              : "bg-electric/15 text-electric border border-electric/30"
                          }`}
                        >
                          {f.severity}
                        </span>

                        <span className="font-mono text-xs text-muted font-bold">[{f.rule_id}]</span>

                        <h3 className="text-sm font-bold text-fg">{f.title}</h3>
                      </div>

                      <div className="flex items-center gap-2">
                        {/* Evidence Level Chip */}
                        {f.evidence_level === "observed" && (
                          <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-blue-600 text-white">
                            observed
                          </span>
                        )}
                        {f.evidence_level === "counterfactual" && (
                          <span className="px-2.5 py-0.5 rounded text-[10px] font-bold border border-electric text-electric bg-transparent">
                            counterfactual
                          </span>
                        )}
                        {f.evidence_level === "measured_effect" && (
                          <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-emerald text-obsidian">
                            measured_effect
                          </span>
                        )}
                        {f.evidence_level === "hypothesis" && (
                          <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-amber/20 text-amber border border-amber/40">
                            hypothesis
                          </span>
                        )}

                        {/* Finding Status Chip */}
                        <span
                          className={`px-2.5 py-0.5 rounded text-[10px] font-mono uppercase font-bold ${
                            f.status === "verified_gain"
                              ? "bg-emerald/20 text-emerald border border-emerald/50"
                              : f.status === "verified_no_change"
                              ? "bg-slate text-muted border border-graphite"
                              : f.status === "verified_regression"
                              ? "bg-crimson/20 text-crimson border border-crimson/50"
                              : f.status === "applied"
                              ? "bg-electric/20 text-electric border border-electric/50"
                              : f.status === "approved"
                              ? "bg-emerald/15 text-emerald"
                              : f.status === "rejected"
                              ? "bg-crimson/15 text-crimson"
                              : "bg-slate text-muted"
                          }`}
                        >
                          {f.status}
                        </span>
                      </div>
                    </div>

                    {/* Diagnosis */}
                    <div className="space-y-1">
                      <div className="text-[11px] font-bold text-muted/70 uppercase tracking-wider">Diagnosis</div>
                      <p className="text-fg text-xs leading-relaxed">{f.diagnosis}</p>
                    </div>

                    {/* Proposed Patch Diff View */}
                    {Object.keys(f.proposed_patch || {}).length > 0 && (
                      <div className="space-y-1">
                        <div className="text-[11px] font-bold text-muted/70 uppercase tracking-wider">Proposed Configuration Patch</div>
                        <div className="p-3 rounded bg-obsidian border border-graphite text-xs font-mono text-emerald">
                          <pre>{JSON.stringify(f.proposed_patch, null, 2)}</pre>
                        </div>
                      </div>
                    )}

                    {/* Expected Effect & Cost Note */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                      <div className="p-3 rounded bg-slate/30 border border-graphite space-y-1">
                        <span className="font-bold text-electric">Expected Effect:</span>
                        <p className="text-fg/90">{f.expected_effect}</p>
                      </div>

                      <div className="p-3 rounded bg-slate/30 border border-graphite space-y-1">
                        <span className="font-bold text-amber">Cost Note:</span>
                        <p className="text-muted">{f.cost_note || "No additional indexing or computational overhead."}</p>
                      </div>
                    </div>

                    {/* D4 / D5 Counterfactual Detail & SVG Sweep Chart */}
                    {hasCounterfactual && sweep.length > 0 && (
                      <div className="p-4 rounded-lg bg-obsidian border border-graphite space-y-3">
                        <div className="flex items-center justify-between border-b border-graphite/60 pb-2">
                          <span className="font-bold text-electric text-xs">
                            Threshold Counterfactual Sweep (Unsafe Rate vs False Refusal Rate)
                          </span>
                          <span className="text-[10px] text-muted font-mono">
                            Optimal t* = {optT !== undefined ? optT.toFixed(4) : "N/A"}
                          </span>
                        </div>

                        {/* Simple SVG Polyline Sweep Chart */}
                        <div className="py-2">
                          <svg viewBox="0 0 500 140" className="w-full h-36 bg-carbon/50 rounded border border-graphite">
                            {/* Grid lines */}
                            <line x1="40" y1="20" x2="480" y2="20" stroke="#2a2e39" strokeDasharray="2,2" />
                            <line x1="40" y1="70" x2="480" y2="70" stroke="#2a2e39" strokeDasharray="2,2" />
                            <line x1="40" y1="120" x2="480" y2="120" stroke="#2a2e39" />
                            <line x1="40" y1="20" x2="40" y2="120" stroke="#2a2e39" />

                            {/* Y axis labels */}
                            <text x="32" y="24" fill="#8892b0" fontSize="9" textAnchor="end">1.0</text>
                            <text x="32" y="74" fill="#8892b0" fontSize="9" textAnchor="end">0.5</text>
                            <text x="32" y="124" fill="#8892b0" fontSize="9" textAnchor="end">0.0</text>

                            {/* Polylines for unsafe rate (crimson) and false refusal rate (amber) */}
                            {(() => {
                              const pointsUnsafe = sweep
                                .map((pt, i) => {
                                  const x = 40 + (i / Math.max(1, sweep.length - 1)) * 440;
                                  const y = 120 - pt.unsafe_rate * 100;
                                  return `${x.toFixed(1)},${y.toFixed(1)}`;
                                })
                                .join(" ");

                              const pointsFR = sweep
                                .map((pt, i) => {
                                  const x = 40 + (i / Math.max(1, sweep.length - 1)) * 440;
                                  const y = 120 - pt.false_refusal_rate * 100;
                                  return `${x.toFixed(1)},${y.toFixed(1)}`;
                                })
                                .join(" ");

                              // Find optimal point index
                              const optIdx = sweep.findIndex((pt) => Math.abs(pt.threshold - (optT || 0)) < 1e-4);
                              const optX = optIdx >= 0 ? 40 + (optIdx / Math.max(1, sweep.length - 1)) * 440 : 40;

                              return (
                                <g>
                                  <polyline fill="none" stroke="#ff4d4f" strokeWidth="2" points={pointsUnsafe} />
                                  <polyline fill="none" stroke="#faad14" strokeWidth="2" points={pointsFR} />
                                  {/* Optimal threshold indicator vertical line */}
                                  <line x1={optX} y1="20" x2={optX} y2="120" stroke="#00f0ff" strokeWidth="1.5" strokeDasharray="3,3" />
                                  <circle cx={optX} cy="70" r="4" fill="#00f0ff" />
                                  <text x={optX + 4} y="40" fill="#00f0ff" fontSize="9" fontWeight="bold">Optimal t*</text>
                                </g>
                              );
                            })()}
                          </svg>

                          <div className="flex items-center justify-between text-[10px] text-muted mt-1 px-1">
                            <div className="flex items-center gap-3">
                              <span className="flex items-center gap-1 text-crimson">
                                <span className="w-2.5 h-0.5 bg-crimson" /> Unsafe Rate
                              </span>
                              <span className="flex items-center gap-1 text-amber">
                                <span className="w-2.5 h-0.5 bg-amber" /> False Refusal Rate
                              </span>
                            </div>
                            <span>Sweep across observed candidate cosine scores</span>
                          </div>
                        </div>

                        {/* In-sample vs Leave-One-Out (LOO) Values */}
                        <div className="grid grid-cols-2 gap-3 text-[11px] pt-2 border-t border-graphite/40">
                          <div>
                            <span className="text-muted">In-Sample Estimates:</span>
                            <div className="font-mono text-fg mt-0.5">
                              Unsafe: {(f.counterfactual?.in_sample?.proposed_unsafe_rate * 100 || 0).toFixed(1)}% | FR: {(f.counterfactual?.in_sample?.proposed_false_refusal_rate * 100 || 0).toFixed(1)}%
                            </div>
                          </div>
                          <div>
                            <span className="text-muted">Leave-One-Out (Jackknife) Estimates:</span>
                            <div className="font-mono text-fg mt-0.5">
                              LOO Unsafe: {(f.counterfactual?.leave_one_out?.loo_unsafe_rate * 100 || 0).toFixed(1)}% | LOO FR: {(f.counterfactual?.leave_one_out?.loo_false_refusal_rate * 100 || 0).toFixed(1)}%
                            </div>
                          </div>
                        </div>

                        {f.counterfactual?.warnings && f.counterfactual.warnings.length > 0 && (
                          <div className="text-[10px] text-amber flex items-center gap-1.5 pt-1">
                            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                            <span>{f.counterfactual.warnings[0]}</span>
                          </div>
                        )}

                        {f.counterfactual?.limitations && (
                          <div className="text-[10px] text-muted italic">
                            Limitation: {f.counterfactual.limitations}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Verification Card (if verified) */}
                    {f.status.startsWith("verified_") && (
                      <div
                        className={`p-4 rounded-lg border text-xs space-y-2 ${
                          f.status === "verified_gain"
                            ? "bg-emerald/10 border-emerald/40 text-emerald"
                            : f.status === "verified_no_change"
                            ? "bg-slate/50 border-graphite text-muted"
                            : "bg-crimson/10 border-crimson/40 text-crimson"
                        }`}
                      >
                        <div className="flex items-center justify-between font-bold">
                          <span>Verification Result: {f.status.replace("verified_", "").toUpperCase()}</span>
                          <span className="font-mono">Verification Run #{f.verification_run_id}</span>
                        </div>
                        <p className="text-fg/90 text-[11px]">
                          Automated paired evaluation executed against patched pipeline configuration #{f.applied_config_id}.
                        </p>
                      </div>
                    )}

                    {/* Action Buttons Lifecycle Flow */}
                    <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-graphite/40">
                      {f.status === "open" && (
                        <>
                          <button
                            onClick={() => handleApprove(f.id)}
                            disabled={isLoading}
                            className="px-3 py-1.5 bg-emerald/20 hover:bg-emerald/30 text-emerald border border-emerald/40 rounded flex items-center gap-1.5 font-bold transition-colors disabled:opacity-50"
                          >
                            <Check className="w-3.5 h-3.5" />
                            <span>Approve Patch</span>
                          </button>

                          <button
                            onClick={() => setRejectModalFindingId(f.id)}
                            disabled={isLoading}
                            className="px-3 py-1.5 bg-crimson/15 hover:bg-crimson/25 text-crimson border border-crimson/40 rounded flex items-center gap-1.5 font-bold transition-colors disabled:opacity-50"
                          >
                            <X className="w-3.5 h-3.5" />
                            <span>Reject</span>
                          </button>
                        </>
                      )}

                      {f.status === "approved" && (
                        <button
                          onClick={() => handleApply(f.id)}
                          disabled={isLoading || Object.keys(f.proposed_patch || {}).length === 0}
                          className="px-4 py-1.5 bg-electric hover:bg-electric/90 text-obsidian rounded flex items-center gap-1.5 font-bold transition-colors disabled:opacity-50"
                        >
                          {isLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Layers className="w-3.5 h-3.5" />}
                          <span>Apply Patch to Pipeline</span>
                        </button>
                      )}

                      {f.status === "applied" && (
                        <button
                          onClick={() => handleVerify(f.id)}
                          disabled={isLoading}
                          className="px-4 py-1.5 bg-emerald hover:bg-emerald/90 text-obsidian rounded flex items-center gap-1.5 font-bold transition-colors disabled:opacity-50"
                        >
                          {isLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                          <span>Verify Patch (Run Benchmark Suite)</span>
                        </button>
                      )}

                      {isLoading && (
                        <div className="flex items-center gap-2 text-muted text-xs ml-2">
                          <RefreshCw className="w-3.5 h-3.5 animate-spin text-electric" />
                          <span>Processing patch lifecycle...</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}

            {/* Collapsed Section: Rules Evaluated But Not Fired */}
            <div className="bg-carbon rounded-lg border border-graphite overflow-hidden">
              <div
                onClick={() => setShowNotFired(!showNotFired)}
                className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate/30 transition-colors"
              >
                <div className="flex items-center gap-2 font-bold text-fg">
                  {showNotFired ? <ChevronDown className="w-4 h-4 text-muted" /> : <ChevronRight className="w-4 h-4 text-muted" />}
                  <span>Rules Evaluated But Not Fired ({notFiredCount})</span>
                </div>
                <span className="text-[11px] text-muted">Documented reasons why diagnostic rules did not trigger</span>
              </div>

              {showNotFired && (
                <div className="p-4 bg-obsidian border-t border-graphite space-y-2 text-xs">
                  {Object.entries(notFiredReasons).map(([ruleId, reason]) => (
                    <div key={ruleId} className="flex items-start gap-3 p-2 rounded bg-carbon border border-graphite/40">
                      <span className="font-mono text-electric font-bold w-12 flex-shrink-0">{ruleId}:</span>
                      <span className="text-muted/90">{reason}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Reject Modal */}
      {rejectModalFindingId && (
        <div className="fixed inset-0 bg-obsidian/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-carbon border border-graphite rounded-lg max-w-md w-full p-6 space-y-4">
            <h3 className="text-sm font-bold text-fg">Reject Finding #{rejectModalFindingId}</h3>
            <p className="text-muted text-xs">Provide a rationale or reason for rejecting this diagnostic remediation.</p>
            <textarea
              value={rejectionNote}
              onChange={(e) => setRejectionNote(e.target.value)}
              placeholder="e.g. Expected threshold variance on historical documents..."
              className="w-full h-24 bg-slate border border-graphite rounded p-3 text-fg text-xs focus:outline-none focus:border-crimson"
            />
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => {
                  setRejectModalFindingId(null);
                  setRejectionNote("");
                }}
                className="px-3 py-1.5 rounded bg-slate text-muted hover:text-fg text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleRejectConfirm}
                className="px-4 py-1.5 rounded bg-crimson hover:bg-crimson/90 text-white font-bold text-xs"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

