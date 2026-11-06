"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import {
  UploadCloud,
  Globe,
  FileText,
  Table as TableIcon,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Database,
  ExternalLink,
} from "lucide-react";
import { api, SourceItem } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";

export default function SourcesPage() {
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Upload state
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // URL Ingest state
  const [urlInput, setUrlInput] = useState<string>("");
  const [maxPages, setMaxPages] = useState<number>(10);
  const [ingesting, setIngesting] = useState<boolean>(false);

  // Toast state
  const [toast, setToast] = useState<{
    message: string;
    sourceId?: number;
    sourceName?: string;
    type: "success" | "error";
  } | null>(null);

  async function loadSources() {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getSources();
      setSources(data);
    } catch (err: any) {
      setError(err.message || "Failed to load sources");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSources();
  }, []);

  // Handle file upload
  async function handleFileUpload(file: File) {
    if (file.size > 20 * 1024 * 1024) {
      setToast({
        message: "File exceeds 20 MB limit.",
        type: "error",
      });
      return;
    }

    try {
      setUploading(true);
      const res = await api.uploadFile(file);
      await loadSources();
      setToast({
        message: `Successfully ingested "${file.name}"`,
        sourceId: res.source_id,
        sourceName: file.name,
        type: "success",
      });
    } catch (err: any) {
      setToast({
        message: err.message || "File upload failed.",
        type: "error",
      });
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  // Handle URL ingest
  async function handleUrlIngest(e: React.FormEvent) {
    e.preventDefault();
    if (!urlInput.trim()) return;

    try {
      setIngesting(true);
      const res = await api.ingestUrl(urlInput.trim(), maxPages);
      await loadSources();
      setToast({
        message: `Fetched ${res.pages_fetched} page(s) from "${urlInput}"`,
        sourceId: res.source_id,
        sourceName: urlInput,
        type: "success",
      });
      setUrlInput("");
    } catch (err: any) {
      setToast({
        message: err.message || "URL ingest failed.",
        type: "error",
      });
    } finally {
      setIngesting(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Toast Notification */}
      {toast && (
        <div
          className={`p-4 rounded-card border flex items-center justify-between transition-all ${
            toast.type === "success"
              ? "bg-emerald/10 border-emerald/30 text-fg"
              : "bg-crimson/10 border-crimson/30 text-fg"
          }`}
        >
          <div className="flex items-center gap-3">
            {toast.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 text-emerald flex-shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-crimson flex-shrink-0" />
            )}
            <span className="text-sm">{toast.message}</span>
          </div>

          <div className="flex items-center gap-3">
            {toast.sourceId && (
              <Link
                href={`/sources/${toast.sourceId}?tab=health`}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-electric hover:underline"
              >
                Inspect Data Health <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            )}
            <button
              onClick={() => setToast(null)}
              className="text-muted hover:text-fg text-xs px-2 py-1 rounded"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Header */}
      <div>
        <h1 className="font-heading font-bold text-3xl text-fg tracking-tight">
          Data Sources
        </h1>
        <p className="text-sm text-muted mt-1">
          Ingest, profile, and audit structured data tables and unstructured document sources.
        </p>
      </div>

      {/* Ingestion Panels (File Upload + URL Ingest) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* File Drag-and-Drop */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
              handleFileUpload(e.dataTransfer.files[0]);
            }
          }}
          className={`p-6 rounded-card border transition-all flex flex-col items-center justify-center text-center cursor-pointer min-h-[200px] ${
            isDragging
              ? "border-electric bg-electric/10"
              : "border-graphite bg-carbon hover:border-muted/50"
          }`}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFileUpload(e.target.files[0]);
              }
            }}
            className="hidden"
            accept=".pdf,.docx,.csv,.xlsx,.txt,.png,.jpg,.jpeg"
          />

          <div className="w-12 h-12 rounded-full bg-slate flex items-center justify-center text-electric mb-3 border border-graphite">
            <UploadCloud className="w-6 h-6" />
          </div>

          <div className="font-heading font-semibold text-base text-fg">
            {uploading ? "Ingesting file..." : "Click or drag file to upload"}
          </div>
          <p className="text-xs text-muted mt-1 max-w-sm">
            Supported formats: PDF, DOCX, CSV, XLSX, TXT, Images (OCR)
          </p>
          <div className="mt-3 inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate border border-graphite text-[11px] font-mono text-muted">
            Max file size: 20 MB
          </div>
        </div>

        {/* URL Ingest */}
        <div className="p-6 rounded-card border border-graphite bg-carbon flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Globe className="w-5 h-5 text-electric" />
              <h2 className="font-heading font-semibold text-base text-fg">
                Web Crawl Ingest
              </h2>
            </div>
            <p className="text-xs text-muted">
              Crawl domain seeds safely with strict SSRF protection and page depth limits.
            </p>
          </div>

          <form onSubmit={handleUrlIngest} className="mt-4 space-y-3">
            <div>
              <label className="block text-xs font-medium text-muted mb-1">
                Target URL
              </label>
              <input
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://example.com/docs"
                required
                className="w-full px-3 py-2 rounded-lg bg-obsidian border border-graphite text-sm text-fg placeholder-muted/50 focus:border-electric focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-4">
              <div className="flex-1">
                <label className="block text-xs font-medium text-muted mb-1">
                  Max Pages (Cap: 50)
                </label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={maxPages}
                  onChange={(e) => setMaxPages(Math.min(50, Math.max(1, parseInt(e.target.value) || 1)))}
                  className="w-full px-3 py-2 rounded-lg bg-obsidian border border-graphite text-sm text-fg focus:border-electric focus:outline-none font-mono"
                />
              </div>

              <div className="pt-5">
                <button
                  type="submit"
                  disabled={ingesting || !urlInput.trim()}
                  className="px-5 py-2 rounded-lg bg-electric hover:bg-electric/90 text-white font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {ingesting ? "Crawling..." : "Start Ingest"}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      {/* Sources Table */}
      <div className="rounded-card border border-graphite bg-carbon overflow-hidden">
        <div className="px-6 py-4 border-b border-graphite flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-electric" />
            <h3 className="font-heading font-semibold text-base text-fg">
              Ingested Sources ({sources.length})
            </h3>
          </div>
          <button
            onClick={loadSources}
            className="text-xs text-muted hover:text-fg font-mono"
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="p-8 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-slate/50 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : error ? (
          <div className="p-8 text-center text-sm text-crimson">
            {error}
          </div>
        ) : sources.length === 0 ? (
          <div className="p-12 text-center space-y-2">
            <Database className="w-8 h-8 text-muted mx-auto opacity-50" />
            <div className="text-sm font-medium text-fg">No sources ingested yet</div>
            <p className="text-xs text-muted max-w-sm mx-auto">
              Upload a document, messy CSV, or crawl a documentation site above to begin.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate border-b border-graphite text-xs text-muted font-mono uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-6">Source Name</th>
                  <th className="py-3 px-6">Type</th>
                  <th className="py-3 px-6">Version</th>
                  <th className="py-3 px-6">Counts</th>
                  <th className="py-3 px-6">Ingested</th>
                  <th className="py-3 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-graphite/60">
                {sources.map((s) => {
                  const isStructured = s.name.endsWith(".csv") || s.name.endsWith(".xlsx");
                  return (
                    <tr
                      key={s.id}
                      className="hover:bg-slate/40 transition-colors group"
                    >
                      <td className="py-4 px-6 font-medium text-fg">
                        <Link
                          href={`/sources/${s.id}`}
                          className="flex items-center gap-2.5 hover:text-electric transition-colors"
                        >
                          {isStructured ? (
                            <TableIcon className="w-4 h-4 text-amber flex-shrink-0" />
                          ) : (
                            <FileText className="w-4 h-4 text-electric flex-shrink-0" />
                          )}
                          <span>{s.name}</span>
                        </Link>
                      </td>
                      <td className="py-4 px-6 text-xs text-muted font-mono">
                        {s.source_type}
                      </td>
                      <td className="py-4 px-6 text-xs font-mono">
                        <span className="px-2 py-0.5 rounded bg-slate border border-graphite text-fg">
                          v{s.latest_version ?? 1}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-xs text-muted font-mono">
                        {isStructured ? (
                          <span>{s.records_count ?? "n/a"} rows</span>
                        ) : (
                          <span>{s.documents_count ?? "n/a"} docs</span>
                        )}
                      </td>
                      <td className="py-4 px-6 text-xs text-muted font-mono">
                        {s.created_at ? new Date(s.created_at).toLocaleDateString() : "n/a"}
                      </td>
                      <td className="py-4 px-6 text-right">
                        <Link
                          href={`/sources/${s.id}`}
                          className="inline-flex items-center gap-1 text-xs font-medium text-electric hover:underline"
                        >
                          Details <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

