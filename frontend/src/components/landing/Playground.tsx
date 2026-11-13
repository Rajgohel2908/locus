"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  FileText,
  Sparkles,
  Send,
  CheckCircle2,
  ExternalLink,
  RotateCcw,
  Database,
  ArrowRight,
} from "lucide-react";

interface ConfettiDot {
  id: number;
  x: number;
  y: number;
  size: number;
  duration: number;
  delay: number;
}

const SAMPLE_DOCS = [
  { name: "financial_report_q3.pdf", size: "2.4 MB", chunks: 32 },
  { name: "system_architecture_v2.md", size: "840 KB", chunks: 18 },
  { name: "student_policies_2024.docx", size: "1.1 MB", chunks: 26 },
];

const PRESET_QUERIES = [
  "What drove the revenue growth in Q3?",
  "How does our vector index handle schema changes?",
  "What is the maximum token budget per chunk?",
];

const SAMPLE_ANSWERS: Record<
  string,
  {
    answer: string;
    citations: Array<{ source: string; page: string; score: number; snippet: string }>;
  }
> = {
  "What drove the revenue growth in Q3?": {
    answer:
      "Enterprise API adoption and multi-tenant RAG integrations grew 42% YoY, accounting for $14.2M of net recurring revenue in Q3.",
    citations: [
      {
        source: "financial_report_q3.pdf",
        page: "Page 12",
        score: 0.96,
        snippet: "Enterprise API volume surged 42% year-over-year to 1.8B calls.",
      },
      {
        source: "financial_report_q3.pdf",
        page: "Page 15",
        score: 0.91,
        snippet: "Net recurring revenue reached $14.2M behind dedicated studio seats.",
      },
    ],
  },
  "How does our vector index handle schema changes?": {
    answer:
      "Vector indexing uses immutable revision snapshots in Qdrant with atomic pointer swaps, ensuring zero downtime and instant rollbacks.",
    citations: [
      {
        source: "system_architecture_v2.md",
        page: "Section 4.1",
        score: 0.95,
        snippet: "Revisions are written to shadow collections before switching active aliases.",
      },
    ],
  },
  "What is the maximum token budget per chunk?": {
    answer:
      "The default chunk strategy targets 512 tokens with a 64-token sliding overlap window, preserved with semantic boundary awareness.",
    citations: [
      {
        source: "system_architecture_v2.md",
        page: "Section 3.2",
        score: 0.94,
        snippet: "Chunker enforces 512 token ceiling using recursive Markdown and AST splits.",
      },
    ],
  },
};

