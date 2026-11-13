"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence, useInView } from "framer-motion";
import { Search, FileStack, Hash, Braces } from "lucide-react";

const vectors = [
  { id: "vec_001", text: "Final year project report...", source: "report.pdf p.2", score: 0.94, x: 15, y: 20 },
  { id: "vec_002", text: "Postgres connection string...", source: "db: students", score: 0.89, x: 45, y: 10 },
  { id: "vec_003", text: "Chunking strategy with overlap...", source: "notes.docx", score: 0.92, x: 75, y: 25 },
  { id: "vec_004", text: "API endpoint for retrieval...", source: "codebase", score: 0.87, x: 25, y: 50 },
  { id: "vec_005", text: "Exam syllabus 2024...", source: "syllabus.pdf p.1", score: 0.96, x: 60, y: 55 },
  { id: "vec_006", text: "Student attendance data...", source: "db: attendance", score: 0.91, x: 85, y: 60 },
  { id: "vec_007", text: "RAG evaluation metrics...", source: "paper.pdf p.8", score: 0.88, x: 10, y: 80 },
  { id: "vec_008", text: "Lime is our accent color...", source: "brand.md", score: 0.93, x: 50, y: 85 },
];

// Deterministic pseudo-random delays for dot entrance stagger
const entranceDelays = [0.1, 0.35, 0.2, 0.5, 0.15, 0.45, 0.3, 0.55];

// Pre-generated deterministic bar heights for embedding previews (per vector)
const embeddingBars: Record<string, number[]> = {
  vec_001: [60, 30, 80, 45, 20, 70, 55, 35, 90, 25, 50, 75, 40, 65, 15, 85, 30, 55, 70, 45],
  vec_002: [40, 70, 25, 85, 50, 35, 60, 90, 20, 75, 45, 30, 80, 55, 65, 15, 70, 40, 85, 50],
  vec_003: [75, 20, 55, 40, 90, 30, 65, 50, 80, 15, 70, 45, 25, 85, 60, 35, 50, 75, 20, 65],
  vec_004: [30, 85, 50, 65, 20, 75, 40, 55, 70, 90, 25, 60, 35, 80, 45, 15, 65, 30, 85, 50],
  vec_005: [55, 40, 70, 25, 80, 45, 30, 65, 15, 85, 60, 50, 75, 20, 90, 35, 45, 70, 25, 80],
  vec_006: [20, 65, 45, 80, 35, 55, 70, 25, 60, 40, 90, 15, 50, 75, 30, 85, 55, 20, 65, 40],
  vec_007: [80, 35, 60, 15, 70, 50, 25, 85, 45, 55, 30, 75, 65, 20, 50, 90, 40, 60, 35, 75],
  vec_008: [45, 75, 30, 55, 65, 20, 80, 40, 70, 35, 60, 85, 15, 50, 25, 70, 90, 45, 55, 30],
};

function ScoreColor(score: number) {
  if (score >= 0.95) return "text-[#C8F432]";
  if (score >= 0.9) return "text-emerald-400";
  return "text-white/70";
}

