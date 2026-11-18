"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  Activity,
  Sparkles,
  History,
  FileText,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Flag,
  Calendar,
  RefreshCw,
  Sliders,
  ExternalLink,
  Info,
} from "lucide-react";
import {
  api,
  SourceItem,
  QualityReport,
  CleaningProposal,
  DocumentItem,
  IndexRunItem,
  ChunkItem,
  RecordItem,
} from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";

export default function SourceDetailPage({ params }: { params?: { id: string } }) {
  const routeParams = useParams();
  const idStr =
    params?.id ||
    (typeof routeParams?.id === "string"
      ? routeParams.id
      : Array.isArray(routeParams?.id)
      ? routeParams.id[0]
      : "0");
  const sourceId = parseInt(idStr, 10) || 0;
  const searchParams = useSearchParams();
  const paramTab = searchParams?.get("tab") || "health";
  const initialTab = paramTab === "indexing" ? "index" : paramTab;

  const [tab, setTab] = useState<string>(initialTab);
  const [source, setSource] = useState<SourceItem | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Trust Strip State
  const [activeCount, setActiveCount] = useState<number | string>("n/a");
  const [quarantinedCount, setQuarantinedCount] = useState<number | string>("n/a");
  const [pendingCritCount, setPendingCritCount] = useState<number | string>("n/a");
  const [freshnessSummary, setFreshnessSummary] = useState<string>("n/a");
  const [currentVersion, setCurrentVersion] = useState<number>(1);

  // Health State
  const [quality, setQuality] = useState<QualityReport | null>(null);

  // Cleaning State
  const [roles, setRoles] = useState<Record<string, string>>({});
  const [proposals, setProposals] = useState<CleaningProposal[]>([]);
  const [cleaningLoading, setCleaningLoading] = useState<boolean>(false);
  const [showApplyModal, setShowApplyModal] = useState<boolean>(false);

  // Versions State
  const [versions, setVersions] = useState<any[]>([]);
  const [quarantinedRecords, setQuarantinedRecords] = useState<RecordItem[]>([]);
  const [recordsPage, setRecordsPage] = useState<number>(1);
  const [recordsTotal, setRecordsTotal] = useState<number>(0);

  // Documents State
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocForOverride, setSelectedDocForOverride] = useState<DocumentItem | null>(null);
  const [overrideDate, setOverrideDate] = useState<string>("");
  const [overrideTitle, setOverrideTitle] = useState<string>("");

  // Index State
  const [indexRuns, setIndexRuns] = useState<IndexRunItem[]>([]);
  const [selectedRunChunks, setSelectedRunChunks] = useState<ChunkItem[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [chunkSizeInput, setChunkSizeInput] = useState<number>(800);
  const [chunkOverlapInput, setChunkOverlapInput] = useState<number>(120);

  // Load Source & Trust Strip
  async function loadSourceData() {
    try {
      setLoading(true);
      setError(null);
      const s = await api.getSource(sourceId);
      setSource(s);
      setCurrentVersion(s.latest_version ?? 1);

      // Load Quality Report
      try {
        const q = await api.getSourceQuality(sourceId, s.latest_version ?? 1);
        setQuality(q);

        if (q.freshness_distribution) {
          const fresh = q.freshness_distribution["fresh"] || 0;
          const stale = q.freshness_distribution["stale"] || 0;
          const unk = q.freshness_distribution["unknown"] || 0;
          setFreshnessSummary(`${fresh} fresh, ${stale} stale, ${unk} unk`);
        }
      } catch {
        // Quality report may not exist yet
      }

      // Load Proposals
      try {
        const pList = await api.getProposals(sourceId);
        setProposals(pList);
        const crits = pList.filter(
          (p) => p.status === "pending" && p.severity === "critical"
        ).length;
        setPendingCritCount(crits);
      } catch {
        setPendingCritCount("n/a");
      }

      // Load Records Counts
      try {
        const recActive = await api.getRecords(sourceId, {
          version: s.latest_version ?? 1,
          status: "active",
          limit: 1,
        });
        setActiveCount(recActive.total);

        const recQuar = await api.getRecords(sourceId, {
          version: s.latest_version ?? 1,
          status: "quarantined",
          limit: 1,
        });
        setQuarantinedCount(recQuar.total);
      } catch {
        setActiveCount(s.records_count ?? s.documents_count ?? "n/a");
      }

      // Load Roles
      try {
        const rMap = await api.getRoles(sourceId);
        setRoles(rMap);
      } catch {}

      // Load Versions
      try {
        const vList = await api.getSourceVersions(sourceId);
        setVersions(vList);
      } catch {}

      // Load Documents
      try {
        const docList = await api.getDocuments(sourceId);
        setDocuments(docList);
      } catch {}

      // Load Index Runs
      try {
        const irList = await api.getIndexRuns(sourceId);
        setIndexRuns(irList);
        if (irList.length > 0 && !selectedRunId) {
          loadChunks(irList[0].id);
        }
      } catch {}
    } catch (err: any) {
      setError(err.message || "Failed to load source details");
    } finally {
      setLoading(false);
    }
  }

  async function loadQuarantined(page: number = 1) {
    try {
      const res = await api.getRecords(sourceId, {
        version: currentVersion,
        status: "quarantined",
        page,
        limit: 10,
      });
      setQuarantinedRecords(res.records);
      setRecordsTotal(res.total);
      setRecordsPage(page);
    } catch {}
  }

  async function loadChunks(runId: number) {
    setSelectedRunId(runId);
    try {
      const ch = await api.getChunks(runId, 25);
      setSelectedRunChunks(Array.isArray(ch) ? ch : (ch as any)?.chunks || []);
    } catch {
      setSelectedRunChunks([]);
    }
  }

  useEffect(() => {
    loadSourceData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceId]);

  useEffect(() => {
    if (tab === "versions") {
      loadQuarantined(1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, currentVersion]);

  // Actions
  async function handleInferRoles() {
    try {
      setCleaningLoading(true);
      const res = await api.inferRoles(sourceId);
      setRoles(res);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setCleaningLoading(false);
    }
  }

  async function handleUpdateRole(col: string, newRole: string) {
    const updated = { ...roles, [col]: newRole };
    setRoles(updated);
    try {
      await api.updateRoles(sourceId, updated);
    } catch (err: any) {
      alert(err.message);
    }
  }

  async function handleGenerateProposals() {
    try {
      setCleaningLoading(true);
      const pList = await api.generateProposals(sourceId);
      setProposals(pList);
      const crits = pList.filter(
        (p) => p.status === "pending" && p.severity === "critical"
      ).length;
      setPendingCritCount(crits);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setCleaningLoading(false);
    }
  }

  async function handleApproveProposal(id: number) {
    try {
      await api.approveProposal(id);
      setProposals((prev) =>
        prev.map((p) => (p.id === id ? { ...p, status: "approved" } : p))
      );
    } catch (err: any) {
      alert(err.message);
    }
  }

  async function handleRejectProposal(id: number) {
    try {
      await api.rejectProposal(id);
      setProposals((prev) =>
        prev.map((p) => (p.id === id ? { ...p, status: "rejected" } : p))
      );
    } catch (err: any) {
      alert(err.message);
    }
  }

  async function handleApproveAll(minSeverity: string = "info") {
    try {
      await api.approveAllProposals(sourceId, minSeverity);
      const updated = await api.getProposals(sourceId);
      setProposals(updated);
    } catch (err: any) {
      alert(err.message);
    }
  }

  async function handleApplyCleaning() {
    setShowApplyModal(false);
    try {
      setCleaningLoading(true);
      const res = await api.applyCleaning(sourceId);
      alert(
        `Applied proposals successfully!\nNew Version: v${res.version_no}\nActive Rows: ${res.rows_active}\nQuarantined: ${res.rows_quarantined}`
      );
      await loadSourceData();
      setTab("versions");
    } catch (err: any) {
      alert(err.message);
    } finally {
      setCleaningLoading(false);
    }
  }

  async function handleOverrideSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedDocForOverride) return;

    try {
      await api.overrideDocument(selectedDocForOverride.id, {
        published_at: overrideDate || undefined,
        title: overrideTitle || undefined,
      });
      setSelectedDocForOverride(null);
      const docList = await api.getDocuments(sourceId);
      setDocuments(docList);
    } catch (err: any) {
      alert(err.message);
    }
  }

  async function handleStartIndex() {
    try {
      await api.startIndexRun(sourceId, {
        version: currentVersion,
        chunk_size: chunkSizeInput,
        chunk_overlap: chunkOverlapInput,
      });
      const irList = await api.getIndexRuns(sourceId);
      setIndexRuns(irList);
      if (irList.length > 0) loadChunks(irList[0].id);
    } catch (err: any) {
      alert(err.message);
    }
  }

  const approvedCount = proposals.filter((p) => p.status === "approved").length;
  const isStructured = source?.name.endsWith(".csv") || source?.name.endsWith(".xlsx");

  if (loading) {
    return (
      <div className="p-8 space-y-4">
        <div className="h-8 w-48 bg-slate rounded animate-pulse" />
        <div className="h-24 bg-slate rounded-card animate-pulse" />
        <div className="h-64 bg-slate rounded-card animate-pulse" />
      </div>
    );
  }

  if (error || !source) {
    return (
      <div className="p-8 text-center space-y-3">
        <div className="text-crimson font-medium">Failed to load source: {error}</div>
        <Link href="/sources" className="text-electric text-sm hover:underline">
          &larr; Back to Sources
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div>
        <Link
          href="/sources"
          className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-fg font-medium transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Sources
        </Link>
      </div>

      {/* Header & Source Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-heading font-bold text-2xl text-fg tracking-tight">
              {source.name}
            </h1>
            <span className="px-2.5 py-0.5 rounded bg-slate border border-graphite text-xs font-mono text-muted">
              {source.source_type}
            </span>
          </div>
          <div className="text-xs text-muted mt-1 font-mono">
            Source ID: #{source.id} &bull; Ingested {source.created_at ? new Date(source.created_at).toLocaleString() : "n/a"}
          </div>
        </div>

        <button
          onClick={loadSourceData}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate border border-graphite text-xs font-medium text-muted hover:text-fg font-mono"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {/* Persistent TRUST STRIP */}
      <div className="p-4 rounded-card border border-graphite bg-carbon grid grid-cols-2 sm:grid-cols-4 gap-4 divide-y sm:divide-y-0 sm:divide-x divide-graphite">
        <div className="flex flex-col px-3">
          <span className="text-[11px] font-mono uppercase tracking-wider text-muted">
            Version
          </span>
          <span className="font-heading font-semibold text-lg text-fg mt-0.5">
            v{currentVersion}
          </span>
        </div>

        <div className="flex flex-col px-3 pt-2 sm:pt-0">
          <span className="text-[11px] font-mono uppercase tracking-wider text-muted">
            Active / Quarantined
          </span>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="font-heading font-semibold text-lg text-emerald">
              {activeCount}
            </span>
            <span className="text-muted">/</span>
            <span className={`font-heading font-semibold text-lg ${typeof quarantinedCount === "number" && quarantinedCount > 0 ? "text-crimson" : "text-muted"}`}>
              {quarantinedCount}
            </span>
          </div>
        </div>

        <div className="flex flex-col px-3 pt-2 sm:pt-0">
          <span className="text-[11px] font-mono uppercase tracking-wider text-muted">
            Pending Critical
          </span>
          <span
            className={`font-heading font-semibold text-lg mt-0.5 ${
              typeof pendingCritCount === "number" && pendingCritCount > 0 ? "text-crimson" : "text-muted"
            }`}
          >
            {pendingCritCount}
          </span>
        </div>

        <div className="flex flex-col px-3 pt-2 sm:pt-0">
          <span className="text-[11px] font-mono uppercase tracking-wider text-muted">
            Freshness Summary
          </span>
          <span className="font-heading font-medium text-xs text-muted mt-1 font-mono">
            {freshnessSummary}
          </span>
        </div>
      </div>

      {/* Tabs Navigation (Horizontally scrollable on mobile) */}
      <div className="border-b border-graphite flex gap-4 sm:gap-6 text-xs sm:text-sm font-medium overflow-x-auto whitespace-nowrap pb-0.5">
        {[
          { id: "health", label: "Health", icon: Activity },
          { id: "cleaning", label: "Cleaning", icon: Sparkles },
          { id: "versions", label: "Versions", icon: History },
          { id: "documents", label: "Documents", icon: FileText, hide: isStructured },
          { id: "index", label: "Indexing", icon: Layers },
        ]
          .filter((t) => !t.hide)
          .map((t) => {
            const Icon = t.icon;
            const isActive = tab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-2 pb-3 border-b-2 transition-colors ${
                  isActive
                    ? "border-electric text-electric font-semibold"
                    : "border-transparent text-muted hover:text-fg"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{t.label}</span>
              </button>
            );
          })}
      </div>

      {/* TAB 1: HEALTH */}
      {tab === "health" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Duplicates Card */}
            <div className="p-5 rounded-card border border-graphite bg-carbon">
              <span className="text-xs font-mono uppercase text-muted">
                Duplicate Rows
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="font-heading font-bold text-2xl text-fg">
                  {quality?.duplicate_rows_count ?? "0"}
                </span>
                <span className="text-xs text-muted font-mono">
                  ({quality?.duplicate_rows_percentage ? `${quality.duplicate_rows_percentage.toFixed(1)}%` : "0%"})
                </span>
              </div>
            </div>

            {/* Inconsistent Categories */}
            <div className="p-5 rounded-card border border-graphite bg-carbon">
              <span className="text-xs font-mono uppercase text-muted">
                Category Inconsistencies
              </span>
              <div className="mt-2 text-sm text-fg font-mono">
                {quality?.inconsistent_categories && Object.keys(quality.inconsistent_categories).length > 0 ? (
                  Object.entries(quality.inconsistent_categories).map(([col, variants]: any) => (
                    <div key={col} className="truncate">
                      <span className="text-amber font-semibold">{col}:</span>{" "}
                      {Array.isArray(variants) ? variants.join(", ") : JSON.stringify(variants)}
                    </div>
                  ))
                ) : (
                  <span className="text-muted">None detected</span>
                )}
              </div>
            </div>

            {/* Outliers & Dates */}
            <div className="p-5 rounded-card border border-graphite bg-carbon">
              <span className="text-xs font-mono uppercase text-muted">
                Invalid Dates & Outliers
              </span>
              <div className="mt-2 space-y-1 text-sm font-mono text-muted">
                <div>
                  Invalid Dates:{" "}
                  <span className="text-fg font-semibold">
                    {quality?.invalid_dates ? Object.keys(quality.invalid_dates).length : 0}
                  </span>
                </div>
                <div>
                  Outlier Flags:{" "}
                  <span className="text-fg font-semibold">
                    {quality?.outliers ? Object.keys(quality.outliers).length : 0}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Missing Percentage per Column */}
          {quality?.columns && (
            <div className="p-6 rounded-card border border-graphite bg-carbon space-y-4">
              <h3 className="font-heading font-semibold text-base text-fg">
                Column Completeness & Missing Rates
              </h3>
              <div className="space-y-3">
                {Object.entries(quality.columns).map(([colName, colData]: any) => {
                  const missingPct = colData.missing_percentage ?? 0;
                  const barColor =
                    missingPct > 20
                      ? "bg-crimson"
                      : missingPct > 5
                      ? "bg-amber"
                      : "bg-emerald";

                  return (
                    <div key={colName} className="space-y-1">
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-fg font-medium">{colName}</span>
                        <span className="text-muted">
                          {colData.missing_count ?? 0} missing ({missingPct.toFixed(1)}%)
                        </span>
                      </div>
                      <div className="h-2 w-full bg-slate rounded-full overflow-hidden">
                        <div
                          className={`h-full ${barColor} transition-all`}
                          style={{ width: `${Math.min(100, missingPct)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: CLEANING */}
      {tab === "cleaning" && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="p-4 rounded-card border border-graphite bg-carbon flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button
                onClick={handleInferRoles}
                disabled={cleaningLoading}
                className="px-3.5 py-1.5 rounded-lg bg-slate hover:bg-slate/80 text-fg text-xs font-medium border border-graphite transition-colors flex items-center gap-1.5"
              >
                <Sliders className="w-3.5 h-3.5 text-electric" />
                Infer Roles
              </button>
              <button
                onClick={handleGenerateProposals}
                disabled={cleaningLoading}
                className="px-3.5 py-1.5 rounded-lg bg-slate hover:bg-slate/80 text-fg text-xs font-medium border border-graphite transition-colors flex items-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5 text-amber" />
                Generate Proposals
              </button>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => handleApproveAll("info")}
                disabled={proposals.length === 0}
                className="px-3.5 py-1.5 rounded-lg bg-slate hover:bg-slate/80 text-fg text-xs font-medium border border-graphite transition-colors"
              >
                Approve All
              </button>
              <button
                onClick={() => setShowApplyModal(true)}
                disabled={approvedCount === 0 || cleaningLoading}
                className="px-4 py-1.5 rounded-lg bg-electric hover:brightness-110 active:brightness-95 text-black text-xs font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_12px_rgba(200,244,50,0.15)] cursor-pointer"
              >
                Apply Approved ({approvedCount})
              </button>
            </div>
          </div>

          {/* Column Roles Editor */}
          {Object.keys(roles).length > 0 && (
            <div className="p-5 rounded-card border border-graphite bg-carbon space-y-3">
              <h3 className="font-heading font-semibold text-sm text-fg">
                Column Roles
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(roles).map(([col, role]) => (
                  <div
                    key={col}
                    className="p-3 rounded-lg bg-slate/60 border border-graphite flex flex-col gap-1.5"
                  >
                    <span className="text-xs font-mono font-medium text-fg truncate">
                      {col}
                    </span>
                    <select
                      value={role}
                      onChange={(e) => handleUpdateRole(col, e.target.value)}
                      className="px-2 py-1 rounded bg-obsidian border border-graphite text-xs text-fg focus:border-electric focus:outline-none"
                    >
                      <option value="identifier">identifier</option>
                      <option value="numeric">numeric</option>
                      <option value="category">category</option>
                      <option value="date">date</option>
                      <option value="optional">optional</option>
                      <option value="required">required</option>
                    </select>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Proposals List */}
          <div className="rounded-card border border-graphite bg-carbon overflow-hidden">
            <div className="px-6 py-4 border-b border-graphite">
              <h3 className="font-heading font-semibold text-base text-fg">
                Cleaning Proposals ({proposals.length})
              </h3>
            </div>

            {proposals.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted">
                No cleaning proposals generated yet. Click &quot;Generate Proposals&quot; above.
              </div>
            ) : (
              <div className="divide-y divide-graphite/60">
                {proposals.map((p) => (
                  <div key={p.id} className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <StatusBadge status={p.severity} label={p.severity} />
                        <span className="font-heading font-semibold text-sm text-fg">
                          {p.proposal_type}
                        </span>
                        {p.column_name && (
                          <span className="text-xs font-mono text-muted">
                            on [{p.column_name}]
                          </span>
                        )}
                        <StatusBadge status={p.status} label={p.status} />
                      </div>
                      <p className="text-xs text-muted max-w-2xl">{p.description}</p>

                      {p.sample_before_after && p.sample_before_after.length > 0 && (
                        <div className="mt-2 text-[11px] font-mono bg-obsidian p-2 rounded border border-graphite max-w-xl">
                          <span className="text-muted block mb-1">Impact Examples:</span>
                          {p.sample_before_after.slice(0, 3).map((ex, i) => (
                            <div key={i} className="text-muted/80">
                              <span className="text-crimson line-through">{String(ex.before)}</span> &rarr;{" "}
                              <span className="text-emerald">{String(ex.after)}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      {p.status === "pending" ? (
                        <>
                          <button
                            onClick={() => handleApproveProposal(p.id)}
                            className="px-3 py-1 rounded bg-emerald/15 hover:bg-emerald/25 text-emerald border border-emerald/30 text-xs font-medium"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleRejectProposal(p.id)}
                            className="px-3 py-1 rounded bg-carbon hover:bg-slate text-muted border border-graphite text-xs font-medium"
                          >
                            Reject
                          </button>
                        </>
                      ) : (
                        <span className="text-xs font-mono text-muted capitalize">
                          {p.status}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Confirm Apply Modal */}
          {showApplyModal && (
            <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <div className="bg-carbon border border-graphite rounded-card max-w-md w-full p-6 space-y-4">
                <h3 className="font-heading font-bold text-lg text-fg">
                  Apply Approved Proposals?
                </h3>
                <p className="text-sm text-muted">
                  Applying proposals creates a <strong className="text-fg">NEW version</strong> in the database (v{currentVersion + 1}).
                  The original version 1 and raw data stay completely untouched.
                </p>
                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    onClick={() => setShowApplyModal(false)}
                    className="px-4 py-2 rounded-lg bg-slate text-sm text-muted hover:text-fg font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleApplyCleaning}
                    className="px-5 py-2 rounded-lg bg-electric hover:brightness-110 active:brightness-95 text-black text-sm font-bold cursor-pointer shadow-[0_0_12px_rgba(200,244,50,0.15)]"
                  >
                    Confirm &amp; Apply
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: VERSIONS */}
      {tab === "versions" && (
        <div className="space-y-6">
          <div className="p-6 rounded-card border border-graphite bg-carbon space-y-4">
            <h3 className="font-heading font-semibold text-base text-fg">
              Version History
            </h3>
            <div className="space-y-3">
              {versions.map((v) => (
                <div
                  key={v.version_no}
                  className="p-4 rounded-lg bg-slate border border-graphite flex items-center justify-between"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-sm text-fg">
                        Version {v.version_no}
                      </span>
                      {v.version_no === currentVersion && (
                        <StatusBadge status="active" label="Latest" />
                      )}
                    </div>
                    <p className="text-xs text-muted font-mono">
                      {v.note || "No version note"} &bull; Created {v.created_at ? new Date(v.created_at).toLocaleDateString() : "n/a"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quarantined Rows Table */}
          <div className="rounded-card border border-graphite bg-carbon overflow-hidden">
            <div className="px-6 py-4 border-b border-graphite flex items-center justify-between">
              <h3 className="font-heading font-semibold text-base text-fg">
                Quarantined Rows ({recordsTotal})
              </h3>
              <span className="text-xs text-muted font-mono">
                Page {recordsPage}
              </span>
            </div>

            {quarantinedRecords.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted">
                No quarantined rows in version {currentVersion}.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate border-b border-graphite text-xs text-muted font-mono uppercase">
                    <tr>
                      <th className="py-2.5 px-6">Row Index</th>
                      <th className="py-2.5 px-6">Data</th>
                      <th className="py-2.5 px-6">Quarantine Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-graphite/60 font-mono text-xs">
                    {quarantinedRecords.map((r) => (
                      <tr key={r.id}>
                        <td className="py-3 px-6 text-muted">#{r.row_index}</td>
                        <td className="py-3 px-6 text-fg max-w-md truncate">
                          {JSON.stringify(r.data)}
                        </td>
                        <td className="py-3 px-6 text-crimson">
                          {r.metadata?.quarantine_reason || "Missing identifier"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: DOCUMENTS (For Text/Web Sources) */}
      {tab === "documents" && (
        <div className="space-y-6">
          <div className="rounded-card border border-graphite bg-carbon overflow-hidden">
            <div className="px-6 py-4 border-b border-graphite">
              <h3 className="font-heading font-semibold text-base text-fg">
                Documents &amp; Freshness ({documents.length})
              </h3>
            </div>

            <div className="divide-y divide-graphite/60">
              {documents.map((d) => (
                <div key={d.id} className="p-5 flex items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-fg">
                        {d.title || `Document #${d.id}`}
                      </span>
                      {d.page_number && (
                        <span className="text-xs text-muted font-mono">
                          (Page {d.page_number})
                        </span>
                      )}
                      <StatusBadge status={d.freshness_bucket || "unknown"} label={d.freshness_bucket || "unknown"} />
                    </div>
                    <div className="text-xs text-muted font-mono flex items-center gap-3">
                      <span>Published: {d.published_at ? new Date(d.published_at).toLocaleDateString() : "Undated"}</span>
                      <span>Words: {d.word_count ?? "n/a"}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setSelectedDocForOverride(d);
                      setOverrideTitle(d.title || "");
                      setOverrideDate(d.published_at ? d.published_at.slice(0, 10) : "");
                    }}
                    className="px-3 py-1.5 rounded-lg bg-slate hover:bg-slate/80 text-xs font-mono text-electric border border-graphite"
                  >
                    Edit Override
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Document Override Modal */}
          {selectedDocForOverride && (
            <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <form
                onSubmit={handleOverrideSubmit}
                className="bg-carbon border border-graphite rounded-card max-w-md w-full p-6 space-y-4"
              >
                <h3 className="font-heading font-bold text-base text-fg">
                  Override Document Metadata
                </h3>
                <p className="text-xs text-muted">
                  Overrides take effect on the <strong className="text-fg">next index run</strong>.
                </p>

                <div>
                  <label className="block text-xs font-medium text-muted mb-1">
                    Title
                  </label>
                  <input
                    type="text"
                    value={overrideTitle}
                    onChange={(e) => setOverrideTitle(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-obsidian border border-graphite text-xs text-fg focus:border-electric focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-muted mb-1">
                    Published At Date
                  </label>
                  <input
                    type="date"
                    value={overrideDate}
                    onChange={(e) => setOverrideDate(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-obsidian border border-graphite text-xs text-fg focus:border-electric focus:outline-none font-mono"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-3">
                  <button
                    type="button"
                    onClick={() => setSelectedDocForOverride(null)}
                    className="px-4 py-1.5 rounded bg-slate text-xs text-muted hover:text-fg font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 rounded bg-electric hover:brightness-110 active:brightness-95 text-black text-xs font-bold cursor-pointer"
                  >
                    Save Override
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      )}

      {/* TAB 5: INDEXING */}
      {tab === "index" && (
        <div className="space-y-6">
          <div className="p-6 rounded-card border border-graphite bg-carbon space-y-4">
            <h3 className="font-heading font-semibold text-base text-fg">
              Trigger Indexing Run
            </h3>
            <div className="flex flex-wrap items-center gap-4">
              <div>
                <label className="block text-xs font-mono text-muted mb-1">
                  Chunk Size (chars)
                </label>
                <input
                  type="number"
                  value={chunkSizeInput}
                  onChange={(e) => setChunkSizeInput(parseInt(e.target.value) || 800)}
                  className="px-3 py-1.5 rounded bg-obsidian border border-graphite text-xs font-mono text-fg w-32 focus:border-electric focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-muted mb-1">
                  Chunk Overlap (chars)
                </label>
                <input
                  type="number"
                  value={chunkOverlapInput}
                  onChange={(e) => setChunkOverlapInput(parseInt(e.target.value) || 120)}
                  className="px-3 py-1.5 rounded bg-obsidian border border-graphite text-xs font-mono text-fg w-32 focus:border-electric focus:outline-none"
                />
              </div>

              <div className="pt-5">
                <button
                  onClick={handleStartIndex}
                  className="px-4 py-2 rounded-lg bg-electric hover:brightness-110 active:brightness-95 text-black text-xs font-bold cursor-pointer shadow-[0_0_12px_rgba(200,244,50,0.15)]"
                >
                  Start Index Run
                </button>
              </div>
            </div>
          </div>

          {/* Index Runs List */}
          <div className="rounded-card border border-graphite bg-carbon overflow-hidden">
            <div className="px-6 py-4 border-b border-graphite">
              <h3 className="font-heading font-semibold text-base text-fg">
                Index Runs History ({indexRuns.length})
              </h3>
            </div>

            <div className="divide-y divide-graphite/60">
              {indexRuns.map((ir) => (
                <div
                  key={ir.id}
                  onClick={() => loadChunks(ir.id)}
                  className={`p-4 flex items-center justify-between cursor-pointer transition-colors ${
                    selectedRunId === ir.id ? "bg-slate border-l-4 border-electric" : "hover:bg-slate/50"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-sm text-fg">
                        Run #{ir.id}
                      </span>
                      <StatusBadge status={ir.status} label={ir.status} />
                      <span className="text-xs font-mono text-muted">
                        v{ir.source_version}
                      </span>
                    </div>
                    <div className="text-xs text-muted font-mono">
                      Config: {ir.chunk_size}/{ir.chunk_overlap} chars &bull; Chunks: {ir.chunks_created}
                    </div>
                  </div>

                  <span className="text-xs font-mono text-electric">
                    {selectedRunId === ir.id ? "Viewing Chunks" : "Inspect Chunks"} &rarr;
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Chunk Browser */}
          {selectedRunId && (
            <div className="rounded-card border border-graphite bg-carbon p-6 space-y-4">
              <h3 className="font-heading font-semibold text-base text-fg">
                Chunk Browser (Run #{selectedRunId})
              </h3>

              <div className="space-y-3">
                {(Array.isArray(selectedRunChunks) ? selectedRunChunks : []).map((ch) => (
                  <div
                    key={ch.id}
                    className="p-3.5 rounded bg-obsidian border border-graphite text-xs font-mono space-y-1"
                  >
                    <div className="flex items-center justify-between text-muted">
                      <span>Chunk #{ch.chunk_index} (ID: {ch.id})</span>
                      <span>{ch.token_count ?? ch.content.length} chars</span>
                    </div>
                    <p className="text-fg/90 whitespace-pre-wrap line-clamp-3">
                      {ch.content}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

