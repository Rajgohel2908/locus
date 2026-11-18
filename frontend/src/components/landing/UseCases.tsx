"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GraduationCap, Microscope, Bot, CheckCircle2, ArrowRight } from "lucide-react";

const tabs = [
  {
    id: "student",
    label: "Student",
    icon: GraduationCap,
    title: "Study Smarter with Verifiable Notes",
    desc: "Upload syllabi, lecture slides, and voluminous textbooks. Ask complex conceptual questions and receive exact page-level citations to prepare for examinations with confidence.",
    features: [
      "Sub-second PDF, CSV & DOCX ingestion",
      "Instant page-level citations & highlight snippets",
      "Interactive knowledge recall with pgvector search"
    ],
    pattern: "student",
    badge: "EXAM READY",
  },
  {
    id: "researcher",
    label: "Researcher",
    icon: Microscope,
    title: "Cross-Reference Literature at Scale",
    desc: "Index hundreds of arXiv preprints, technical whitepapers, and scientific datasets. Uncover non-obvious correlations across papers with dense 384-dimensional semantic similarity.",
    features: [
      "Multi-document cosine cluster analysis",
      "Verbatim mathematical & technical quote extraction",
      "Seamless export of structured markdown citations"
    ],
    pattern: "researcher",
    badge: "MULTI-DOC RAG",
  },
  {
    id: "support",
    label: "Engineer / Bot",
    icon: Bot,
    title: "Deploy Verified Production Bots",
    desc: "Connect your API documentation, release notes, and troubleshooting runbooks. Embed a low-latency chat widget that answers customer inquiries without hallucinations.",
    features: [
      "FastAPI streaming SSE endpoints with API keys",
      "Embeddable zero-config React component",
      "Strict grounding in company knowledge base"
    ],
    pattern: "support",
    badge: "PRODUCTION API",
  },
] as const;

/* ────────────────────────────────────────────────────────────────── */
/*  Principle 7: Moving in Arcs & Principle 8: Secondary Action       */
/* ────────────────────────────────────────────────────────────────── */