export default function VectorViewer() {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(canvasRef, { once: true, margin: "-80px" });

  const hoveredVector = vectors.find((v) => v.id === hoveredId) ?? null;

  return (
    <section id="vector-viewer" className="w-full py-24 md:py-32 px-4 bg-[#080808]">
      <div className="max-w-4xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-12">
          <motion.h2
            className="font-heading text-3xl md:text-4xl lg:text-5xl text-[#F5F5F0] tracking-tight"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          >
            Your Vector Space, Visualized
          </motion.h2>
          <motion.p
            className="font-body text-white/50 text-base md:text-lg mt-3"
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, ease: "easeOut", delay: 0.1 }}
          >
            Hover any vector to see its source &amp; similarity
          </motion.p>
        </div>

        {/* Viewer Card */}
        <motion.div
          className="bg-[#0E0E0E] border border-white/[0.08] rounded-2xl md:rounded-3xl overflow-hidden"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease: "easeOut", delay: 0.15 }}
        >
          {/* Header Bar */}
          <div className="flex items-center justify-between px-4 md:px-6 py-3 border-b border-white/[0.06]">
            <div className="flex items-center gap-3">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#C8F432] opacity-50" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[#C8F432]" />
              </span>
              <span className="font-mono text-xs text-white/50 tracking-wide">
                8 vectors&nbsp;&middot;&nbsp;1,234 dimensions&nbsp;&middot;&nbsp;Qdrant
              </span>
            </div>
            <span className="font-mono text-xs text-white/30 hidden sm:block">
              cosine similarity
            </span>
          </div>

          {/* Canvas Area */}
          <div
            ref={canvasRef}
            className="relative h-[340px] md:h-[420px] bg-[#0A0A0A] overflow-hidden"
            style={{
              backgroundImage:
                "radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px)",
              backgroundSize: "28px 28px",
            }}
          >
            {/* Search Query Pill */}
            <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-[#F5F5F0] rounded-full px-3.5 py-1.5 shadow-md">
              <Search className="w-3.5 h-3.5 text-black/70" strokeWidth={1.5} />
              <span className="font-mono text-[11px] text-[#080808] whitespace-nowrap">
                &ldquo;how to build RAG from DB?&rdquo;
              </span>
              <span className="relative flex h-1.5 w-1.5 ml-1">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#C8F432] opacity-60" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#C8F432]" />
              </span>
            </div>

            {/* Vector Dots */}
            {vectors.map((vec, i) => {
              const isHovered = hoveredId === vec.id;
              return (
                <motion.div
                  key={vec.id}
                  className="absolute z-[5] cursor-pointer"
                  style={{
                    left: `${vec.x}%`,
                    top: `${vec.y}%`,
                    transform: "translate(-50%, -50%)",
                  }}
                  initial={{ opacity: 0, scale: 0 }}
                  animate={
                    isInView
                      ? { opacity: 1, scale: 1 }
                      : { opacity: 0, scale: 0 }
                  }
                  transition={{
                    type: "spring",
                    stiffness: 260,
                    damping: 20,
                    delay: entranceDelays[i],
                  }}
                  onMouseEnter={() => setHoveredId(vec.id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  {/* Hit area (larger than dot for easier hover) */}
                  <div className="relative flex items-center justify-center w-8 h-8">
                    <motion.div
                      className="rounded-full"
                      animate={{
                        width: isHovered ? 14 : 12,
                        height: isHovered ? 14 : 12,
                        backgroundColor: isHovered ? "#C8F432" : ScoreToColor(vec.score),
                        boxShadow: isHovered
                          ? "0 0 20px #C8F432, 0 0 40px rgba(200,244,50,0.3)"
                          : "0 0 0px transparent",
                        scale: isHovered ? 1.8 : 1,
                      }}
                      transition={{ duration: 0.2, ease: "easeOut" }}
                    />
                  </div>

                  {/* Connection line to query (faint) when hovered */}
                  {isHovered && (
                    <motion.div
                      className="absolute top-1/2 left-1/2 pointer-events-none"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                    >
                      <svg
                        className="absolute"
                        style={{
                          width: 0,
                          height: 0,
                          overflow: "visible",
                        }}
                      >
                        <line
                          x1={0}
                          y1={0}
                          x2={`${-vec.x + 8}%`}
                          y2={`${-vec.y + 6}%`}
                          stroke="#C8F432"
                          strokeOpacity={0.12}
                          strokeWidth={1}
                          strokeDasharray="4 4"
                        />
                      </svg>
                    </motion.div>
                  )}
                </motion.div>
              );
            })}

            {/* Tooltip Panel — bottom overlay */}
            <AnimatePresence mode="wait">
              {hoveredVector && (
                <motion.div
                  key={hoveredVector.id}
                  className="absolute bottom-4 left-4 right-4 z-20"
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  transition={{ duration: 0.25, ease: "easeOut" }}
                >
                  <div className="bg-[#F5F5F0] rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center gap-4 shadow-2xl border border-white/20">
                    {/* Left info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <span className="inline-flex items-center bg-[#080808] text-white font-mono text-[10px] px-2.5 py-0.5 rounded-full tracking-wide">
                          {hoveredVector.id}
                        </span>
                        <span className="inline-flex items-center gap-1 font-mono text-xs font-semibold text-[#080808]">
                          <Hash className="w-3 h-3 text-black/50" strokeWidth={1.5} />
                          <span>score: {hoveredVector.score.toFixed(2)}</span>
                        </span>
                        <span className="inline-flex items-center gap-1 bg-[#080808]/[0.06] text-[#080808]/70 font-mono text-[10px] px-2.5 py-0.5 rounded-full">
                          <FileStack className="w-3 h-3 text-black/50" strokeWidth={1.5} />
                          <span>{hoveredVector.source}</span>
                        </span>
                      </div>
                      <p className="font-body text-sm text-[#080808]/85 leading-relaxed truncate">
                        &ldquo;{hoveredVector.text}&rdquo;
                      </p>
                    </div>

                    {/* Embedding preview bars */}
                    <div className="flex items-center gap-2 shrink-0 bg-black/[0.04] px-3 py-2 rounded-xl">
                      <Braces className="w-3.5 h-3.5 text-black/40" strokeWidth={1.5} />
                      <div className="flex items-end gap-[2px] h-7">
                        {embeddingBars[hoveredVector.id].map((h, i) => (
                          <motion.div
                            key={i}
                            className="w-[2.5px] rounded-full bg-[#080808]/30"
                            initial={{ height: 2 }}
                            animate={{ height: `${h * 0.3}px` }}
                            transition={{
                              duration: 0.4,
                              ease: "easeOut",
                              delay: i * 0.02,
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Footer Stats */}
          <div className="grid grid-cols-3 border-t border-white/[0.06]">
            {[
              { label: "Total Chunks", value: "1,234" },
              { label: "Avg Latency", value: "43ms" },
              { label: "Model", value: "bge-small" },
            ].map((stat, i) => (
              <div
                key={stat.label}
                className={`px-4 md:px-6 py-3 ${
                  i < 2 ? "border-r border-white/[0.06]" : ""
                }`}
              >
                <span className="block font-mono text-[10px] uppercase tracking-wider text-white/30 mb-0.5">
                  {stat.label}
                </span>
                <span className="block font-mono text-sm text-[#F5F5F0]">
                  {stat.value}
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function ScoreToColor(score: number): string {
  if (score >= 0.95) return "#C8F432";
  if (score >= 0.92) return "rgba(200, 244, 50, 0.7)";
  if (score >= 0.89) return "rgba(200, 244, 50, 0.45)";
  return "rgba(200, 244, 50, 0.25)";
}