export default function Playground() {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [isEmbedding, setIsEmbedding] = useState(false);
  const [embedProgress, setEmbedProgress] = useState(0);
  const [isIndexed, setIsIndexed] = useState(false);
  const [confetti, setConfetti] = useState<ConfettiDot[]>([]);

  const [query, setQuery] = useState(PRESET_QUERIES[0]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [displayedAnswer, setDisplayedAnswer] = useState("");
  const [citationsReady, setCitationsReady] = useState(false);

  // Trigger file simulation
  const handleSelectFile = (name: string) => {
    setSelectedFile(name);
    setIsIndexed(false);
    setIsEmbedding(true);
    setEmbedProgress(0);
    setDisplayedAnswer("");
    setCitationsReady(false);
  };

  // Embedding progress animation
  useEffect(() => {
    if (!isEmbedding) return;

    const interval = setInterval(() => {
      setEmbedProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsEmbedding(false);
          setIsIndexed(true);
          // Spawn confetti burst of small lime dots
          const dots: ConfettiDot[] = Array.from({ length: 24 }).map((_, i) => ({
            id: i,
            x: (Math.random() - 0.5) * 220,
            y: (Math.random() - 0.5) * 160 - 20,
            size: Math.random() * 4 + 3,
            duration: 0.6 + Math.random() * 0.4,
            delay: Math.random() * 0.1,
          }));
          setConfetti(dots);
          return 100;
        }
        return prev + 12;
      });
    }, 90);

    return () => clearInterval(interval);
  }, [isEmbedding]);

  // Answer streaming word-by-word
  const handleRunQuery = () => {
    const data = SAMPLE_ANSWERS[query] || {
      answer: `Based on ${selectedFile || "your documents"}, the verified answer contains structured evidence with high cosine similarity.`,
      citations: [
        {
          source: selectedFile || "document.pdf",
          page: "Page 1",
          score: 0.93,
          snippet: "Extracted context matching the query semantics with zero hallucination.",
        },
      ],
    };

    setIsStreaming(true);
    setDisplayedAnswer("");
    setCitationsReady(false);

    const words = data.answer.split(" ");
    let i = 0;

    const streamInterval = setInterval(() => {
      if (i < words.length) {
        setDisplayedAnswer((prev) => (prev ? `${prev} ${words[i]}` : words[i]));
        i++;
      } else {
        clearInterval(streamInterval);
        setIsStreaming(false);
        // citations slide in with a bounce after answer finishes
        setTimeout(() => setCitationsReady(true), 150);
      }
    }, 45);
  };

  const handleReset = () => {
    setSelectedFile(null);
    setIsEmbedding(false);
    setEmbedProgress(0);
    setIsIndexed(false);
    setDisplayedAnswer("");
    setCitationsReady(false);
    setConfetti([]);
  };

  return (
    <section id="playground" className="py-24 bg-[#080808] relative overflow-hidden">
      {/* Background radial gradient */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-[#C8F432]/[0.02] rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-5xl mx-auto px-6 relative z-10">
        {/* Header */}
        <div className="text-center max-w-2xl mx-auto mb-16">
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.05] border border-white/10 text-white/70 text-xs font-mono mb-4"
          >
            <Sparkles className="w-3.5 h-3.5 text-[#C8F432]" />
            Live Playground Demo
          </motion.div>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl md:text-4xl font-bold font-heading text-white tracking-tight"
          >
            Drop a file. See it vectorize. Ask anything.
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="mt-3 text-white/50 text-sm md:text-base font-body"
          >
            Real-time chunking, progress bar shimmer, confetti on embed, and citation-gated answers.
          </motion.p>
        </div>

        {/* Playground Container */}
        <div className="bg-[#0D0D0E] border border-white/10 rounded-2xl md:rounded-3xl p-6 md:p-8 shadow-2xl">
          {/* Top Status & Controls */}
          <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-white/5">
            <div className="flex items-center gap-3">
              <span className="w-2.5 h-2.5 rounded-full bg-[#C8F432] animate-pulse" />
              <span className="text-white text-sm font-mono font-medium">
                LOCUS Engine • Ingestion &amp; Chat Sandbox
              </span>
            </div>
            {selectedFile && (
              <button
                onClick={handleReset}
                className="inline-flex items-center gap-1.5 text-xs text-white/50 hover:text-white transition font-mono px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/5 hover:border-white/20"
              >
                <RotateCcw className="w-3 h-3" />
                Reset Sandbox
              </button>
            )}
          </div>

          <div className="grid md:grid-cols-2 gap-8 mt-6">
            {/* LEFT: File Upload & Ingestion Simulation */}
            <div className="flex flex-col gap-5">
              <div className="text-xs font-mono uppercase tracking-wider text-white/40">
                1. Connect Data Source
              </div>

              {!selectedFile ? (
                <div className="flex flex-col gap-3">
                  <div className="border border-dashed border-white/20 rounded-2xl p-6 text-center bg-white/[0.01] hover:border-[#C8F432]/40 transition group cursor-pointer">
                    <div className="w-12 h-12 rounded-xl bg-white/[0.05] border border-white/10 flex items-center justify-center mx-auto mb-3 group-hover:scale-105 transition">
                      <Upload className="w-5 h-5 text-[#C8F432]" />
                    </div>
                    <div className="text-sm font-medium text-white mb-1">
                      Choose a sample document to ingest
                    </div>
                    <p className="text-xs text-white/40">
                      Click any file below to trigger automatic chunking &amp; embedding.
                    </p>
                  </div>

                  {/* Sample Document Pills */}
                  <div className="space-y-2 mt-2">
                    {SAMPLE_DOCS.map((doc) => (
                      <button
                        key={doc.name}
                        onClick={() => handleSelectFile(doc.name)}
                        className="w-full flex items-center justify-between p-3 rounded-xl bg-white/[0.03] border border-white/5 hover:border-white/20 hover:bg-white/[0.06] transition text-left group"
                      >
                        <div className="flex items-center gap-3">
                          <FileText className="w-4 h-4 text-white/40 group-hover:text-[#C8F432] transition" />
                          <div>
                            <div className="text-xs font-medium text-white group-hover:text-white">
                              {doc.name}
                            </div>
                            <div className="text-[10px] text-white/40 font-mono">
                              {doc.size} • ~{doc.chunks} chunks
                            </div>
                          </div>
                        </div>
                        <span className="text-[11px] text-[#C8F432] font-mono opacity-0 group-hover:opacity-100 transition flex items-center gap-1">
                          Ingest <ArrowRight className="w-3 h-3" />
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                /* Selected File State + Ingestion Animation */
                <div className="bg-white/[0.02] border border-white/10 rounded-2xl p-5 flex flex-col gap-4 relative">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg bg-[#C8F432]/10 border border-[#C8F432]/30 flex items-center justify-center text-[#C8F432]">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-white">{selectedFile}</div>
                        <div className="text-[10px] text-white/40 font-mono">
                          Parsed with Semantic AST Chunker
                        </div>
                      </div>
                    </div>
                    {isIndexed && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-mono text-[#C8F432] bg-[#C8F432]/10 px-2.5 py-1 rounded-full border border-[#C8F432]/30">
                        <CheckCircle2 className="w-3 h-3" /> Ready
                      </span>
                    )}
                  </div>

                  {/* Embedding Shimmer Progress Bar */}
                  {isEmbedding && (
                    <div className="space-y-2 mt-2">
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-white/60 flex items-center gap-1.5">
                          <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#C8F432] animate-ping" />
                          Embedding with bge-small-en...
                        </span>
                        <span className="text-[#C8F432]">{embedProgress}%</span>
                      </div>

                      {/* Shimmer progress bar */}
                      <div className="relative w-full h-2.5 bg-white/10 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full bg-[#C8F432] rounded-full relative overflow-hidden"
                          style={{ width: `${embedProgress}%` }}
                          transition={{ ease: "easeOut" }}
                        >
                          {/* Animated shimmer highlight */}
                          <motion.div
                            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent w-full"
                            animate={{ x: ["-100%", "200%"] }}
                            transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }}
                          />
                        </motion.div>
                      </div>
                      <div className="text-[10px] text-white/40 font-mono">
                        Computing 384-dimensional cosine embeddings
                      </div>
                    </div>
                  )}

                  {/* Confetti Burst Overlay */}
                  <div className="relative w-full flex justify-center">
                    <AnimatePresence>
                      {confetti.map((dot) => (
                        <motion.div
                          key={dot.id}
                          className="absolute rounded-full bg-[#C8F432] pointer-events-none shadow-[0_0_8px_#C8F432]"
                          style={{
                            width: dot.size,
                            height: dot.size,
                          }}
                          initial={{ x: 0, y: 0, scale: 1, opacity: 1 }}
                          animate={{
                            x: dot.x,
                            y: dot.y,
                            scale: 0.2,
                            opacity: 0,
                          }}
                          transition={{
                            duration: dot.duration,
                            delay: dot.delay,
                            ease: "easeOut",
                          }}
                        />
                      ))}
                    </AnimatePresence>
                  </div>

                  {/* Ready State Box */}
                  {isIndexed && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="p-3 rounded-xl bg-[#C8F432]/5 border border-[#C8F432]/20 flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <Database className="w-3.5 h-3.5 text-[#C8F432]" />
                        <span className="text-white/80 font-mono">
                          Indexed into Qdrant collection
                        </span>
                      </div>
                      <span className="text-[#C8F432] font-mono text-[11px]">
                        24 chunks • 384 dims
                      </span>
                    </motion.div>
                  )}
                </div>
              )}
            </div>

            {/* RIGHT: Live Question & Answer with Citations */}
            <div className="flex flex-col gap-5">
              <div className="text-xs font-mono uppercase tracking-wider text-white/40">
                2. Test Retrieval &amp; Ask
              </div>

              {/* Preset Query Chips */}
              <div className="flex flex-wrap gap-1.5">
                {PRESET_QUERIES.map((q) => (
                  <button
                    key={q}
                    onClick={() => {
                      setQuery(q);
                      setDisplayedAnswer("");
                      setCitationsReady(false);
                    }}
                    className={`text-[11px] px-2.5 py-1 rounded-full border transition font-mono ${
                      query === q
                        ? "bg-[#C8F432] text-black border-[#C8F432] font-medium"
                        : "bg-white/[0.03] text-white/60 border-white/10 hover:border-white/20"
                    }`}
                  >
                    {q}
                  </button>
                ))}
              </div>

              {/* Query Input Bar */}
              <div className="relative flex items-center">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ask a question about the uploaded document..."
                  className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-4 py-3 text-xs md:text-sm text-white placeholder-white/30 focus:outline-none focus:border-[#C8F432]/50 font-body pr-20"
                />
                <button
                  onClick={handleRunQuery}
                  disabled={isStreaming}
                  className="absolute right-1.5 bg-[#C8F432] hover:brightness-110 active:scale-95 disabled:opacity-50 text-black px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition font-body"
                >
                  <Send className="w-3 h-3" />
                  Ask
                </button>
              </div>

              {/* Streaming Answer Box */}
              <div className="min-h-[160px] bg-white/[0.02] border border-white/10 rounded-2xl p-4 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono uppercase text-white/40">
                      Generated Answer
                    </span>
                    {isStreaming && (
                      <span className="text-[10px] font-mono text-[#C8F432] flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#C8F432] animate-pulse" />
                        Streaming tokens...
                      </span>
                    )}
                  </div>

                  {displayedAnswer ? (
                    <p className="text-xs md:text-sm text-white/90 font-body leading-relaxed">
                      {displayedAnswer}
                      {isStreaming && (
                        <span className="inline-block w-1.5 h-3.5 bg-[#C8F432] ml-1 animate-pulse align-middle" />
                      )}
                    </p>
                  ) : (
                    <p className="text-xs text-white/30 italic">
                      Click "Ask" or choose a question above to test evidence retrieval...
                    </p>
                  )}
                </div>

                {/* Source Citations with Bounce Animation */}
                <AnimatePresence>
                  {citationsReady && (
                    <motion.div
                      initial={{ opacity: 0, x: 30 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      transition={{
                        type: "spring",
                        stiffness: 260,
                        damping: 20,
                      }}
                      className="mt-4 pt-3 border-t border-white/5 space-y-2"
                    >
                      <div className="text-[10px] font-mono text-[#C8F432] uppercase tracking-wider flex items-center gap-1.5">
                        <CheckCircle2 className="w-3 h-3" />
                        Grounded Sources ({SAMPLE_ANSWERS[query]?.citations.length || 1})
                      </div>
                      <div className="grid gap-2">
                        {(
                          SAMPLE_ANSWERS[query]?.citations || [
                            {
                              source: selectedFile || "document.pdf",
                              page: "Page 1",
                              score: 0.94,
                              snippet: "Verified sentence matching vector space projection.",
                            },
                          ]
                        ).map((cit, idx) => (
                          <div
                            key={idx}
                            className="bg-[#F5F5F0] text-black rounded-xl p-2.5 shadow-md flex flex-col gap-1 text-xs"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-mono font-semibold text-[11px] text-black/80">
                                {cit.source} • {cit.page}
                              </span>
                              <span className="font-mono text-[10px] bg-black text-[#C8F432] px-1.5 py-0.5 rounded-full font-medium">
                                cosine: {cit.score}
                              </span>
                            </div>
                            <p className="text-[11px] text-black/70 italic leading-snug">
                              "{cit.snippet}"
                            </p>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

