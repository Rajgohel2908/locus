"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  FileText,
  Sparkles,
  Send,
  CheckCircle2,
  RotateCcw,
  Database,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";

interface ConfettiDot {
  id: number;
  x: number;
  y: number;
  size: number;
  duration: number;
  delay: number;
}

// Principle 15: Hick's Law + Principle 16: Miller's Law (Curated 3 choices)
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
      "Vector indexing uses immutable revision snapshots in PostgreSQL pgvector with atomic pointer swaps, ensuring zero downtime and instant rollbacks.",
    citations: [
      {
        source: "system_architecture_v2.md",
        page: "Section 4.1",
        score: 0.95,
        snippet: "Revisions are written to shadow tables before switching active query pointers.",
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
  const [optimisticFlash, setOptimisticFlash] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);

  // Trigger file simulation with Principle 17: Doherty Threshold (< 100ms instant feedback)
  const handleSelectFile = (name: string) => {
    setSelectedFile(name);
    setIsIndexed(false);
    setIsEmbedding(true);
    setEmbedProgress(0);
    setDisplayedAnswer("");
    setCitationsReady(false);
  };

  // Principle 7: Moving in arcs + Principle 10: Exaggerated feedback (Confetti particles)
  useEffect(() => {
    if (!isEmbedding) return;

    const interval = setInterval(() => {
      setEmbedProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsEmbedding(false);
          setIsIndexed(true);

          // Spawn confetti burst along parabolic arc trajectories
          const dots: ConfettiDot[] = Array.from({ length: 28 }).map((_, i) => ({
            id: i,
            x: (Math.random() - 0.5) * 260,
            y: (Math.random() - 0.5) * 180 - 30,
            size: Math.random() * 4 + 3.5,
            duration: 0.65 + Math.random() * 0.45,
            delay: Math.random() * 0.08,
          }));
          setConfetti(dots);
          return 100;
        }
        return prev + 15;
      });
    }, 75);

    return () => clearInterval(interval);
  }, [isEmbedding]);

  // Principle 18: Postel's Law — Clean messy input + Principle 17: Doherty threshold (<50ms feedback)
  const handleRunQuery = () => {
    const cleanQuery = query.trim() || PRESET_QUERIES[0];
    setQuery(cleanQuery);

    // Instant optimistic response
    setOptimisticFlash(true);
    setTimeout(() => setOptimisticFlash(false), 200);

    const data = SAMPLE_ANSWERS[cleanQuery] || {
      answer: `Based on ${selectedFile || "your documents"}, the verified answer contains grounded evidence from PostgreSQL pgvector with zero hallucination.`,
      citations: [
        {
          source: selectedFile || "document.pdf",
          page: "Page 1",
          score: 0.94,
          snippet: "Extracted context matching the query semantics with verified cosine distance.",
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
        // Principle 5: Follow-through — citations bounce in with spring settle after stream completes
        setTimeout(() => setCitationsReady(true), 120);
      }
    }, 38);
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
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-[#C8F432]/[0.025] rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-5xl mx-auto px-6 relative z-10">
        {/* Header */}
        <div className="text-center max-w-2xl mx-auto mb-16">
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.05] border border-white/10 text-white/70 text-xs font-mono mb-4"
          >
            <Sparkles className="w-3.5 h-3.5 text-[#C8F432]" />
            Live Playground Demo
          </motion.div>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1], delay: 0.05 }}
            className="text-3xl md:text-4xl font-bold font-heading text-white tracking-tight"
          >
            Drop a file. See it vectorize. Ask anything.
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.12, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
            className="mt-3 text-white/50 text-sm md:text-base font-body"
          >
            Real-time chunking, progress bar shimmer, confetti on embed, and citation-gated answers.
          </motion.p>
        </div>

        {/* Playground Container with Principle 11: Solid Drawing in 3D */}
        <div className="bg-[#0D0D0E] border border-white/10 rounded-2xl md:rounded-3xl p-6 md:p-8 shadow-[0_30px_90px_rgba(0,0,0,0.85),0_0_0_1px_rgba(255,255,255,0.06)] relative overflow-hidden">
          {/* Top subtle bevel highlight */}
          <div className="absolute inset-x-8 top-0 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent" />

          {/* Top Status & Controls */}
          <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-white/5">
            <div className="flex items-center gap-3">
              <span className="w-2.5 h-2.5 rounded-full bg-[#C8F432] animate-pulse shadow-[0_0_8px_#C8F432]" />
              <span className="text-white text-sm font-mono font-medium">
                LOCUS Engine • Ingestion &amp; Chat Sandbox
              </span>
            </div>
            {selectedFile && (
              <motion.button
                onClick={handleReset}
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.94 }}
                className="inline-flex items-center gap-1.5 text-xs text-white/60 hover:text-white transition font-mono px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/5 hover:border-white/20 cursor-pointer"
              >
                <RotateCcw className="w-3 h-3" />
                Reset Sandbox
              </motion.button>
            )}
          </div>

          <div className="grid md:grid-cols-2 gap-8 mt-6">
            {/* LEFT: File Upload & Ingestion Simulation — Principle 3: Staging Focus (dims when answering) */}
            <motion.div
              animate={{ opacity: isStreaming ? 0.5 : 1 }}
              transition={{ duration: 0.25 }}
              className="flex flex-col gap-5"
            >
              <div className="text-xs font-mono uppercase tracking-wider text-white/40 flex items-center justify-between">
                <span>1. Connect Data Source</span>
                {isIndexed && (
                  <span className="text-[#C8F432] text-[11px] font-mono flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5" /> Gated
                  </span>
                )}
              </div>

              {!selectedFile ? (
                <div className="flex flex-col gap-3">
                  {/* Principle 14: Bigger Hit Area + Principle 1: Squash & Stretch */}
                  <motion.div
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    className="border border-dashed border-white/20 rounded-2xl p-6 text-center bg-white/[0.015] hover:border-[#C8F432]/40 transition-colors group cursor-pointer"
                  >
                    <div className="w-12 h-12 rounded-xl bg-white/[0.05] border border-white/10 flex items-center justify-center mx-auto mb-3 group-hover:scale-110 group-hover:border-[#C8F432]/40 transition-all duration-200">
                      <Upload className="w-5 h-5 text-[#C8F432]" />
                    </div>
                    <div className="text-sm font-medium text-white mb-1">
                      Choose a sample document to ingest
                    </div>
                    <p className="text-xs text-white/40">
                      Click any file below to trigger automatic chunking &amp; embedding.
                    </p>
                  </motion.div>

                  {/* Sample Document Pills — Principle 1: Squash & stretch + Principle 14: Bigger hit area */}
                  <div className="space-y-2 mt-2">
                    {SAMPLE_DOCS.map((doc) => (
                      <motion.button
                        key={doc.name}
                        onClick={() => handleSelectFile(doc.name)}
                        whileHover={{ scale: 1.015, x: 2 }}
                        whileTap={{ scaleX: 1.03, scaleY: 0.93 }}
                        transition={{ type: "spring", stiffness: 450, damping: 22 }}
                        className="w-full flex items-center justify-between p-3.5 rounded-xl bg-white/[0.03] border border-white/5 hover:border-white/20 hover:bg-white/[0.06] transition-colors text-left group cursor-pointer"
                      >
                        <div className="flex items-center gap-3">
                          <FileText className="w-4 h-4 text-white/40 group-hover:text-[#C8F432] transition-colors duration-150" />
                          <div>
                            <div className="text-xs font-medium text-white group-hover:text-white">
                              {doc.name}
                            </div>
                            <div className="text-[10px] text-white/40 font-mono">
                              {doc.size} • ~{doc.chunks} chunks
                            </div>
                          </div>
                        </div>
                        <span className="text-[11px] text-[#C8F432] font-mono opacity-0 group-hover:opacity-100 transition-opacity duration-150 flex items-center gap-1">
                          Ingest <ArrowRight className="w-3 h-3" />
                        </span>
                      </motion.button>
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
                      <motion.span
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ type: "spring", stiffness: 500, damping: 20 }}
                        className="inline-flex items-center gap-1 text-[11px] font-mono text-[#C8F432] bg-[#C8F432]/10 px-2.5 py-1 rounded-full border border-[#C8F432]/30 shadow-[0_0_12px_rgba(200,244,50,0.25)]"
                      >
                        <CheckCircle2 className="w-3 h-3" /> Ready
                      </motion.span>
                    )}
                  </div>

                  {/* Embedding Shimmer Progress Bar */}
                  {isEmbedding && (
                    <div className="space-y-2 mt-2">
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-white/60 flex items-center gap-1.5">
                          <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#C8F432] animate-ping" />
                          Embedding with all-MiniLM-L6-v2...
                        </span>
                        <span className="text-[#C8F432] font-semibold">{embedProgress}%</span>
                      </div>

                      {/* Shimmer progress bar */}
                      <div className="relative w-full h-2.5 bg-white/10 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full bg-[#C8F432] rounded-full relative overflow-hidden"
                          style={{ width: `${embedProgress}%` }}
                          transition={{ ease: [0.16, 1, 0.3, 1] }}
                        >
                          {/* Animated shimmer highlight */}
                          <motion.div
                            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/50 to-transparent w-full"
                            animate={{ x: ["-100%", "200%"] }}
                            transition={{ repeat: Infinity, duration: 1.1, ease: "linear" }}
                          />
                        </motion.div>
                      </div>
                      <div className="text-[10px] text-white/40 font-mono">
                        Computing 384-dimensional cosine embeddings
                      </div>
                    </div>
                  )}

                  {/* Confetti Burst Overlay — Principle 7: Moving in arcs + Principle 10: Exaggerated Feedback */}
                  <div className="relative w-full flex justify-center">
                    <AnimatePresence>
                      {confetti.map((dot) => (
                        <motion.div
                          key={dot.id}
                          className="absolute rounded-full bg-[#C8F432] pointer-events-none shadow-[0_0_10px_#C8F432]"
                          style={{
                            width: dot.size,
                            height: dot.size,
                          }}
                          initial={{ x: 0, y: 0, scale: 1, opacity: 1 }}
                          animate={{
                            x: dot.x,
                            y: dot.y,
                            scale: 0.15,
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
                      transition={{ type: "spring", stiffness: 400, damping: 22 }}
                      className="p-3 rounded-xl bg-[#C8F432]/5 border border-[#C8F432]/25 flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <Database className="w-3.5 h-3.5 text-[#C8F432]" />
                        <span className="text-white/80 font-mono">
                          Indexed into PostgreSQL pgvector
                        </span>
                      </div>
                      <span className="text-[#C8F432] font-mono text-[11px] font-semibold">
                        24 chunks • 384 dims
                      </span>
                    </motion.div>
                  )}
                </div>
              )}
            </motion.div>

            {/* RIGHT: Live Question & Answer with Citations */}
            <div className="flex flex-col gap-5">
              <div className="text-xs font-mono uppercase tracking-wider text-white/40">
                2. Test Retrieval &amp; Ask
              </div>

              {/* Principle 14: Bigger hit areas & Principle 20: Frequency of Use (Fast, zero-latency clicks) */}
              <div className="flex flex-wrap gap-2">
                {PRESET_QUERIES.map((q) => (
                  <motion.button
                    key={q}
                    onClick={() => {
                      setQuery(q);
                      setDisplayedAnswer("");
                      setCitationsReady(false);
                    }}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scaleX: 1.03, scaleY: 0.93 }}
                    transition={{ type: "spring", stiffness: 500, damping: 25 }}
                    className={`text-[11px] px-3 py-1.5 rounded-full border transition-colors font-mono cursor-pointer relative before:absolute before:-inset-1 before:content-[''] ${
                      query === q
                        ? "bg-[#C8F432] text-black border-[#C8F432] font-semibold shadow-[0_0_12px_rgba(200,244,50,0.3)]"
                        : "bg-white/[0.03] text-white/60 border-white/10 hover:border-white/20 hover:text-white"
                    }`}
                  >
                    {q}
                  </motion.button>
                ))}
              </div>

              {/* Query Input Bar — Principle 19: Jakob's Law (Enter to submit) */}
              <div className="relative flex items-center">
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !isStreaming) {
                      e.preventDefault();
                      handleRunQuery();
                    }
                  }}
                  placeholder="Ask a question about the document..."
                  className={`w-full bg-white/[0.04] border rounded-xl px-4 py-3.5 text-xs md:text-sm text-white placeholder-white/30 focus:outline-none focus:border-[#C8F432]/60 font-body pr-20 transition-all duration-200 ${
                    optimisticFlash ? "border-[#C8F432] shadow-[0_0_15px_rgba(200,244,50,0.4)]" : "border-white/10"
                  }`}
                />
                {/* Principle 1: Squash & Stretch + Principle 2: Anticipation Wind-up */}
                <motion.button
                  onClick={handleRunQuery}
                  disabled={isStreaming}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scaleX: 1.06, scaleY: 0.9 }}
                  transition={{ type: "spring", stiffness: 500, damping: 22 }}
                  className="absolute right-1.5 bg-[#C8F432] hover:brightness-110 active:brightness-95 disabled:opacity-50 text-black px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all font-body cursor-pointer shadow-[0_0_10px_rgba(200,244,50,0.2)]"
                >
                  <Send className="w-3 h-3" />
                  Ask
                </motion.button>
              </div>

              {/* Streaming Answer Box — Principle 3: Staging the Focus */}
              <div className="min-h-[170px] bg-white/[0.02] border border-white/10 rounded-2xl p-4 md:p-5 flex flex-col justify-between transition-shadow duration-300">
                <div>
                  <div className="flex items-center justify-between mb-2.5">
                    <span className="text-[10px] font-mono uppercase text-white/40">
                      Generated Answer
                    </span>
                    {isStreaming && (
                      <span className="text-[10px] font-mono text-[#C8F432] flex items-center gap-1 font-semibold">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#C8F432] animate-pulse" />
                        Streaming tokens...
                      </span>
                    )}
                  </div>

                  {displayedAnswer ? (
                    <p className="text-xs md:text-sm text-white/95 font-body leading-relaxed">
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

                {/* Source Citations — Principle 5: Follow Through & Overlapping Action */}
                <AnimatePresence>
                  {citationsReady && (
                    <motion.div
                      initial={{ opacity: 0, y: 16, scale: 0.97 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 10 }}
                      /* Elastic spring overshoot follow-through */
                      transition={{
                        type: "spring",
                        stiffness: 340,
                        damping: 18,
                      }}
                      className="mt-4 pt-3 border-t border-white/5 space-y-2"
                    >
                      <div className="text-[10px] font-mono text-[#C8F432] uppercase tracking-wider flex items-center gap-1.5 font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5" />
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
                          <motion.div
                            key={idx}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: idx * 0.08, type: "spring", stiffness: 400, damping: 20 }}
                            className="bg-[#F5F5F0] text-black rounded-xl p-3 shadow-lg flex flex-col gap-1 text-xs border-l-4 border-[#C8F432]"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-mono font-semibold text-[11px] text-black/85">
                                {cit.source} • {cit.page}
                              </span>
                              {/* Principle 10: Exaggerated Feedback */}
                              <motion.span
                                initial={{ scale: 0.8 }}
                                animate={{ scale: [1, 1.25, 1] }}
                                transition={{ duration: 0.4 }}
                                className="font-mono text-[10px] bg-black text-[#C8F432] px-2 py-0.5 rounded-full font-bold"
                              >
                                cosine: {cit.score}
                              </motion.span>
                            </div>
                            <p className="text-[11px] text-black/75 italic leading-snug">
                              &ldquo;{cit.snippet}&rdquo;
                            </p>
                          </motion.div>
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