function DynamicPatternVisual({ pattern }: { pattern: string }) {
  if (pattern === "student") {
    // Knowledge Matrix with curved arcs and pulsating nodes
    return (
      <div className="relative w-full h-full flex items-center justify-center p-6">
        <svg
          viewBox="0 0 240 240"
          className="w-full h-full"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Subtle background grid lines */}
          {Array.from({ length: 5 }).map((_, i) => (
            <line
              key={`h-${i}`}
              x1="30"
              y1={40 + i * 40}
              x2="210"
              y2={40 + i * 40}
              stroke="rgba(255,255,255,0.06)"
              strokeDasharray="3 3"
            />
          ))}
          {Array.from({ length: 5 }).map((_, i) => (
            <line
              key={`v-${i}`}
              x1={40 + i * 40}
              y1="30"
              x2={40 + i * 40}
              y2="210"
              stroke="rgba(255,255,255,0.06)"
              strokeDasharray="3 3"
            />
          ))}

          {/* Curved Knowledge Arc (Principle 7) */}
          <motion.path
            d="M 40 160 Q 120 40 200 120"
            stroke="#C8F432"
            strokeWidth="2"
            strokeOpacity="0.7"
            fill="none"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          />

          <motion.path
            d="M 50 180 Q 100 210 180 170"
            stroke="rgba(255,255,255,0.25)"
            strokeWidth="1.5"
            strokeDasharray="4 4"
            fill="none"
          />

          {/* Knowledge Nodes */}
          {[
            { cx: 40, cy: 160, r: 6, pulse: true, label: "Textbook.pdf" },
            { cx: 120, cy: 75, r: 8, pulse: true, label: "Lecture_04.docx" },
            { cx: 200, cy: 120, r: 6, pulse: true, label: "Lab_Notes.csv" },
            { cx: 80, cy: 120, r: 4, pulse: false },
            { cx: 160, cy: 140, r: 4, pulse: false },
          ].map((node, i) => (
            <g key={i}>
              {node.pulse && (
                <motion.circle
                  cx={node.cx}
                  cy={node.cy}
                  r={node.r * 2.2}
                  fill="#C8F432"
                  initial={{ opacity: 0.4, scale: 0.8 }}
                  animate={{ opacity: [0.4, 0], scale: [0.8, 1.8] }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    delay: i * 0.4,
                    ease: "easeOut",
                  }}
                />
              )}
              <circle
                cx={node.cx}
                cy={node.cy}
                r={node.r}
                fill={node.pulse ? "#C8F432" : "#FFFFFF"}
                opacity={node.pulse ? 0.95 : 0.4}
              />
            </g>
          ))}
        </svg>

        {/* Floating Citation Pill */}
        <motion.div
          initial={{ opacity: 0, y: 10, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="absolute bottom-4 left-6 right-6 bg-[#0B0B0B]/90 backdrop-blur-md border border-[#C8F432]/30 px-3 py-2 rounded-xl flex items-center justify-between text-xs font-mono shadow-xl"
        >
          <span className="text-[#C8F432] flex items-center gap-1.5 font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-[#C8F432] animate-pulse" />
            Chapter 8 • Page 142
          </span>
          <span className="text-white/40">98.4% match</span>
        </motion.div>
      </div>
    );
  }

  if (pattern === "researcher") {
    // Dynamic Constellation Graph oscillating in arcs
    const nodes = [
      { id: 0, x: 120, y: 40, r: 7, label: "arXiv:2401" },
      { id: 1, x: 50, y: 90, r: 5, label: "BERT" },
      { id: 2, x: 190, y: 80, r: 6, label: "Gemini" },
      { id: 3, x: 80, y: 160, r: 7, label: "MiniLM" },
      { id: 4, x: 160, y: 150, r: 8, label: "pgvector" },
      { id: 5, x: 120, y: 200, r: 5, label: "Cosine" },
    ];

    const edges = [
      [0, 1], [0, 2], [1, 3], [2, 4], [3, 4], [3, 5], [4, 5], [1, 4]
    ];

    return (
      <div className="relative w-full h-full flex items-center justify-center p-6">
        <svg
          viewBox="0 0 240 240"
          className="w-full h-full"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Laser connection arcs */}
          {edges.map(([a, b], i) => (
            <motion.line
              key={`edge-${i}`}
              x1={nodes[a].x}
              y1={nodes[a].y}
              x2={nodes[b].x}
              y2={nodes[b].y}
              stroke="rgba(200, 244, 50, 0.3)"
              strokeWidth="1.2"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.6, delay: i * 0.05 }}
            />
          ))}

          {/* Oscillating Constellation Nodes */}
          {nodes.map((node, i) => (
            <g key={node.id}>
              <motion.circle
                cx={node.x}
                cy={node.y}
                r={node.r}
                fill="#C8F432"
                animate={{
                  y: [0, i % 2 === 0 ? -4 : 4, 0],
                  x: [0, i % 3 === 0 ? 3 : -3, 0],
                }}
                transition={{
                  duration: 3 + i * 0.5,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
                className="drop-shadow-[0_0_8px_rgba(200,244,50,0.6)]"
              />
              <text
                x={node.x + 10}
                y={node.y + 3}
                fill="rgba(255,255,255,0.5)"
                fontSize="8"
                fontFamily="monospace"
              >
                {node.label}
              </text>
            </g>
          ))}
        </svg>

        {/* Floating Metrics Pill */}
        <motion.div
          initial={{ opacity: 0, y: 10, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="absolute bottom-4 left-6 right-6 bg-[#0B0B0B]/90 backdrop-blur-md border border-white/10 px-3 py-2 rounded-xl flex items-center justify-between text-xs font-mono shadow-xl"
        >
          <span className="text-white/80 font-mono">148 Papers Indexed</span>
          <span className="text-[#C8F432]">d = 384</span>
        </motion.div>
      </div>
    );
  }

  // Support bot — real-time floating chat wave & response bubble
  return (
    <div className="relative w-full h-full flex flex-col justify-between p-6">
      {/* Background audio/retrieval waveform */}
      <svg
        viewBox="0 0 240 100"
        className="w-full h-24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {[20, 50, 80].map((y, i) => (
          <motion.path
            key={`wave-${i}`}
            d={`M 10 ${y} Q 60 ${y - 14} 120 ${y} T 230 ${y}`}
            stroke="#C8F432"
            strokeOpacity={0.25 + i * 0.15}
            strokeWidth="1.5"
            fill="none"
            animate={{
              d: [
                `M 10 ${y} Q 60 ${y - 14} 120 ${y} T 230 ${y}`,
                `M 10 ${y} Q 60 ${y + 14} 120 ${y} T 230 ${y}`,
                `M 10 ${y} Q 60 ${y - 14} 120 ${y} T 230 ${y}`,
              ],
            }}
            transition={{
              duration: 3 + i,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        ))}
      </svg>

      {/* Realistic chat bubble stack */}
      <div className="space-y-2.5 z-10">
        <motion.div
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
          className="bg-white/[0.08] border border-white/15 p-2.5 rounded-xl rounded-tl-sm text-xs font-mono text-white/90 max-w-[85%]"
        >
          <span className="text-[#C8F432]">User:</span> How do I authenticate?
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0.15 }}
          className="bg-[#C8F432]/10 border border-[#C8F432]/30 p-2.5 rounded-xl rounded-tr-sm text-xs font-mono text-white max-w-[90%] ml-auto"
        >
          <span className="text-[#C8F432] font-semibold">LOCUS:</span> Pass Bearer token via Authorization header.
          <span className="block mt-1 text-[10px] text-[#C8F432]/70">Source: auth_v1.md #L42</span>
        </motion.div>
      </div>

      {/* Latency badge */}
      <div className="mt-3 bg-[#0B0B0B]/90 border border-white/10 px-3 py-1.5 rounded-lg flex items-center justify-between text-[11px] font-mono text-white/40">
        <span className="flex items-center gap-1.5 text-white/70">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          FastAPI SSE Streaming
        </span>
        <span className="text-[#C8F432]">32ms TTFT</span>
      </div>
    </div>
  );
}

