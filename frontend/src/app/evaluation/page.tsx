"use client";

import React, { useState, useEffect } from "react";
import {
  CheckSquare,
  Play,
  Layers,
  GitCompare,
  Upload,
  AlertTriangle,
  CheckCircle,
  XCircle,
  FileText,
  Clock,
  Shield,
  Search,
  ChevronDown,
  ChevronRight,
  Info,
  RefreshCw,
  Copy,
  Download,
  Flame,
  Zap,
  Bookmark,
  Split,
  Crosshair,
  PenTool,
} from "lucide-react";
import {
  api,
  EvalSuiteItem,
  EvalSuiteDetail,
  EvalItemModel,
  EvalRunItem,
  RunReport,
  CompareRunsResult,
  LintReport,
  SourceItem,
  PipelineConfigItem,
  TextUnitItem,
} from "@/lib/api";

export default function EvaluationPage() {
  const [activeTab, setActiveTab] = useState<"suites" | "runner" | "scorecard" | "compare" | "builder">("suites");

  // Suites state
  const [suites, setSuites] = useState<EvalSuiteItem[]>([]);
  const [selectedSuiteId, setSelectedSuiteId] = useState<number | null>(null);
  const [suiteDetail, setSuiteDetail] = useState<EvalSuiteDetail | null>(null);
  const [lintReport, setLintReport] = useState<LintReport | null>(null);
  const [isLintDrawerOpen, setIsLintDrawerOpen] = useState<boolean>(false);
  const [loadingSuites, setLoadingSuites] = useState<boolean>(false);

  // Split control state
  const [holdoutFraction, setHoldoutFraction] = useState<number>(0.3);
  const [splitSeed, setSplitSeed] = useState<number>(42);
  const [splittingSuite, setSplittingSuite] = useState<boolean>(false);
  const [isSplitModalOpen, setIsSplitModalOpen] = useState<boolean>(false);

  // Sources & Pipeline configs
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [pipelineConfigs, setPipelineConfigs] = useState<PipelineConfigItem[]>([]);

  // Runs state
  const [runs, setRuns] = useState<EvalRunItem[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [runReport, setRunReport] = useState<RunReport | null>(null);
  const [loadingReport, setLoadingReport] = useState<boolean>(false);
  const [scorecardSplit, setScorecardSplit] = useState<"all" | "dev" | "holdout">("all");

  // Compare state
  const [compareRunA, setCompareRunA] = useState<number | null>(null);
  const [compareRunB, setCompareRunB] = useState<number | null>(null);
  const [compareSplit, setCompareSplit] = useState<"all" | "dev" | "holdout">("all");
  const [compareResult, setCompareResult] = useState<CompareRunsResult | null>(null);
  const [loadingCompare, setLoadingCompare] = useState<boolean>(false);

  // Gold Set Builder state
  const [builderSuiteId, setBuilderSuiteId] = useState<number | null>(null);
  const [builderSourceId, setBuilderSourceId] = useState<number | null>(null);
  const [builderVersion, setBuilderVersion] = useState<number | undefined>(undefined);
  const [builderPage, setBuilderPage] = useState<number>(1);
  const [textUnits, setTextUnits] = useState<TextUnitItem[]>([]);
  const [totalUnits, setTotalUnits] = useState<number>(0);
  const [loadingUnits, setLoadingUnits] = useState<boolean>(false);
  const [selectedUnit, setSelectedUnit] = useState<TextUnitItem | null>(null);
  const [builderQuestion, setBuilderQuestion] = useState<string>("");
  const [builderItemType, setBuilderItemType] = useState<string>("answerable");
  const [builderExpectedRoute, setBuilderExpectedRoute] = useState<string>("semantic");
  const [builderSelectedSpan, setBuilderSelectedSpan] = useState<string>("");
  const [builderFacts, setBuilderFacts] = useState<string>("");
  const [builderReferenceAnswer, setBuilderReferenceAnswer] = useState<string>("");
  const [builderRowKey, setBuilderRowKey] = useState<string>("");
  const [savingItem, setSavingItem] = useState<boolean>(false);
  const [builderValidationStatus, setBuilderValidationStatus] = useState<{ status: number; message: string; details?: any } | null>(null);

  // Single Variant Runner Form State
  const [runnerSuiteId, setRunnerSuiteId] = useState<number>(1);
  const [runnerName, setRunnerName] = useState<string>("");
  const [strategy, setStrategy] = useState<string>("dense");
  const [chunkSize, setChunkSize] = useState<number>(800);
  const [chunkOverlap, setChunkOverlap] = useState<number>(100);
  const [topK, setTopK] = useState<number>(5);
  const [useRerank, setUseRerank] = useState<boolean>(false);
  const [rerankModel, setRerankModel] = useState<string>("cross-encoder/ms-marco-MiniLM-L-6-v2");
  const [useHyde, setUseHyde] = useState<boolean>(false);
  const [pipelineConfigId, setPipelineConfigId] = useState<string>("");
  const [generate, setGenerate] = useState<boolean>(false);
  const [judge, setJudge] = useState<boolean>(false);
  const [includeUnreviewed, setIncludeUnreviewed] = useState<boolean>(true);
  const [maxLlmCalls, setMaxLlmCalls] = useState<number>(0);
  const [submittingRun, setSubmittingRun] = useState<boolean>(false);

  // Matrix Sweep Launcher State
  const [matrixStrategies, setMatrixStrategies] = useState<string[]>(["dense", "hybrid"]);
  const [matrixChunkSizes, setMatrixChunkSizes] = useState<number[]>([400, 800]);
  const [matrixTopKs, setMatrixTopKs] = useState<number[]>([3, 5]);
  const [matrixGenerate, setMatrixGenerate] = useState<boolean>(false);
  const [matrixJudge, setMatrixJudge] = useState<boolean>(false);
  const [matrixIncludeUnreviewed, setMatrixIncludeUnreviewed] = useState<boolean>(true);
  const [matrixMaxLlmCalls, setMatrixMaxLlmCalls] = useState<number>(0);
  const [submittingMatrix, setSubmittingMatrix] = useState<boolean>(false);

  // Expandable failure items in scorecard
  const [expandedFailures, setExpandedFailures] = useState<Record<number, boolean>>({});

  // Message notifications
  const [notification, setNotification] = useState<{ type: "success" | "error" | "info"; msg: string } | null>(null);

  // Load initial data
  useEffect(() => {
    loadAllData();
  }, []);

  async function loadAllData() {
    setLoadingSuites(true);
    try {
      const [sList, rList, srcList, cfgList] = await Promise.all([
        api.getEvalSuites(),
        api.getEvalRuns(),
        api.getSources(),
        api.getPipelineConfigs().catch(() => []),
      ]);
      setSuites(sList);
      setRuns(rList);
      setSources(srcList);
      setPipelineConfigs(cfgList);

      if (sList.length > 0) {
        setSelectedSuiteId(sList[0].id);
        setRunnerSuiteId(sList[0].id);
        setBuilderSuiteId(sList[0].id);
        loadSuiteDetail(sList[0].id);
      }
      if (srcList.length > 0) {
        setBuilderSourceId(srcList[0].id);
        loadTextUnits(srcList[0].id, undefined, 1);
      }
      if (rList.length > 0) {
        setSelectedRunId(rList[0].id);
        loadRunReport(rList[0].id);
        if (rList.length >= 2) {
          setCompareRunA(rList[0].id);
          setCompareRunB(rList[1].id);
        }
      }
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message || "Failed to load evaluation data" });
    } finally {
      setLoadingSuites(false);
    }
  }

  async function loadSuiteDetail(id: number) {
    try {
      const det = await api.getEvalSuite(id);
      setSuiteDetail(det);
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message });
    }
  }

  async function handleSplitSuite(suiteId: number) {
    setSplittingSuite(true);
    try {
      const res = await api.splitEvalSuite(suiteId, holdoutFraction, splitSeed);
      setNotification({
        type: "success",
        msg: `Deterministic split established: ${res.dev_count} dev, ${res.holdout_count} holdout (total: ${res.total}, seed: ${res.seed})`,
      });
      setIsSplitModalOpen(false);
      await loadSuiteDetail(suiteId);
      const sList = await api.getEvalSuites();
      setSuites(sList);
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message || "Failed to split suite" });
    } finally {
      setSplittingSuite(false);
    }
  }

  async function loadTextUnits(sourceId: number, versionNo?: number, page: number = 1) {
    setLoadingUnits(true);
    try {
      const raw = (await api.getTextUnits(sourceId, versionNo, page)) as any;
      const list: TextUnitItem[] = Array.isArray(raw) ? raw : (raw?.units || []);
      setTextUnits(list);
      setTotalUnits(Array.isArray(raw) ? list.length : (raw?.total_units || list.length));
      setBuilderPage(page);
      if (list.length > 0) {
        setSelectedUnit(list[0]);
        if (list[0].row_key) {
          setBuilderRowKey(list[0].row_key);
        }
      }
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message || "Failed to load text units" });
    } finally {
      setLoadingUnits(false);
    }
  }

  function handleCaptureSelection() {
    const sel = window.getSelection();
    const str = sel ? sel.toString().trim() : "";
    if (!str) {
      setNotification({ type: "info", msg: "Highlight text inside the text unit display to capture verbatim span." });
      return;
    }
    if (selectedUnit && !selectedUnit.text.includes(str)) {
      setNotification({ type: "error", msg: "Selection must occur verbatim in the active text unit." });
      return;
    }
    setBuilderSelectedSpan(str);
    setNotification({ type: "success", msg: `Captured verbatim span (${str.length} chars).` });
  }

  async function handleCreateGoldItem(e: React.FormEvent) {
    e.preventDefault();
    if (!builderSuiteId) {
      setNotification({ type: "error", msg: "Select a draft suite first." });
      return;
    }
    if (!builderQuestion.trim()) {
      setNotification({ type: "error", msg: "Question cannot be empty." });
      return;
    }
    setSavingItem(true);
    setBuilderValidationStatus(null);

    const rawFacts = builderFacts.split(",").map((f) => f.trim()).filter(Boolean);
    const evidenceList: any[] = [];
    if (selectedUnit) {
      evidenceList.push({
        unit_id: selectedUnit.unit_id,
        span: builderSelectedSpan || undefined,
        document_id: selectedUnit.source_type === "document" ? selectedUnit.source_id : undefined,
        page_number: selectedUnit.page_number,
        row_key: builderRowKey || selectedUnit.row_key,
      });
    }

    const payload = {
      question: builderQuestion.trim(),
      item_type: builderItemType,
      expected_route: builderExpectedRoute,
      expected_facts: rawFacts,
      reference_answer: builderReferenceAnswer.trim() || undefined,
      expected_evidence: evidenceList,
      expected_value: builderItemType === "structured" ? builderReferenceAnswer.trim() : undefined,
    };

    try {
      const res = await api.createEvalItem(builderSuiteId, payload);
      setBuilderValidationStatus({
        status: 201,
        message: `Successfully created Test Case #${res.id}. Verbatim span verified against ${selectedUnit?.unit_id || "source"}.`,
        details: res,
      });
      setNotification({ type: "success", msg: `Created Test Case #${res.id} in Suite #${builderSuiteId}.` });
      setBuilderQuestion("");
      setBuilderSelectedSpan("");
      setBuilderFacts("");
      setBuilderReferenceAnswer("");
      if (selectedSuiteId === builderSuiteId) {
        loadSuiteDetail(builderSuiteId);
      }
    } catch (err: any) {
      let code = 422;
      if (err.message && err.message.includes("409")) code = 409;
      if (err.message && err.message.includes("422")) code = 422;
      setBuilderValidationStatus({
        status: code,
        message: err.message || "Validation failed: expected span does not occur verbatim or suite is frozen.",
      });
      setNotification({ type: "error", msg: err.message });
    } finally {
      setSavingItem(false);
    }
  }

  async function handleRunLint(id: number) {
    try {
      setNotification({ type: "info", msg: "Running label lint checks on corpus..." });
      const lr = await api.lintEvalSuite(id);
      setLintReport(lr);
      setIsLintDrawerOpen(true);
      setNotification({
        type: "success",
        msg: `Lint completed: ${lr.lint_failed_count} item(s) flagged out of ${lr.total_items}`,
      });
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message });
    }
  }

  async function handleReviewToggle(itemId: number, currentReviewed: boolean) {
    try {
      await api.reviewEvalItem(itemId, !currentReviewed);
      if (suiteDetail) {
        setSuiteDetail({
          ...suiteDetail,
          items: suiteDetail.items.map((it) =>
            it.id === itemId ? { ...it, reviewed: !currentReviewed } : it
          ),
        });
      }
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message });
    }
  }

  async function loadRunReport(id: number, split?: "all" | "dev" | "holdout") {
    setLoadingReport(true);
    try {
      const sp = split !== undefined ? split : scorecardSplit;
      const rep = await api.getEvalRunReport(id, sp);
      setRunReport(rep);
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message });
    } finally {
      setLoadingReport(false);
    }
  }

  async function handleExecuteRun(e: React.FormEvent) {
    e.preventDefault();
    setSubmittingRun(true);
    try {
      const variant: Record<string, any> = {
        strategy,
        chunk_size: Number(chunkSize),
        chunk_overlap: Number(chunkOverlap),
        top_k: Number(topK),
        use_rerank: useRerank,
        rerank_model: useRerank ? rerankModel : undefined,
        use_hyde: useHyde,
      };
      if (pipelineConfigId) {
        variant.pipeline_config_id = Number(pipelineConfigId);
      }

      const res = await api.createEvalRun({
        suite_id: runnerSuiteId,
        name: runnerName.trim() || undefined,
        variant,
        generate,
        judge,
        include_unreviewed: includeUnreviewed,
        max_llm_calls: maxLlmCalls > 0 ? maxLlmCalls : undefined,
        wait: true, // synchronous demo wait
      });

      setNotification({ type: "success", msg: `EvalRun #${res.id} completed.` });
      const rList = await api.getEvalRuns();
      setRuns(rList);
      setSelectedRunId(res.id);
      loadRunReport(res.id);
      setActiveTab("scorecard");
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message });
    } finally {
      setSubmittingRun(false);
    }
  }

  // Calculate Cartesian Product count for matrix
  const matrixCount = matrixStrategies.length * matrixChunkSizes.length * matrixTopKs.length;
  const isMatrixCapped = matrixCount > 24;

  async function handleExecuteMatrix(e: React.FormEvent) {
    e.preventDefault();
    if (isMatrixCapped || matrixCount === 0) return;
    setSubmittingMatrix(true);
    try {
      const res = await api.createEvalMatrix({
        suite_id: runnerSuiteId,
        base_variant: { use_rerank: false },
        vary: {
          strategy: matrixStrategies,
          chunk_size: matrixChunkSizes,
          top_k: matrixTopKs,
        },
        generate: matrixGenerate,
        judge: matrixJudge,
        include_unreviewed: matrixIncludeUnreviewed,
        max_llm_calls: matrixMaxLlmCalls > 0 ? matrixMaxLlmCalls : undefined,
        wait: true,
      });

      setNotification({
        type: "success",
        msg: `Matrix sweep executed successfully: ${res.runs_created} runs created.`,
      });
      const rList = await api.getEvalRuns();
      setRuns(rList);
      if (res.run_ids.length > 0) {
        setSelectedRunId(res.run_ids[0]);
        loadRunReport(res.run_ids[0]);
      }
      setActiveTab("scorecard");
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message });
    } finally {
      setSubmittingMatrix(false);
    }
  }

  async function handleCompare(split?: "all" | "dev" | "holdout") {
    if (!compareRunA || !compareRunB || compareRunA === compareRunB) return;
    setLoadingCompare(true);
    try {
      const sp = split !== undefined ? split : compareSplit;
      const res = await api.compareEvalRuns(compareRunA, compareRunB, sp);
      setCompareResult(res);
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message });
    } finally {
      setLoadingCompare(false);
    }
  }

  async function handleDownloadMarkdown(runId: number) {
    try {
      const md = await api.getReportMarkdown(String(runId));
      const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `locus_eval_scorecard_run_${runId}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setNotification({ type: "error", msg: err.message });
    }
  }

  return (
    <div className="flex-1 bg-obsidian text-fg min-h-screen flex flex-col font-mono text-xs">
      {/* Top Header */}
      <div className="h-16 px-6 border-b border-graphite bg-carbon flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-electric/10 border border-electric/30 flex items-center justify-center text-electric">
            <CheckSquare className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-fg font-heading tracking-tight">Quantitative Evaluation Studio</h1>
            <p className="text-[11px] text-muted">Offline benchmark suites, matrix parameter sweeps & statistical paired bootstrap</p>
          </div>
        </div>

        {/* View Switcher (Horizontally scrollable on mobile) */}
        <div className="flex items-center gap-1 bg-graphite/40 p-1 rounded-lg border border-graphite overflow-x-auto whitespace-nowrap max-w-full">
          <button
            onClick={() => setActiveTab("suites")}
            className={`px-3 py-1.5 rounded text-xs transition-colors ${
              activeTab === "suites" ? "bg-slate text-electric font-semibold border border-electric/40" : "text-muted hover:text-fg"
            }`}
          >
            Benchmark Suites
          </button>
          <button
            onClick={() => setActiveTab("runner")}
            className={`px-3 py-1.5 rounded text-xs transition-colors ${
              activeTab === "runner" ? "bg-slate text-electric font-semibold border border-electric/40" : "text-muted hover:text-fg"
            }`}
          >
            Variant & Matrix Runner
          </button>
          <button
            onClick={() => setActiveTab("scorecard")}
            className={`px-3 py-1.5 rounded text-xs transition-colors ${
              activeTab === "scorecard" ? "bg-slate text-electric font-semibold border border-electric/40" : "text-muted hover:text-fg"
            }`}
          >
            Run Scorecard ({runs.length})
          </button>
          <button
            onClick={() => {
              setActiveTab("compare");
              if (compareRunA && compareRunB && !compareResult) {
                handleCompare();
              }
            }}
            className={`px-3 py-1.5 rounded text-xs transition-colors ${
              activeTab === "compare" ? "bg-slate text-electric font-semibold border border-electric/40" : "text-muted hover:text-fg"
            }`}
          >
            Paired Comparison
          </button>
          <button
            onClick={() => {
              setActiveTab("builder");
              if (builderSourceId && textUnits.length === 0) {
                loadTextUnits(builderSourceId, builderVersion, 1);
              }
            }}
            className={`px-3 py-1.5 rounded text-xs transition-colors ${
              activeTab === "builder" ? "bg-slate text-electric font-semibold border border-electric/40" : "text-muted hover:text-fg"
            }`}
          >
            Gold Set Builder
          </button>
        </div>
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

      {/* Main Workspace Body */}
      <div className="flex-1 p-6 space-y-6 overflow-y-auto">
        {/* ==================================================================== */}
        {/* TAB 1: SUITES & BENCHMARKS */}
        {/* ==================================================================== */}
        {activeTab === "suites" && (
          <div className="space-y-6">
            {/* Suites Selector & Controls */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {suites.map((s) => (
                <div
                  key={s.id}
                  onClick={() => {
                    setSelectedSuiteId(s.id);
                    setRunnerSuiteId(s.id);
                    loadSuiteDetail(s.id);
                  }}
                  className={`p-4 rounded-lg border cursor-pointer transition-all ${
                    selectedSuiteId === s.id
                      ? "bg-carbon border-electric/60 shadow-sm"
                      : "bg-carbon/50 border-graphite hover:border-graphite/80"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-fg text-sm">{s.name}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] ${s.is_frozen ? "bg-amber/10 text-amber border border-amber/30" : "bg-emerald/10 text-emerald border border-emerald/30"}`}>
                      {s.is_frozen ? "Frozen (Executed)" : "Draft"}
                    </span>
                  </div>
                  <p className="text-muted text-[11px] line-clamp-2 mb-3">{s.description || "No description provided."}</p>
                  <div className="grid grid-cols-2 gap-2 text-[10px] text-muted border-t border-graphite/50 pt-2">
                    <div>Items: <span className="text-fg font-mono">{s.item_count}</span></div>
                    <div>Runs Executed: <span className="text-fg font-mono">{s.run_count}</span></div>
                    <div className="col-span-2 truncate">Hash: <span className="text-muted/80 font-mono">{s.suite_hash || "Not frozen"}</span></div>
                  </div>
                </div>
              ))}
            </div>

            {/* Active Suite Details & Label Inspector */}
            {suiteDetail && (
              <div className="bg-carbon rounded-lg border border-graphite p-6 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-graphite pb-4">
                  <div>
                    <h2 className="text-base font-bold text-fg flex items-center gap-2">
                      <span>{suiteDetail.name}</span>
                      <span className="text-xs text-muted font-normal">({suiteDetail.items.length} items)</span>
                    </h2>
                    <div className="flex items-center gap-3 text-muted text-[11px] mt-1">
                      <span>Suite Hash: <code className="text-electric">{suiteDetail.suite_hash}</code></span>
                      <span>•</span>
                      <span>Sources: {suiteDetail.source_ids.join(", ")}</span>
                      <span>•</span>
                      <span>Reviewed: {suiteDetail.items.filter((it) => it.reviewed).length} / {suiteDetail.items.length}</span>
                      <span>•</span>
                      <span>Split: {suiteDetail.items.filter((it) => it.split === "dev").length} dev / {suiteDetail.items.filter((it) => it.split === "holdout").length} holdout</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setIsSplitModalOpen(!isSplitModalOpen)}
                      disabled={suiteDetail.is_frozen}
                      className="px-3 py-1.5 bg-slate hover:bg-slate/80 text-fg rounded border border-graphite flex items-center gap-2 transition-colors disabled:opacity-50"
                      title={suiteDetail.is_frozen ? "Split can only be established before first run" : "Deterministic hash-based stratified split"}
                    >
                      <Split className="w-3.5 h-3.5 text-electric" />
                      <span>Partition (Dev / Holdout)</span>
                    </button>
                    <button
                      onClick={() => handleRunLint(suiteDetail.id)}
                      className="px-3 py-1.5 bg-slate hover:bg-slate/80 text-fg rounded border border-graphite flex items-center gap-2 transition-colors"
                    >
                      <Shield className="w-3.5 h-3.5 text-amber" />
                      <span>Lint Suite Labels</span>
                    </button>
                    <label className="px-3 py-1.5 bg-slate hover:bg-slate/80 text-fg rounded border border-graphite flex items-center gap-2 cursor-pointer transition-colors">
                      <Upload className="w-3.5 h-3.5 text-electric" />
                      <span>Import CSV</span>
                      <input
                        type="file"
                        accept=".csv"
                        className="hidden"
                        onChange={async (e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            try {
                              const res = await api.uploadSuiteItemsCsv(suiteDetail.id, file);
                              setNotification({ type: "success", msg: `Imported ${res.imported_count} items from CSV.` });
                              loadSuiteDetail(suiteDetail.id);
                            } catch (err: any) {
                              setNotification({ type: "error", msg: err.message });
                            }
                          }
                        }}
                      />
                    </label>
                  </div>
                </div>

                {/* Partition Drawer / Modal */}
                {isSplitModalOpen && (
                  <div className="p-4 bg-obsidian border border-electric/40 rounded-lg space-y-3">
                    <div className="flex items-center justify-between border-b border-graphite pb-2">
                      <span className="font-bold text-fg text-xs flex items-center gap-2">
                        <Split className="w-4 h-4 text-electric" />
                        <span>Deterministic Hash-Based Stratified Split (Dev / Holdout)</span>
                      </span>
                      <span className="text-[10px] text-muted">Allowed strictly before the first eval run</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                      <div>
                        <label className="block text-[10px] text-muted mb-1">Holdout Fraction (e.g. 0.30 for 30%)</label>
                        <input
                          type="number"
                          step="0.05"
                          min="0.1"
                          max="0.5"
                          value={holdoutFraction}
                          onChange={(e) => setHoldoutFraction(parseFloat(e.target.value))}
                          className="w-full bg-slate border border-graphite rounded px-3 py-1.5 text-fg text-xs font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] text-muted mb-1">Deterministic Seed</label>
                        <input
                          type="number"
                          value={splitSeed}
                          onChange={(e) => setSplitSeed(parseInt(e.target.value))}
                          className="w-full bg-slate border border-graphite rounded px-3 py-1.5 text-fg text-xs font-mono"
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleSplitSuite(suiteDetail.id)}
                          disabled={splittingSuite}
                          className="flex-1 py-1.5 px-3 bg-electric hover:bg-electric/90 text-obsidian font-bold rounded flex items-center justify-center gap-2 text-xs transition-colors disabled:opacity-50"
                        >
                          {splittingSuite ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Split className="w-3.5 h-3.5" />}
                          <span>Execute Partition</span>
                        </button>
                        <button
                          onClick={() => setIsSplitModalOpen(false)}
                          className="py-1.5 px-3 bg-slate text-muted hover:text-fg rounded border border-graphite text-xs"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Items Table */}
                <div className="overflow-x-auto border border-graphite rounded-lg">
                  <table className="w-full text-left border-collapse">
                    <thead className="bg-slate/50 text-muted text-[11px] border-b border-graphite">
                      <tr>
                        <th className="py-2.5 px-3 w-12 text-center">Pos</th>
                        <th className="py-2.5 px-3 w-28">Type</th>
                        <th className="py-2.5 px-3 w-20 text-center">Split</th>
                        <th className="py-2.5 px-3">Question & Expected Evidence</th>
                        <th className="py-2.5 px-3 w-28">Route</th>
                        <th className="py-2.5 px-3 w-24">Origin</th>
                        <th className="py-2.5 px-3 w-20 text-center">Reviewed</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-graphite/40 text-[11px]">
                      {suiteDetail.items.map((it) => (
                        <tr key={it.id} className="hover:bg-slate/20 transition-colors">
                          <td className="py-2.5 px-3 text-center text-muted font-mono">{it.position}</td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] ${
                                it.item_type === "answerable"
                                  ? "bg-emerald/10 text-emerald border border-emerald/30"
                                  : it.item_type === "unanswerable"
                                  ? "bg-crimson/10 text-crimson border border-crimson/30"
                                  : "bg-electric/10 text-electric border border-electric/30"
                              }`}
                            >
                              {it.item_type}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-mono ${
                                it.split === "dev"
                                  ? "bg-electric/15 text-electric border border-electric/30"
                                  : it.split === "holdout"
                                  ? "bg-purple-500/15 text-purple-400 border border-purple-500/30"
                                  : "bg-slate text-muted"
                              }`}
                            >
                              {it.split || "none"}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 space-y-1">
                            <div className="text-fg font-medium">{it.question}</div>
                            {it.expected_facts && it.expected_facts.length > 0 && (
                              <div className="text-muted text-[10px]">
                                Expected Facts: <span className="text-fg/80">{it.expected_facts.join(", ")}</span>
                              </div>
                            )}
                            {it.expected_evidence && it.expected_evidence.length > 0 && (
                              <div className="text-muted/70 text-[10px] truncate max-w-xl">
                                Span: <span className="font-mono text-muted/90">{it.expected_evidence[0].span || "N/A"}</span>
                              </div>
                            )}
                          </td>
                          <td className="py-2.5 px-3 font-mono text-muted">{it.expected_route || "auto"}</td>
                          <td className="py-2.5 px-3 font-mono text-muted/80">{it.origin}</td>
                          <td className="py-2.5 px-3 text-center">
                            <input
                              type="checkbox"
                              checked={it.reviewed}
                              onChange={() => handleReviewToggle(it.id, it.reviewed)}
                              className="w-3.5 h-3.5 rounded bg-carbon border-graphite accent-electric cursor-pointer"
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Lint Results Drawer */}
            {isLintDrawerOpen && lintReport && (
              <div className="bg-carbon rounded-lg border border-amber/40 p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-graphite pb-3">
                  <div className="flex items-center gap-2">
                    <Shield className="w-5 h-5 text-amber" />
                    <h3 className="text-sm font-bold text-fg">Corpus Grounding & Label Lint Report</h3>
                    <span className="px-2 py-0.5 rounded text-[10px] bg-amber/10 text-amber border border-amber/30">
                      {lintReport.lint_failed_count} failing items / {lintReport.total_items} total
                    </span>
                  </div>
                  <button
                    onClick={() => setIsLintDrawerOpen(false)}
                    className="text-muted hover:text-fg text-xs px-2 py-1 rounded hover:bg-slate"
                  >
                    Close Drawer ✕
                  </button>
                </div>

                <div className="space-y-3">
                  {lintReport.items.map((it) => (
                    <div
                      key={it.item_id}
                      className={`p-3 rounded border text-xs ${
                        it.lint_failed
                          ? "bg-crimson/5 border-crimson/40 text-fg"
                          : "bg-slate/30 border-graphite text-muted"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold">
                          Item #{it.position}: {it.question}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] ${
                            it.lint_failed ? "bg-crimson/20 text-crimson font-bold" : "bg-emerald/10 text-emerald"
                          }`}
                        >
                          {it.lint_failed ? "LINT FAILED" : "PASSED"}
                        </span>
                      </div>

                      {it.lint_failed && (
                        <div className="mt-2 space-y-1">
                          {it.failures.map((f, idx) => (
                            <div key={idx} className="flex items-center gap-2 text-crimson text-[11px]">
                              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                              <span>{f}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {it.span_checks && it.span_checks.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-graphite/40 text-[10px] text-muted space-y-1">
                          {it.span_checks.map((sc, sidx) => (
                            <div key={sidx} className="flex items-center justify-between">
                              <span className="truncate max-w-md">Span: &ldquo;{sc.span}&rdquo;</span>
                              <span className="font-mono">
                                Overlap: {(sc.best_overlap * 100).toFixed(1)}% | Docs: {sc.matching_doc_count}
                                {sc.ambiguous && " (AMBIGUOUS)"}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================================================================== */}
        {/* TAB 2: VARIANT RUNNER & MATRIX SWEEP */}
        {/* ==================================================================== */}
        {activeTab === "runner" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Single Variant Runner */}
            <div className="bg-carbon rounded-lg border border-graphite p-6 space-y-4">
              <div className="border-b border-graphite pb-3">
                <h2 className="text-sm font-bold text-fg flex items-center gap-2">
                  <Play className="w-4 h-4 text-electric" />
                  <span>Execute Single Variant Evaluation</span>
                </h2>
                <p className="text-muted text-[11px] mt-1">Runs internal retrieval / generation against benchmark suite without HTTP overhead.</p>
              </div>

              <form onSubmit={handleExecuteRun} className="space-y-4">
                <div>
                  <label className="block text-[11px] text-muted mb-1">Target Suite</label>
                  <select
                    value={runnerSuiteId}
                    onChange={(e) => setRunnerSuiteId(Number(e.target.value))}
                    className="w-full bg-slate border border-graphite rounded px-3 py-2 text-fg text-xs focus:outline-none focus:border-electric"
                  >
                    {suites.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.item_count} items)
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] text-muted mb-1">Run Name (Optional)</label>
                  <input
                    type="text"
                    value={runnerName}
                    onChange={(e) => setRunnerName(e.target.value)}
                    placeholder="e.g. dense_topk5_k800"
                    className="w-full bg-slate border border-graphite rounded px-3 py-2 text-fg text-xs focus:outline-none focus:border-electric"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] text-muted mb-1">Retrieval Strategy</label>
                    <select
                      value={strategy}
                      onChange={(e) => setStrategy(e.target.value)}
                      className="w-full bg-slate border border-graphite rounded px-3 py-2 text-fg text-xs focus:outline-none focus:border-electric"
                    >
                      <option value="dense">dense (Vector Cosine)</option>
                      <option value="hybrid">hybrid (Vector + BM25 RRF)</option>
                      <option value="sparse">sparse (BM25 only)</option>
                      <option value="auto">auto (Intent Classifier)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] text-muted mb-1">Top K Chunks</label>
                    <input
                      type="number"
                      value={topK}
                      onChange={(e) => setTopK(Number(e.target.value))}
                      min={1}
                      max={50}
                      className="w-full bg-slate border border-graphite rounded px-3 py-2 text-fg text-xs focus:outline-none focus:border-electric"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] text-muted mb-1">Chunk Size</label>
                    <input
                      type="number"
                      value={chunkSize}
                      onChange={(e) => setChunkSize(Number(e.target.value))}
                      className="w-full bg-slate border border-graphite rounded px-3 py-2 text-fg text-xs focus:outline-none focus:border-electric"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] text-muted mb-1">Chunk Overlap</label>
                    <input
                      type="number"
                      value={chunkOverlap}
                      onChange={(e) => setChunkOverlap(Number(e.target.value))}
                      className="w-full bg-slate border border-graphite rounded px-3 py-2 text-fg text-xs focus:outline-none focus:border-electric"
                    />
                  </div>
                </div>

                <div className="space-y-2 border-t border-graphite/50 pt-3">
                  <label className="flex items-center gap-2 text-muted hover:text-fg cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useRerank}
                      onChange={(e) => setUseRerank(e.target.checked)}
                      className="rounded bg-carbon border-graphite accent-electric"
                    />
                    <span>Enable Cross-Encoder Reranker</span>
                  </label>

                  <label className="flex items-center gap-2 text-muted hover:text-fg cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeUnreviewed}
                      onChange={(e) => setIncludeUnreviewed(e.target.checked)}
                      className="rounded bg-carbon border-graphite accent-electric"
                    />
                    <span>Include Unreviewed Items in Evaluation</span>
                  </label>
                </div>

                <div className="p-3 bg-slate/40 rounded border border-graphite space-y-2">
                  <div className="text-[11px] font-semibold text-fg">LLM Generation & Judge (Default: OFF)</div>
                  <div className="grid grid-cols-2 gap-2">
                    <label className="flex items-center gap-2 text-muted text-[11px] cursor-pointer">
                      <input
                        type="checkbox"
                        checked={generate}
                        onChange={(e) => setGenerate(e.target.checked)}
                        className="rounded bg-carbon border-graphite accent-electric"
                      />
                      <span>Generate Answers</span>
                    </label>

                    <label className="flex items-center gap-2 text-muted text-[11px] cursor-pointer">
                      <input
                        type="checkbox"
                        checked={judge}
                        onChange={(e) => setJudge(e.target.checked)}
                        className="rounded bg-carbon border-graphite accent-electric"
                      />
                      <span>Run LLM Judge</span>
                    </label>
                  </div>

                  {(generate || judge) && (
                    <div className="mt-2 pt-2 border-t border-graphite/40">
                      <label className="block text-[10px] text-muted mb-1">Max LLM Budget Cap (Strict Enforced)</label>
                      <input
                        type="number"
                        value={maxLlmCalls}
                        onChange={(e) => setMaxLlmCalls(Number(e.target.value))}
                        placeholder="0 for unlimited"
                        className="w-full bg-carbon border border-graphite rounded px-2 py-1 text-fg text-xs font-mono"
                      />
                    </div>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={submittingRun}
                  className="w-full py-2.5 bg-electric hover:bg-electric/90 text-obsidian font-bold rounded flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                >
                  {submittingRun ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  <span>{submittingRun ? "Executing Evaluation..." : "Execute Evaluation Run"}</span>
                </button>
              </form>
            </div>

            {/* Matrix Parameter Sweep Launcher */}
            <div className="bg-carbon rounded-lg border border-graphite p-6 space-y-4">
              <div className="border-b border-graphite pb-3">
                <h2 className="text-sm font-bold text-fg flex items-center gap-2">
                  <Layers className="w-4 h-4 text-emerald" />
                  <span>Parameter Sweep Matrix Launcher</span>
                </h2>
                <p className="text-muted text-[11px] mt-1">Multi-variant Cartesian sweep with hard safety cap (max 24 runs).</p>
              </div>

              <form onSubmit={handleExecuteMatrix} className="space-y-4">
                <div>
                  <label className="block text-[11px] text-muted mb-1">Select Strategies</label>
                  <div className="grid grid-cols-2 gap-2">
                    {["dense", "hybrid", "sparse", "auto"].map((st) => (
                      <label key={st} className="flex items-center gap-2 p-2 rounded bg-slate border border-graphite cursor-pointer text-xs">
                        <input
                          type="checkbox"
                          checked={matrixStrategies.includes(st)}
                          onChange={(e) => {
                            if (e.target.checked) setMatrixStrategies([...matrixStrategies, st]);
                            else setMatrixStrategies(matrixStrategies.filter((s) => s !== st));
                          }}
                          className="rounded bg-carbon border-graphite accent-emerald"
                        />
                        <span>{st}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] text-muted mb-1">Select Chunk Sizes</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[400, 600, 800].map((cs) => (
                      <label key={cs} className="flex items-center gap-2 p-2 rounded bg-slate border border-graphite cursor-pointer text-xs">
                        <input
                          type="checkbox"
                          checked={matrixChunkSizes.includes(cs)}
                          onChange={(e) => {
                            if (e.target.checked) setMatrixChunkSizes([...matrixChunkSizes, cs]);
                            else setMatrixChunkSizes(matrixChunkSizes.filter((c) => c !== cs));
                          }}
                          className="rounded bg-carbon border-graphite accent-emerald"
                        />
                        <span>{cs} chars</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] text-muted mb-1">Select Top K</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[3, 5, 10].map((tk) => (
                      <label key={tk} className="flex items-center gap-2 p-2 rounded bg-slate border border-graphite cursor-pointer text-xs">
                        <input
                          type="checkbox"
                          checked={matrixTopKs.includes(tk)}
                          onChange={(e) => {
                            if (e.target.checked) setMatrixTopKs([...matrixTopKs, tk]);
                            else setMatrixTopKs(matrixTopKs.filter((t) => t !== tk));
                          }}
                          className="rounded bg-carbon border-graphite accent-emerald"
                        />
                        <span>top_k={tk}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Cartesian product preview */}
                <div
                  className={`p-3 rounded border text-xs flex items-center justify-between ${
                    isMatrixCapped
                      ? "bg-crimson/10 border-crimson/40 text-crimson"
                      : "bg-slate/50 border-graphite text-muted"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Info className="w-4 h-4 text-fg" />
                    <span>Total Runs in Matrix: <strong className="text-fg">{matrixCount}</strong></span>
                  </div>
                  <span className="font-mono text-[10px]">
                    {matrixStrategies.length} × {matrixChunkSizes.length} × {matrixTopKs.length} = {matrixCount}
                  </span>
                </div>

                {isMatrixCapped && (
                  <div className="text-crimson text-[11px] flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Matrix sweep exceeds maximum safety cap of 24 runs. Please reduce variant parameters.</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={submittingMatrix || isMatrixCapped || matrixCount === 0}
                  className="w-full py-2.5 bg-emerald hover:bg-emerald/90 text-obsidian font-bold rounded flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                >
                  {submittingMatrix ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Layers className="w-4 h-4" />}
                  <span>{submittingMatrix ? "Running Matrix Sweep..." : `Launch Matrix (${matrixCount} Runs)`}</span>
                </button>
              </form>
            </div>
          </div>
        )}

        {/* ==================================================================== */}
        {/* TAB 3: RUN SCORECARD & DETAILED REPORT */}
        {/* ==================================================================== */}
        {activeTab === "scorecard" && (
          <div className="space-y-6">
            {/* Run Selector & Split Filter */}
            <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-graphite">
              <div className="flex items-center gap-2 overflow-x-auto">
                {runs.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => {
                      setSelectedRunId(r.id);
                      loadRunReport(r.id, scorecardSplit);
                    }}
                    className={`px-3 py-1.5 rounded text-xs flex items-center gap-2 whitespace-nowrap transition-colors ${
                      selectedRunId === r.id
                        ? "bg-electric/20 text-electric border border-electric/50 font-bold"
                        : "bg-carbon border border-graphite text-muted hover:text-fg"
                    }`}
                  >
                    <span>Run #{r.id}</span>
                    <span className="text-[10px] text-muted font-normal">({r.variant.strategy || "auto"})</span>
                    <span className={`w-2 h-2 rounded-full ${r.status === "completed" ? "bg-emerald" : r.status === "failed" ? "bg-crimson" : "bg-amber"}`} />
                  </button>
                ))}
              </div>

              {/* Split Filter Toggle */}
              <div className="flex items-center gap-1 bg-slate/60 p-1 rounded border border-graphite">
                <span className="text-[10px] text-muted px-1.5 font-bold uppercase">Split:</span>
                {(["all", "dev", "holdout"] as const).map((sp) => (
                  <button
                    key={sp}
                    onClick={() => {
                      setScorecardSplit(sp);
                      if (selectedRunId) {
                        loadRunReport(selectedRunId, sp);
                      }
                    }}
                    className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase transition-colors ${
                      scorecardSplit === sp
                        ? "bg-electric text-obsidian font-bold"
                        : "text-muted hover:text-fg"
                    }`}
                  >
                    {sp}
                  </button>
                ))}
              </div>
            </div>

            {loadingReport && (
              <div className="py-12 text-center text-muted flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Computing statistical scorecards & bootstrap confidence intervals...</span>
              </div>
            )}

            {!loadingReport && runReport && (
              <div className="space-y-6">
                {/* STICKY DIAGNOSTIC BANNERS */}
                <div className="space-y-2">
                  {runReport.composition?.skew_banner && (
                    <div className="p-3 bg-amber/10 border border-amber/40 rounded text-amber text-xs font-semibold flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber" />
                      <span><strong>SUITE SKEW DETECTED:</strong> {runReport.composition.skew_banner} (labeled heuristic)</span>
                    </div>
                  )}

                  {runReport.banners?.dirty_tree && (
                    <div className="p-3 bg-amber/10 border border-amber/40 rounded text-amber text-xs flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                      <span><strong>DIRTY WORKING TREE:</strong> Results not reproducible from the commit hash alone. Working tree had uncommitted modifications.</span>
                    </div>
                  )}

                  {runReport.banners?.unreviewed_items && (
                    <div className="p-3 bg-slate/80 border border-graphite rounded text-fg text-xs flex items-center gap-2">
                      <Info className="w-4 h-4 flex-shrink-0 text-electric" />
                      <span><strong>UNREVIEWED ITEMS INCLUDED:</strong> Run includes items with <code>reviewed=false</code>.</span>
                    </div>
                  )}

                  {runReport.banners?.small_sample && (
                    <div className="p-3 bg-slate/80 border border-graphite rounded text-fg text-xs flex items-center gap-2">
                      <Info className="w-4 h-4 flex-shrink-0 text-amber" />
                      <span><strong>SMALL SAMPLE SIZE (n &lt; 30):</strong> Results have wider confidence intervals and high sample sensitivity.</span>
                    </div>
                  )}

                  {runReport.banners?.mock_llm && (
                    <div className="p-3 bg-crimson/10 border border-crimson/40 rounded text-crimson text-xs flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                      <span><strong>MOCK LLM GENERATION:</strong> Generation & judge metrics are INVALID for evaluation claims.</span>
                    </div>
                  )}

                  {runReport.banners?.llm_judged && (
                    <div className="p-3 bg-purple-500/10 border border-purple-500/40 rounded text-purple-300 text-xs flex items-center gap-2">
                      <Info className="w-4 h-4 flex-shrink-0 text-purple-400" />
                      <span><strong>LLM JUDGE ACTIVE:</strong> Quality judgements computed using external LLM evaluation.</span>
                    </div>
                  )}
                </div>

                {/* Scorecard Header & Actions */}
                <div className="flex flex-wrap items-center justify-between gap-4 bg-carbon p-4 rounded-lg border border-graphite">
                  <div>
                    <h2 className="text-base font-bold text-fg flex items-center gap-2">
                      <span>{runReport.run_name}</span>
                      <span className="text-xs text-muted font-normal">(Run ID #{runReport.run_id})</span>
                    </h2>
                    <div className="text-[11px] text-muted mt-1">
                      Status: <span className="text-emerald font-semibold uppercase">{runReport.status}</span> | Strategy: <code className="text-electric">{runReport.variant.strategy}</code> | Split Filter: <code className="text-electric uppercase">{scorecardSplit}</code> | Top K: <code className="text-fg">{runReport.variant.top_k}</code>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDownloadMarkdown(runReport.run_id)}
                    className="px-3 py-1.5 bg-slate hover:bg-slate/80 text-fg rounded border border-graphite flex items-center gap-2 transition-colors text-xs"
                  >
                    <Download className="w-3.5 h-3.5 text-electric" />
                    <span>Download Markdown Report</span>
                  </button>
                </div>

                {/* Suite Composition Panel */}
                {runReport.composition && (
                  <div className="bg-carbon rounded-lg border border-graphite p-4 space-y-3">
                    <div className="flex items-center justify-between border-b border-graphite/50 pb-2">
                      <span className="text-[11px] font-bold text-fg uppercase tracking-wider text-muted/70">
                        Suite Composition ({runReport.composition.total_items} items, Split: <span className="text-electric uppercase">{runReport.composition.split}</span>)
                      </span>
                      {runReport.composition.skew_banner && (
                        <span className="text-[10px] text-amber border border-amber/30 px-2 py-0.5 rounded bg-amber/5">
                          Skew &gt; 60%
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-[11px]">
                      <div className="p-2.5 rounded bg-slate/40 border border-graphite/40 space-y-1">
                        <div className="text-muted text-[10px] uppercase font-bold">Item Types</div>
                        {Object.entries(runReport.composition.item_types || {}).map(([type, cnt]) => (
                          <div key={type} className="flex justify-between">
                            <span className="capitalize text-muted">{type}:</span>
                            <span className="font-mono font-bold text-fg">{cnt}</span>
                          </div>
                        ))}
                      </div>
                      <div className="p-2.5 rounded bg-slate/40 border border-graphite/40 space-y-1">
                        <div className="text-muted text-[10px] uppercase font-bold">Expected Routes</div>
                        {Object.entries(runReport.composition.expected_routes || {}).map(([rt, cnt]) => (
                          <div key={rt} className="flex justify-between">
                            <span className="capitalize text-muted">{rt}:</span>
                            <span className="font-mono font-bold text-fg">{cnt}</span>
                          </div>
                        ))}
                      </div>
                      <div className="p-2.5 rounded bg-slate/40 border border-graphite/40 space-y-1">
                        <div className="text-muted text-[10px] uppercase font-bold">Source Types</div>
                        {Object.entries(runReport.composition.source_types || {}).map(([st, cnt]) => (
                          <div key={st} className="flex justify-between">
                            <span className="capitalize text-muted">{st}:</span>
                            <span className="font-mono font-bold text-fg">{cnt}</span>
                          </div>
                        ))}
                      </div>
                      <div className="p-2.5 rounded bg-slate/40 border border-graphite/40 space-y-1">
                        <div className="text-muted text-[10px] uppercase font-bold">Answerable by Route</div>
                        {Object.entries(runReport.composition.answerable_by_route || {}).map(([rt, cnt]) => (
                          <div key={rt} className="flex justify-between">
                            <span className="capitalize text-muted">{rt}:</span>
                            <span className="font-mono font-bold text-fg">{cnt}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Provenance Card */}
                {runReport.provenance && (
                  <div className="bg-carbon rounded-lg border border-graphite p-4 space-y-2">
                    <div className="text-[11px] font-bold text-fg uppercase tracking-wider text-muted/70">Execution Provenance & Environment</div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[11px]">
                      <div>Git Commit: <code className="text-electric">{runReport.provenance.git_commit?.slice(0, 8) || "N/A"}</code></div>
                      <div>Dirty Tree: <span className={runReport.provenance.dirty ? "text-amber font-bold" : "text-emerald"}>{runReport.provenance.dirty ? "YES (DIRTY)" : "CLEAN"}</span></div>
                      <div>Python: <span className="text-fg">{runReport.provenance.python_version || "3.12.10"}</span></div>
                      <div>Freshness Ref Date: <span className="text-fg font-mono">{runReport.provenance.freshness_reference_date || "2026-10-24"}</span></div>
                      <div>Index Run IDs: <code className="text-fg font-mono">{JSON.stringify(runReport.provenance.index_run_ids || [])}</code></div>
                      <div>Suite Hash: <code className="text-muted/80">{runReport.provenance.suite_hash?.slice(0, 12)}</code></div>
                      <div>CI Method: <span className="text-fg">{runReport.provenance.ci_method || "percentile_bootstrap"} (seed={runReport.provenance.seed || 42}, B={runReport.provenance.B || 2000})</span></div>
                      <div className="col-span-2">Embedder: <span className="text-fg">{runReport.provenance.embedder?.name}</span></div>
                      <div className="col-span-2">Reranker: <span className="text-fg">{runReport.provenance.reranker?.name}</span></div>
                    </div>
                  </div>
                )}

                {/* Quantitative Metrics Table with 95% Bootstrap CIs */}
                <div className="bg-carbon rounded-lg border border-graphite p-4 space-y-3">
                  <div className="text-[11px] font-bold text-fg uppercase tracking-wider text-muted/70">Core Quantitative Metrics (95% Bootstrap CI, 2,000 Resamples)</div>
                  <div className="overflow-x-auto border border-graphite/60 rounded">
                    <table className="w-full text-left border-collapse text-[11px]">
                      <thead className="bg-slate/50 text-muted border-b border-graphite">
                        <tr>
                          <th className="py-2 px-3">Metric</th>
                          <th className="py-2 px-3 text-right">Mean</th>
                          <th className="py-2 px-3">95% Bootstrap Confidence Interval</th>
                          <th className="py-2 px-3 text-center">Sample Size (n)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-graphite/30">
                        {Object.entries(runReport.metrics || {}).map(([metricName, m]) => {
                          const isNa = m.na || m.mean === null || m.mean === undefined;
                          const ciLow = m.ci_lower ?? m.ci_low;
                          const ciHigh = m.ci_upper ?? m.ci_high;
                          return (
                            <tr key={metricName} className="hover:bg-slate/20">
                              <td className="py-2 px-3 font-bold text-fg">{metricName}</td>
                              <td className="py-2 px-3 text-right font-mono">
                                {isNa ? (
                                  <span className="px-2 py-0.5 rounded text-[10px] bg-slate/80 border border-graphite text-muted font-normal">
                                    n/a ({m.reason || "not_computed"})
                                  </span>
                                ) : (
                                  <span>
                                    {m.mean!.toFixed(4)}
                                    {m.precision_ceiling !== undefined && (
                                      <span className="text-muted ml-2 text-[10px]">
                                        (ceiling: {m.precision_ceiling.toFixed(4)})
                                      </span>
                                    )}
                                  </span>
                                )}
                              </td>
                              <td className="py-2 px-3 font-mono text-muted">
                                {isNa || ciLow === null || ciLow === undefined ? (
                                  <span className="text-muted/40">—</span>
                                ) : (
                                  `[${ciLow.toFixed(4)}, ${ciHigh!.toFixed(4)}]`
                                )}
                              </td>
                              <td className="py-2 px-3 text-center font-mono text-muted/80">
                                {m.slice_size !== undefined ? `${m.n} / ${m.slice_size}` : m.n}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Route Classification Confusion Matrix */}
                {runReport.confusion_matrix && (() => {
                  const cm = runReport.confusion_matrix;
                  return (
                    <div className="bg-carbon rounded-lg border border-graphite p-4 space-y-3">
                      <div className="flex items-center justify-between border-b border-graphite/40 pb-2">
                        <div className="text-[11px] font-bold text-fg uppercase tracking-wider text-muted/70">
                          Route Classification Confusion Matrix (Accuracy: {(cm.accuracy * 100).toFixed(1)}%, n = {cm.n})
                        </div>
                        <span className="text-[10px] text-muted">Expected vs Router Decision (Dry-Run on Every Item)</span>
                      </div>
                      <div className="overflow-x-auto border border-graphite/50 rounded">
                        <table className="w-full text-center border-collapse text-[11px]">
                          <thead className="bg-slate/50 text-muted border-b border-graphite">
                            <tr>
                              <th className="py-1.5 px-3 text-left">Expected \ Predicted</th>
                              {cm.routes.map((r) => (
                                <th key={r} className="py-1.5 px-3 font-mono uppercase">{r}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-graphite/30">
                            {cm.routes.map((exp) => (
                              <tr key={exp} className="hover:bg-slate/20">
                                <td className="py-1.5 px-3 text-left font-bold text-fg capitalize">{exp}</td>
                                {cm.routes.map((pred) => {
                                  const count = cm.matrix[exp]?.[pred] || 0;
                                  const isDiag = exp === pred;
                                  return (
                                    <td
                                      key={pred}
                                      className={`py-1.5 px-3 font-mono ${
                                        isDiag && count > 0
                                          ? "text-emerald font-bold bg-emerald/10"
                                          : count > 0
                                          ? "text-crimson font-bold bg-crimson/10"
                                          : "text-muted/40"
                                      }`}
                                    >
                                      {count}
                                    </td>
                                  );
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  );
                })()}

                {/* Latency Breakdown & Route Slices */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Latency Breakdown */}
                  {runReport.latencies && (
                    <div className="bg-carbon rounded-lg border border-graphite p-4 space-y-3">
                      <div className="text-[11px] font-bold text-fg uppercase tracking-wider text-muted/70">Stage Latencies (p50 / p95)</div>
                      <table className="w-full text-left border-collapse text-[11px]">
                        <thead className="bg-slate/50 text-muted border-b border-graphite">
                          <tr>
                            <th className="py-1.5 px-3">Stage</th>
                            <th className="py-1.5 px-3 text-right">p50</th>
                            <th className="py-1.5 px-3 text-right">p95</th>
                            <th className="py-1.5 px-3 text-right">Mean</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-graphite/30">
                          {Object.entries(runReport.latencies).map(([stage, lat]) => (
                            <tr key={stage} className="hover:bg-slate/20">
                              <td className="py-1.5 px-3 font-medium text-fg capitalize">{stage}</td>
                              <td className="py-1.5 px-3 text-right font-mono">{lat.p50.toFixed(2)} ms</td>
                              <td className="py-1.5 px-3 text-right font-mono">{lat.p95.toFixed(2)} ms</td>
                              <td className="py-1.5 px-3 text-right font-mono text-muted">{lat.mean.toFixed(2)} ms</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Route Slices Breakdown */}
                  {(runReport.slices || runReport.route_slices) && (
                    <div className="bg-carbon rounded-lg border border-graphite p-4 space-y-3">
                      <div className="text-[11px] font-bold text-fg uppercase tracking-wider text-muted/70">Route Slices Performance Breakdown</div>
                      <table className="w-full text-left border-collapse text-[11px]">
                        <thead className="bg-slate/50 text-muted border-b border-graphite">
                          <tr>
                            <th className="py-1.5 px-3">Route</th>
                            <th className="py-1.5 px-3 text-center">Slice Size</th>
                            <th className="py-1.5 px-3 text-right">Recall@5</th>
                            <th className="py-1.5 px-3 text-right">Hit@5</th>
                            <th className="py-1.5 px-3 text-right">MRR</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-graphite/30">
                          {Object.entries((runReport as any).slices || runReport.route_slices || {}).map(([route, sl]: [string, any]) => {
                            const sz = sl.slice_size ?? sl.count ?? sl.n ?? 0;
                            const rMetrics = sl.metrics || {};
                            const recMean = rMetrics["recall@5"]?.mean ?? sl.recall_mean;
                            const hitMean = rMetrics["hit@5"]?.mean ?? sl.hit_mean;
                            const mrrMean = rMetrics["mrr"]?.mean ?? sl.mrr_mean;
                            return (
                              <tr key={route} className="hover:bg-slate/20">
                                <td className="py-1.5 px-3 font-bold text-electric">{route}</td>
                                <td className="py-1.5 px-3 text-center font-mono">{sz}</td>
                                <td className="py-1.5 px-3 text-right font-mono">{recMean !== undefined && recMean !== null ? Number(recMean).toFixed(4) : "n/a"}</td>
                                <td className="py-1.5 px-3 text-right font-mono">{hitMean !== undefined && hitMean !== null ? Number(hitMean).toFixed(4) : "n/a"}</td>
                                <td className="py-1.5 px-3 text-right font-mono">{mrrMean !== undefined && mrrMean !== null ? Number(mrrMean).toFixed(4) : "n/a"}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Diagnostic Failures List (Expandable with Gold Span Highlight) */}
                {runReport.failures && runReport.failures.length > 0 && (
                  <div className="bg-carbon rounded-lg border border-graphite p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="text-[11px] font-bold text-fg uppercase tracking-wider text-muted/70">
                        Diagnostic Failures ({runReport.failures.length} items)
                      </div>
                      <span className="text-[10px] text-muted">Click any item to inspect retrieved chunks & gold span alignment</span>
                    </div>

                    <div className="space-y-2">
                      {runReport.failures.map((f) => {
                        const isExpanded = !!expandedFailures[f.item_id];
                        const goldSpan = f.expected_evidence?.[0]?.span || "";

                        return (
                          <div key={f.item_id} className="border border-graphite/60 rounded bg-slate/20 overflow-hidden">
                            <div
                              onClick={() =>
                                setExpandedFailures({ ...expandedFailures, [f.item_id]: !isExpanded })
                              }
                              className="p-3 flex items-center justify-between cursor-pointer hover:bg-slate/40 transition-colors"
                            >
                              <div className="flex items-center gap-3">
                                {isExpanded ? <ChevronDown className="w-4 h-4 text-muted" /> : <ChevronRight className="w-4 h-4 text-muted" />}
                                <div>
                                  <span className="font-bold text-fg">Item #{f.item_id}:</span>{" "}
                                  <span className="text-fg/90">{f.question}</span>
                                </div>
                              </div>

                              <div className="flex items-center gap-2">
                                {f.reasons.map((r, ri) => (
                                  <span key={ri} className="px-2 py-0.5 rounded text-[10px] bg-crimson/15 text-crimson border border-crimson/30">
                                    {r}
                                  </span>
                                ))}
                              </div>
                            </div>

                            {isExpanded && (
                              <div className="p-4 bg-obsidian/60 border-t border-graphite space-y-3 text-[11px]">
                                <div className="grid grid-cols-2 gap-3 text-muted border-b border-graphite/40 pb-2">
                                  <div>Expected Route: <span className="font-mono text-fg">{f.expected_route || "N/A"}</span></div>
                                  <div>Actual Route: <span className="font-mono text-fg">{f.actual_route || "N/A"}</span></div>
                                </div>

                                {goldSpan && (
                                  <div className="p-2.5 rounded bg-amber/10 border border-amber/30 text-amber">
                                    <div className="font-bold mb-1">Expected Gold Span:</div>
                                    <div className="font-mono">{goldSpan}</div>
                                  </div>
                                )}

                                <div>
                                  <div className="font-bold text-fg mb-1">Retrieved Top Chunks:</div>
                                  <div className="space-y-2">
                                    {f.retrieved_chunks && f.retrieved_chunks.length > 0 ? (
                                      f.retrieved_chunks.slice(0, 3).map((ch, cidx) => {
                                        const text = ch.content || "";
                                        const hasGold = goldSpan && text.toLowerCase().includes(goldSpan.toLowerCase());

                                        return (
                                          <div key={cidx} className="p-2 rounded bg-carbon border border-graphite text-xs font-mono">
                                            <div className="flex items-center justify-between text-muted text-[10px] mb-1">
                                              <span>Rank #{ch.rank || cidx + 1} | Score: {ch.score?.toFixed(4) || "N/A"}</span>
                                              <span>Doc: {ch.document_id}</span>
                                            </div>
                                            <div className="text-fg/90">
                                              {hasGold ? (
                                                <span>
                                                  {text.split(new RegExp(`(${goldSpan})`, "gi")).map((part: string, pi: number) =>
                                                    part.toLowerCase() === goldSpan.toLowerCase() ? (
                                                      <mark key={pi} className="bg-emerald/30 text-emerald font-bold px-1 rounded">
                                                        {part}
                                                      </mark>
                                                    ) : (
                                                      part
                                                    )
                                                  )}
                                                </span>
                                              ) : (
                                                text
                                              )}
                                            </div>
                                          </div>
                                        );
                                      })
                                    ) : (
                                      <div className="text-muted italic">No chunks retrieved or gate refused query.</div>
                                    )}
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ==================================================================== */}
        {/* TAB 4: PAIRED STATISTICAL COMPARISON */}
        {/* ==================================================================== */}
        {activeTab === "compare" && (
          <div className="space-y-6">
            <div className="bg-carbon rounded-lg border border-graphite p-6 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-graphite pb-3">
                <div>
                  <h2 className="text-sm font-bold text-fg flex items-center gap-2">
                    <GitCompare className="w-4 h-4 text-electric" />
                    <span>Paired Bootstrap Comparison (2,000 Resamples, 95% CI)</span>
                  </h2>
                  <p className="text-muted text-[11px] mt-1">Rigorous non-parametric paired differences across common benchmark items.</p>
                </div>

                {/* Split Filter */}
                <div className="flex items-center gap-1 bg-slate/60 p-1 rounded border border-graphite">
                  <span className="text-[10px] text-muted px-1.5 font-bold uppercase">Split:</span>
                  {(["all", "dev", "holdout"] as const).map((sp) => (
                    <button
                      key={sp}
                      onClick={() => {
                        setCompareSplit(sp);
                        handleCompare(sp);
                      }}
                      className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase transition-colors ${
                        compareSplit === sp
                          ? "bg-electric text-obsidian font-bold"
                          : "text-muted hover:text-fg"
                      }`}
                    >
                      {sp}
                    </button>
                  ))}
                </div>
              </div>

              {/* Selector */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                <div>
                  <label className="block text-[11px] text-muted mb-1">Baseline Run A</label>
                  <select
                    value={compareRunA || ""}
                    onChange={(e) => setCompareRunA(Number(e.target.value))}
                    className="w-full bg-slate border border-graphite rounded px-3 py-2 text-fg text-xs focus:outline-none focus:border-electric"
                  >
                    {runs.map((r) => (
                      <option key={r.id} value={r.id}>
                        Run #{r.id}: {r.name} ({r.variant.strategy})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] text-muted mb-1">Candidate Run B</label>
                  <select
                    value={compareRunB || ""}
                    onChange={(e) => setCompareRunB(Number(e.target.value))}
                    className="w-full bg-slate border border-graphite rounded px-3 py-2 text-fg text-xs focus:outline-none focus:border-electric"
                  >
                    {runs.map((r) => (
                      <option key={r.id} value={r.id}>
                        Run #{r.id}: {r.name} ({r.variant.strategy})
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={() => handleCompare()}
                  disabled={loadingCompare || !compareRunA || !compareRunB || compareRunA === compareRunB}
                  className="py-2 px-4 bg-electric hover:bg-electric/90 text-obsidian font-bold rounded flex items-center justify-center gap-2 transition-colors disabled:opacity-50 text-xs"
                >
                  {loadingCompare ? <RefreshCw className="w-4 h-4 animate-spin" /> : <GitCompare className="w-4 h-4" />}
                  <span>Compare Runs</span>
                </button>
              </div>
            </div>

            {/* Results Display */}
            {compareResult && (
              <div className="bg-carbon rounded-lg border border-graphite p-6 space-y-6">
                <div className="flex items-center justify-between border-b border-graphite pb-3">
                  <div className="text-xs text-muted">
                    Comparing Run #{compareResult.run_a} vs Run #{compareResult.run_b} on{" "}
                    <strong className="text-fg">{compareResult.common_items_count}</strong> common items
                    {compareResult.split && (
                      <span className="ml-2 font-mono text-electric uppercase">({compareResult.split} split)</span>
                    )}
                  </div>
                </div>

                {/* Overall Metrics Comparisons */}
                <div className="space-y-4">
                  {Object.entries(compareResult.metrics || {}).map(([metricName, comp]) => {
                    const isGain = comp.delta_ci_lower > 0;
                    const isLoss = comp.delta_ci_upper < 0;

                    const colorClass = isGain
                      ? "text-emerald border-emerald/40 bg-emerald/5"
                      : isLoss
                      ? "text-crimson border-crimson/40 bg-crimson/5"
                      : "text-muted border-graphite bg-slate/20";

                    return (
                      <div key={metricName} className={`p-4 rounded-lg border ${colorClass} space-y-2`}>
                        <div className="flex flex-wrap items-center justify-between">
                          <span className="text-sm font-bold text-fg">{metricName}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              isGain
                                ? "bg-emerald/20 text-emerald"
                                : isLoss
                                ? "bg-crimson/20 text-crimson"
                                : "bg-slate text-muted"
                            }`}
                          >
                            {comp.verdict}
                          </span>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
                          <div>Run A Mean: <span className="text-fg">{comp.mean_a.toFixed(4)}</span></div>
                          <div>Run B Mean: <span className="text-fg">{comp.mean_b.toFixed(4)}</span></div>
                          <div>Delta: <span className={comp.delta_mean >= 0 ? "text-emerald font-bold" : "text-crimson font-bold"}>{comp.delta_mean >= 0 ? "+" : ""}{comp.delta_mean.toFixed(4)}</span></div>
                          <div>95% CI: <span>[{comp.delta_ci_lower.toFixed(4)}, {comp.delta_ci_upper.toFixed(4)}]</span></div>
                        </div>

                        {/* Visual CI Bar */}
                        <div className="mt-3 pt-2 border-t border-graphite/40 space-y-1">
                          <div className="flex items-center justify-between text-[10px] text-muted font-mono">
                            <span>-1.0</span>
                            <span className="text-fg/80">0.0 (Zero Delta)</span>
                            <span>+1.0</span>
                          </div>
                          <div className="w-full h-3 bg-obsidian rounded relative overflow-hidden border border-graphite">
                            {/* Zero line */}
                            <div className="absolute top-0 bottom-0 left-1/2 w-0.5 bg-graphite z-10" />

                            {/* CI range bar */}
                            {(() => {
                              const leftPct = Math.max(0, Math.min(100, ((comp.delta_ci_lower + 1) / 2) * 100));
                              const rightPct = Math.max(0, Math.min(100, ((comp.delta_ci_upper + 1) / 2) * 100));
                              const widthPct = Math.max(1, rightPct - leftPct);
                              const barBg = isGain ? "bg-emerald" : isLoss ? "bg-crimson" : "bg-muted/60";

                              return (
                                <div
                                  className={`absolute top-0.5 bottom-0.5 rounded ${barBg}`}
                                  style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                                />
                              );
                            })()}
                          </div>
                        </div>

                        <div className="flex items-center gap-4 text-[11px] text-muted font-mono pt-1">
                          <span>Wins: <strong className="text-emerald">{comp.wins}</strong></span>
                          <span>Losses: <strong className="text-crimson">{comp.losses}</strong></span>
                          <span>Ties: <strong className="text-fg">{comp.ties}</strong></span>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Per-Route Slice Paired Comparisons */}
                {compareResult.route_slices && Object.keys(compareResult.route_slices).length > 0 && (
                  <div className="border-t border-graphite pt-4 space-y-4">
                    <div className="text-xs font-bold text-fg uppercase tracking-wider text-muted/70">
                      Per-Route Slice Paired Comparisons
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {Object.entries(compareResult.route_slices).map(([rt, sliceData]) => (
                        <div key={rt} className="bg-obsidian rounded-lg border border-graphite p-4 space-y-3">
                          <div className="flex items-center justify-between border-b border-graphite/40 pb-2">
                            <span className="font-bold text-electric text-xs uppercase">Route Slice: {rt}</span>
                            <span className="text-[10px] font-mono text-muted">n = {sliceData.n}</span>
                          </div>
                          <div className="space-y-2">
                            {Object.entries(sliceData.metrics || {}).map(([mk, mComp]) => (
                              <div key={mk} className="flex items-center justify-between text-[11px] font-mono">
                                <span className="text-muted">{mk}:</span>
                                <div className="flex items-center gap-2">
                                  <span className={mComp.delta_mean >= 0 ? "text-emerald" : "text-crimson"}>
                                    {mComp.delta_mean >= 0 ? "+" : ""}{mComp.delta_mean.toFixed(4)}
                                  </span>
                                  <span className="text-[10px] text-muted/70">
                                    [{mComp.delta_ci_lower.toFixed(3)}, {mComp.delta_ci_upper.toFixed(3)}]
                                  </span>
                                  <span className={`px-1.5 py-0.2 rounded text-[9px] uppercase font-bold ${
                                    mComp.verdict === "win" ? "bg-emerald/20 text-emerald" : mComp.verdict === "loss" ? "bg-crimson/20 text-crimson" : "bg-slate text-muted"
                                  }`}>
                                    {mComp.verdict}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ==================================================================== */}
        {/* TAB 5: GOLD SET BUILDER */}
        {/* ==================================================================== */}
        {activeTab === "builder" && (
          <div className="space-y-6">
            {/* Header / Selectors */}
            <div className="bg-carbon rounded-lg border border-graphite p-6 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-graphite pb-3">
                <div>
                  <h2 className="text-sm font-bold text-fg flex items-center gap-2">
                    <PenTool className="w-4 h-4 text-electric" />
                    <span>Gold Set Builder</span>
                  </h2>
                  <p className="text-muted text-[11px] mt-1">
                    Select text inside ground-truth document pages or CSV rows to create verbatim expected spans with verified offsets.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-[11px] text-muted mb-1">Target Evaluation Suite</label>
                  <select
                    value={builderSuiteId || ""}
                    onChange={(e) => setBuilderSuiteId(Number(e.target.value))}
                    className="w-full bg-slate border border-graphite rounded px-3 py-2 text-fg text-xs focus:outline-none focus:border-electric"
                  >
                    {suites.map((s) => (
                      <option key={s.id} value={s.id}>
                        Suite #{s.id}: {s.name} ({s.is_frozen ? "Frozen" : "Draft"})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] text-muted mb-1">Source Corpus</label>
                  <select
                    value={builderSourceId || ""}
                    onChange={(e) => {
                      const sid = Number(e.target.value);
                      setBuilderSourceId(sid);
                      loadTextUnits(sid, builderVersion, 1);
                    }}
                    className="w-full bg-slate border border-graphite rounded px-3 py-2 text-fg text-xs focus:outline-none focus:border-electric"
                  >
                    {sources.map((src) => (
                      <option key={src.id} value={src.id}>
                        Source #{src.id}: {src.name} ({src.source_type})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-end justify-between gap-2">
                  <div className="flex-1">
                    <label className="block text-[11px] text-muted mb-1">Unit Page / Offset</label>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          if (builderSourceId && builderPage > 1) {
                            loadTextUnits(builderSourceId, builderVersion, builderPage - 1);
                          }
                        }}
                        disabled={builderPage <= 1 || loadingUnits}
                        className="px-2.5 py-1.5 bg-slate border border-graphite rounded text-fg text-xs disabled:opacity-40"
                      >
                        Prev
                      </button>
                      <span className="text-xs font-mono text-muted">
                        Page {builderPage} / {Math.max(1, Math.ceil(totalUnits / 20))}
                      </span>
                      <button
                        onClick={() => {
                          if (builderSourceId && builderPage < Math.ceil(totalUnits / 20)) {
                            loadTextUnits(builderSourceId, builderVersion, builderPage + 1);
                          }
                        }}
                        disabled={builderPage >= Math.ceil(totalUnits / 20) || loadingUnits}
                        className="px-2.5 py-1.5 bg-slate border border-graphite rounded text-fg text-xs disabled:opacity-40"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                  <span className="text-[11px] text-muted font-mono">{totalUnits} units total</span>
                </div>
              </div>
            </div>

            {/* Validation Alert / Server Response */}
            {builderValidationStatus && (
              <div
                className={`p-4 rounded-lg border text-xs flex items-start gap-3 ${
                  builderValidationStatus.status === 201
                    ? "bg-emerald/10 border-emerald/40 text-emerald"
                    : builderValidationStatus.status === 409
                    ? "bg-amber/10 border-amber/40 text-amber"
                    : "bg-crimson/10 border-crimson/40 text-crimson"
                }`}
              >
                {builderValidationStatus.status === 201 ? (
                  <CheckCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                )}
                <div className="space-y-1">
                  <div className="font-bold">
                    {builderValidationStatus.status === 201
                      ? "201 Created — Verbatim Gold Span Verified"
                      : builderValidationStatus.status === 409
                      ? "409 Conflict — Suite is Frozen"
                      : "422 Unprocessable Entity — Server Validation Failed"}
                  </div>
                  <p className="text-[11px] opacity-90">{builderValidationStatus.message}</p>
                </div>
              </div>
            )}

            {/* 2-Column Builder View */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Units Browser & Span Selector */}
              <div className="lg:col-span-7 space-y-4">
                <div className="bg-carbon rounded-lg border border-graphite p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-graphite pb-2">
                    <span className="text-[11px] font-bold text-fg uppercase tracking-wider text-muted/70">
                      Corpus Text Units ({textUnits.length} loaded)
                    </span>
                    <span className="text-[10px] text-muted">Click a unit to inspect text & highlight span</span>
                  </div>

                  {loadingUnits ? (
                    <div className="py-8 text-center text-muted flex items-center justify-center gap-2">
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Loading stored text units...</span>
                    </div>
                  ) : textUnits.length === 0 ? (
                    <div className="py-8 text-center text-muted">No text units found for this source.</div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-56 overflow-y-auto pr-1">
                      {textUnits.map((u) => (
                        <div
                          key={u.unit_id}
                          onClick={() => {
                            setSelectedUnit(u);
                            if (u.row_key) setBuilderRowKey(u.row_key);
                          }}
                          className={`p-2.5 rounded border text-xs cursor-pointer transition-all ${
                            selectedUnit?.unit_id === u.unit_id
                              ? "bg-slate border-electric text-fg shadow-sm"
                              : "bg-obsidian/60 border-graphite/60 text-muted hover:border-graphite hover:text-fg"
                          }`}
                        >
                          <div className="flex items-center justify-between font-mono text-[10px] mb-1">
                            <span className="text-electric truncate max-w-[120px]">{u.unit_id}</span>
                            <span>{u.page_number !== undefined ? `Page ${u.page_number}` : u.row_key ? `Row ${u.row_key}` : u.source_type}</span>
                          </div>
                          <p className="line-clamp-2 text-[11px] font-sans text-fg/80">{u.text}</p>
                          <div className="text-[10px] text-muted/70 mt-1 font-mono">
                            {u.word_count} words • {u.char_count} chars
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Selected Unit Full Text & Selection Action */}
                {selectedUnit && (
                  <div className="bg-carbon rounded-lg border border-graphite p-4 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-graphite pb-2">
                      <div>
                        <span className="text-xs font-bold text-fg">Active Unit: <code className="text-electric">{selectedUnit.unit_id}</code></span>
                        <span className="text-[10px] text-muted ml-2">
                          ({selectedUnit.page_number !== undefined ? `Page ${selectedUnit.page_number}` : selectedUnit.row_key ? `Row Key: ${selectedUnit.row_key}` : selectedUnit.source_type})
                        </span>
                      </div>

                      <button
                        type="button"
                        onClick={handleCaptureSelection}
                        className="py-1 px-3 bg-amber/20 hover:bg-amber/30 text-amber border border-amber/40 rounded flex items-center gap-1.5 text-xs font-semibold transition-colors"
                      >
                        <Crosshair className="w-3.5 h-3.5" />
                        <span>Use Selection as Expected Span</span>
                      </button>
                    </div>

                    <div className="text-[11px] text-muted mb-1">
                      Highlight any text inside the box below, then click &quot;Use Selection as Expected Span&quot;:
                    </div>

                    <div
                      className="p-3 bg-obsidian border border-graphite rounded font-mono text-xs text-fg leading-relaxed select-text cursor-text max-h-72 overflow-y-auto whitespace-pre-wrap"
                      onMouseUp={handleCaptureSelection}
                    >
                      {selectedUnit.text}
                    </div>

                    {builderSelectedSpan && (
                      <div className="p-2.5 rounded bg-amber/10 border border-amber/30 space-y-1">
                        <div className="flex items-center justify-between text-[10px] text-amber font-bold">
                          <span>Captured Verbatim Span ({builderSelectedSpan.length} characters):</span>
                          <button
                            type="button"
                            onClick={() => setBuilderSelectedSpan("")}
                            className="text-muted hover:text-fg text-[10px]"
                          >
                            Clear
                          </button>
                        </div>
                        <p className="font-mono text-xs text-fg/90 bg-carbon p-2 rounded border border-graphite">
                          &quot;{builderSelectedSpan}&quot;
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Right Column: Eval Item Authoring Form */}
              <div className="lg:col-span-5">
                <form onSubmit={handleCreateGoldItem} className="bg-carbon rounded-lg border border-graphite p-5 space-y-4">
                  <div className="border-b border-graphite pb-2">
                    <h3 className="text-xs font-bold text-fg flex items-center gap-2">
                      <Bookmark className="w-4 h-4 text-electric" />
                      <span>Author New Ground-Truth Item</span>
                    </h3>
                    <p className="text-[10px] text-muted mt-0.5">Enforces verbatim span verification on the server.</p>
                  </div>

                  <div>
                    <label className="block text-[11px] text-muted mb-1">Question / Prompt *</label>
                    <textarea
                      rows={2}
                      value={builderQuestion}
                      onChange={(e) => setBuilderQuestion(e.target.value)}
                      placeholder="e.g. What is the total operating revenue for Q3 2024?"
                      className="w-full bg-slate border border-graphite rounded px-3 py-2 text-fg text-xs focus:outline-none focus:border-electric"
                      required
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] text-muted mb-1">Item Type</label>
                      <select
                        value={builderItemType}
                        onChange={(e) => setBuilderItemType(e.target.value)}
                        className="w-full bg-slate border border-graphite rounded px-2.5 py-1.5 text-fg text-xs focus:outline-none focus:border-electric"
                      >
                        <option value="answerable">answerable</option>
                        <option value="unanswerable">unanswerable</option>
                        <option value="structured">structured</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] text-muted mb-1">Expected Route</label>
                      <select
                        value={builderExpectedRoute}
                        onChange={(e) => setBuilderExpectedRoute(e.target.value)}
                        className="w-full bg-slate border border-graphite rounded px-2.5 py-1.5 text-fg text-xs focus:outline-none focus:border-electric"
                      >
                        <option value="semantic">semantic</option>
                        <option value="exact">exact</option>
                        <option value="hybrid">hybrid</option>
                        <option value="structured">structured</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] text-muted mb-1">
                      Expected Facts (Atomic: number, name, or &le;3 tokens, comma-separated)
                    </label>
                    <input
                      type="text"
                      value={builderFacts}
                      onChange={(e) => setBuilderFacts(e.target.value)}
                      placeholder="e.g. 42000, California, 14.2%"
                      className="w-full bg-slate border border-graphite rounded px-3 py-1.5 text-fg text-xs font-mono focus:outline-none focus:border-electric"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] text-muted mb-1">Reference Answer / Target Value</label>
                    <input
                      type="text"
                      value={builderReferenceAnswer}
                      onChange={(e) => setBuilderReferenceAnswer(e.target.value)}
                      placeholder="Canonical expected answer or numeric value"
                      className="w-full bg-slate border border-graphite rounded px-3 py-1.5 text-fg text-xs focus:outline-none focus:border-electric"
                    />
                  </div>

                  {selectedUnit?.row_key && (
                    <div>
                      <label className="block text-[11px] text-muted mb-1">Row Key (Record Primary Key)</label>
                      <input
                        type="text"
                        value={builderRowKey}
                        onChange={(e) => setBuilderRowKey(e.target.value)}
                        className="w-full bg-slate border border-graphite rounded px-3 py-1.5 text-fg text-xs font-mono"
                      />
                    </div>
                  )}

                  <div className="p-3 bg-obsidian rounded border border-graphite space-y-1">
                    <div className="text-[10px] text-muted font-bold uppercase">Evidence Attachment</div>
                    <div className="text-[11px] text-fg">
                      Unit ID: <span className="font-mono text-electric">{selectedUnit?.unit_id || "None selected"}</span>
                    </div>
                    <div className="text-[11px] text-fg truncate">
                      Span: <span className="font-mono text-amber">{builderSelectedSpan ? `"${builderSelectedSpan}"` : "None"}</span>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={savingItem || !builderSuiteId || !selectedUnit}
                    className="w-full py-2.5 bg-electric hover:bg-electric/90 text-obsidian font-bold rounded flex items-center justify-center gap-2 transition-colors disabled:opacity-50 text-xs"
                  >
                    {savingItem ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                    <span>Save Ground-Truth Item (POST /eval/suites/{builderSuiteId || "..."}/items)</span>
                  </button>
                </form>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

