"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence, useInView } from "framer-motion";
import { Search, FileStack, Hash, Braces, Sparkles } from "lucide-react";

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
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          >
            Your Vector Space, Visualized
          </motion.h2>
          <motion.p
            className="font-body text-white/50 text-base md:text-lg mt-3"
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1], delay: 0.08 }}
          >
            Hover any vector to see its source &amp; similarity
          </motion.p>
        </div>

        {/* Viewer Card with Principle 11: Solid Drawing in 3D */}
        <motion.div
          className="bg-[#0E0E0E] border border-white/[0.08] rounded-2xl md:rounded-3xl overflow-hidden shadow-[0_30px_90px_rgba(0,0,0,0.85)] relative"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1], delay: 0.12 }}
        >
          {/* Header Bar */}
          <div className="flex items-center justify-between px-4 md:px-6 py-3.5 border-b border-white/[0.06] bg-white/[0.01]">
            <div className="flex items-center gap-3">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#C8F432] opacity-50" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[#C8F432]" />
              </span>
              <span className="font-mono text-xs text-white/60 tracking-wide">
                8 vectors&nbsp;&middot;&nbsp;384 dimensions&nbsp;&middot;&nbsp;PostgreSQL pgvector
              </span>
            </div>
            <span className="font-mono text-xs text-[#C8F432] hidden sm:block">
              cosine distance &lt;=&gt;
            </span>
          </div>

          {/* Canvas Area */}
          <div
            ref={canvasRef}
            className="relative h-[340px] md:h-[420px] bg-[#0A0A0A] overflow-hidden"
            style={{
              backgroundImage: `
                radial-gradient(circle at 50% 50%, rgba(200, 244, 50, 0.035) 0%, transparent 60%),
                linear-gradient(to right, rgba(255, 255, 255, 0.025) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(255, 255, 255, 0.025) 1px, transparent 1px)
              `,
              backgroundSize: "100% 100%, 32px 32px, 32px 32px",
            }}
          >
            {/* SVG Connecting lines — Principle 7: Moving in arcs */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
              {hoveredVector &&
                vectors
                  .filter((v) => v.id !== hoveredVector.id)
                  .map((other) => (
                    <motion.line
                      key={`line-${hoveredVector.id}-${other.id}`}
                      initial={{ pathLength: 0, opacity: 0 }}
                      animate={{ pathLength: 1, opacity: 0.35 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.3, ease: "easeOut" }}
                      x1={`${hoveredVector.x}%`}
                      y1={`${hoveredVector.y}%`}
                      x2={`${other.x}%`}
                      y2={`${other.y}%`}
                      stroke="#C8F432"
                      strokeWidth="1"
                      strokeDasharray="3 3"
                    />
                  ))}
            </svg>

            {/* Vector Points */}
            {vectors.map((v, i) => {
              const isHovered = hoveredId === v.id;
              const hasHover = hoveredId !== null;
              /* Principle 3: Staging the Focus — dim non-focused elements */
              const isDimmed = hasHover && !isHovered;

              return (
                <div
                  key={v.id}
                  className="absolute -translate-x-1/2 -translate-y-1/2"
                  style={{ left: `${v.x}%`, top: `${v.y}%` }}
                >
                  {/* Principle 14: Bigger Hit Area — 40x40px touch surface around the 12px dot */}
                  <motion.div
                    className="relative w-10 h-10 -m-3 flex items-center justify-center cursor-pointer group"
                    onMouseEnter={() => setHoveredId(v.id)}
                    onMouseLeave={() => setHoveredId(null)}
                    /* Principle 1: Squash & stretch on tap */
                    whileTap={{ scale: 0.85 }}
                  >
                    {/* Pulsing Sonar Ring when Hovered — Principle 10: Exaggerated Feedback */}
                    {isHovered && (
                      <motion.div
                        className="absolute w-8 h-8 rounded-full border border-[#C8F432] pointer-events-none"
                        initial={{ scale: 0.6, opacity: 1 }}
                        animate={{ scale: 1.8, opacity: 0 }}
                        transition={{ repeat: Infinity, duration: 1.2, ease: "easeOut" }}
                      />
                    )}

                    {/* Dot graphic */}
                    <motion.div
                      className={`rounded-full transition-colors duration-200 ${
                        isHovered
                          ? "w-4 h-4 bg-[#C8F432] shadow-[0_0_18px_#C8F432]"
                          : "w-2.5 h-2.5 bg-white/70 group-hover:bg-[#C8F432]"
                      }`}
                      animate={{
                        opacity: isDimmed ? 0.2 : 1,
                        scale: isHovered ? 1.3 : 1,
                      }}
                      transition={{ duration: 0.18, ease: "easeOut" }}
                    />
                  </motion.div>
                </div>
              );
            })}

            {/* Hover Floating Details Card */}
            <AnimatePresence>
              {hoveredVector && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 8, scale: 0.96 }}
                  /* Principle 6: Slow in & slow out */
                  transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
                  className="absolute bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-80 bg-[#121214]/95 border border-white/15 rounded-xl p-4 backdrop-blur-xl shadow-2xl z-20 pointer-events-none"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[11px] text-white/50">{hoveredVector.id}</span>
                    <span className={`font-mono text-xs font-bold ${ScoreColor(hoveredVector.score)}`}>
                      cosine {(hoveredVector.score * 100).toFixed(0)}%
                    </span>
                  </div>

                  <p className="text-xs text-white/90 font-medium font-body leading-snug mb-3">
                    {hoveredVector.text}
                  </p>

                  <div className="text-[10px] font-mono text-white/50 border-t border-white/5 pt-2 flex items-center justify-between">
                    <span>{hoveredVector.source}</span>
                    <span className="text-[#C8F432]">verified chunk</span>
                  </div>

                  {/* Principle 8: Secondary action — Embedding spectrum animation */}
                  <div className="mt-2.5 flex items-end gap-0.5 h-3">
                    {embeddingBars[hoveredVector.id]?.slice(0, 16).map((h, idx) => (
                      <div
                        key={idx}
                        className="flex-1 bg-[#C8F432]/40 rounded-full"
                        style={{ height: `${h}%` }}
                      />
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