export default function UseCases() {
  const [active, setActive] = useState(0);
  const currentTab = tabs[active];

  return (
    <section id="use-cases" className="relative bg-[#080808] py-24 overflow-hidden border-t border-white/5">
      {/* Background radial gradient */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_40%,rgba(200,244,50,0.03),transparent)]" />

      <div className="relative z-10 mx-auto max-w-5xl px-4 sm:px-6">
        {/* Section header (Principle 3: Staging the Focus) */}
        <motion.div
          className="text-center max-w-2xl mx-auto mb-14"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.05] border border-white/10 text-white/70 text-xs font-mono mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-[#C8F432]" />
            VERSATILE RETRIEVAL
          </div>

          <h2 className="font-heading text-3xl md:text-4xl font-bold text-white tracking-tight">
            One retrieval engine. Endless applications.
          </h2>
          <p className="mt-3 text-white/50 font-body text-sm md:text-base leading-relaxed">
            Whether accelerating technical research, passing university finals, or serving production customer queries.
          </p>
        </motion.div>

        {/* Tab Bar (Principle 13: Fitts's Law + Principle 20: Frequency of Use) */}
        <div className="flex justify-center mb-12">
          <div className="inline-flex bg-white/[0.04] border border-white/10 rounded-full p-1.5 gap-1.5 shadow-[0_8px_30px_rgba(0,0,0,0.6)]">
            {tabs.map((tab, i) => {
              const Icon = tab.icon;
              const isSelected = active === i;

              return (
                <button
                  key={tab.id}
                  onClick={() => setActive(i)}
                  // Principle 14: Bigger Hit Area (before:absolute before:-inset-1.5)
                  className="relative rounded-full px-5 sm:px-7 py-2.5 text-xs sm:text-sm font-medium transition-all duration-200 flex items-center gap-2 cursor-pointer before:absolute before:-inset-1 before:content-['']"
                  style={{ WebkitTapHighlightColor: "transparent" }}
                >
                  {/* Active sliding pill background (Principle 4: Pose to pose / Frequency of use) */}
                  {isSelected && (
                    <motion.div
                      layoutId="activeUseCasePill"
                      className="absolute inset-0 rounded-full bg-white text-black shadow-lg"
                      transition={{ type: "spring", stiffness: 450, damping: 32 }}
                    />
                  )}

                  {/* Icon & Label */}
                  <span
                    className={`relative z-10 flex items-center gap-2 ${
                      isSelected ? "text-black font-semibold" : "text-white/60 hover:text-white"
                    }`}
                  >
                    <Icon className="w-4 h-4" strokeWidth={isSelected ? 2 : 1.5} />
                    <span>{tab.label}</span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Tab Content Box (Principle 11: Solid Drawing & Principle 16: Miller's Law) */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentTab.id}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch"
          >
            {/* Left text column (7 cols) */}
            <div className="md:col-span-7 bg-[#0E0E0E]/90 border border-white/10 rounded-2xl p-7 md:p-8 flex flex-col justify-between shadow-[0_12px_40px_rgba(0,0,0,0.7)] relative overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent">
              <div>
                <div className="inline-block px-2.5 py-0.5 rounded-full bg-[#C8F432]/10 border border-[#C8F432]/30 text-[#C8F432] text-[11px] font-mono font-semibold mb-4">
                  {currentTab.badge}
                </div>

                <h3 className="font-heading text-2xl md:text-3xl font-bold text-white mb-3 tracking-tight">
                  {currentTab.title}
                </h3>

                <p className="font-body text-white/55 text-sm md:text-base leading-relaxed mb-6">
                  {currentTab.desc}
                </p>

                {/* Miller's Law: 3 concise bullet points */}
                <div className="space-y-3.5">
                  {currentTab.features.map((feat) => (
                    <div
                      key={feat}
                      className="flex items-start gap-3 text-sm font-body text-white/80"
                    >
                      <CheckCircle2 className="w-4 h-4 text-[#C8F432] shrink-0 mt-0.5" />
                      <span>{feat}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Bottom CTA link */}
              <div className="mt-8 pt-5 border-t border-white/5 flex items-center justify-between">
                <a
                  href="/playground"
                  className="inline-flex items-center gap-2 text-xs font-mono text-[#C8F432] hover:underline"
                >
                  <span>Experience interactive mode</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </a>
                <span className="text-white/30 text-xs font-mono">PostgreSQL pgvector</span>
              </div>
            </div>

            {/* Right interactive visual column (5 cols) */}
            <div className="md:col-span-5 bg-[#0A0A0A] border border-white/10 rounded-2xl flex items-center justify-center min-h-[300px] shadow-[0_12px_40px_rgba(0,0,0,0.7)] overflow-hidden relative">
              <DynamicPatternVisual pattern={currentTab.pattern} />
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}
