"use client";

import { useState, useEffect, useRef } from "react";
import { motion, useInView, AnimatePresence } from "framer-motion";
import { 
  FileText, 
  Split, 
  Layers, 
  Cpu, 
  MessageSquareCode, 
  Terminal,
  ArrowUpRight
} from "lucide-react";

// ─── Micro-interaction components ───────────────────────────────────

function MultiSourceAnimation({ hovered }: { hovered: boolean }) {
  const files = [
    { label: "PDF", x: -22, y: -16, r: -12, color: "text-[#C8F432]" },
    { label: "CSV", x: 0, y: -24, r: 0, color: "text-white" },
    { label: "DOCX", x: 22, y: -16, r: 12, color: "text-[#C8F432]" },
  ];

  return (
    <div className="relative w-12 h-12 flex items-center justify-center">
      {/* Folder icon with solid depth */}
      <motion.div
        animate={{ scale: hovered ? 1.08 : 1 }}
        transition={{ type: "spring", stiffness: 400, damping: 25 }}
        className="relative z-10 w-9 h-7 rounded-[4px] bg-white/[0.08] border border-white/20 flex items-center justify-center shadow-[0_4px_12px_rgba(0,0,0,0.5)]"
      >
        <svg
          width="16"
          height="14"
          viewBox="0 0 18 16"
          fill="none"
          className="text-white/60"
        >
          <path
            d="M1 4V13C1 14.1 1.9 15 3 15H15C16.1 15 17 14.1 17 13V6C17 4.9 16.1 4 15 4H9L7 2H3C1.9 2 1 2.9 1 4Z"
            stroke="currentColor"
            strokeWidth="1.4"
          />
        </svg>
      </motion.div>

      {/* Flying file icons with Arc motion and Follow-through */}
      {files.map((file, i) => (
        <motion.div
          key={file.label}
          className="absolute z-20 pointer-events-none"
          initial={false}
          animate={{
            x: hovered ? 0 : file.x,
            y: hovered ? 0 : file.y,
            rotate: hovered ? 0 : file.r,
            opacity: hovered ? 0 : 1,
            scale: hovered ? 0.35 : 1,
          }}
          transition={{
            type: "spring",
            stiffness: 320,
            damping: 22,
            delay: hovered ? i * 0.05 : i * 0.04,
          }}
        >
          <div className="w-5 h-6 rounded-[3px] bg-[#121212] border border-white/25 flex items-center justify-center shadow-lg">
            <span className={`text-[6px] font-mono font-bold leading-none ${file.color}`}>
              {file.label}
            </span>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

function SmartChunkingAnimation({ hovered }: { hovered: boolean }) {
  const slicePositions = [25, 50, 75];

  return (
    <div className="relative w-12 h-12 flex items-center justify-center">
      <div className="w-9 h-3.5 bg-white/[0.08] rounded-md border border-white/15 relative overflow-hidden flex items-center px-1">
        <motion.div
          className="absolute inset-0 bg-[#C8F432]/10"
          initial={false}
          animate={{ opacity: hovered ? 1 : 0 }}
          transition={{ duration: 0.2 }}
        />
        <div className="w-full flex justify-between items-center px-0.5">
          <div className="w-1.5 h-1 rounded-sm bg-white/20" />
          <div className="w-1.5 h-1 rounded-sm bg-white/20" />
          <div className="w-1.5 h-1 rounded-sm bg-white/20" />
        </div>
      </div>
      {slicePositions.map((pos, i) => (
        <motion.div
          key={pos}
          className="absolute h-6 w-[2px] bg-[#C8F432] rounded-full shadow-[0_0_8px_#C8F432]"
          style={{ left: `calc(${pos}% - 1px)` }}
          initial={false}
          animate={{
            scaleY: hovered ? 1 : 0,
            opacity: hovered ? 1 : 0,
          }}
          transition={{
            type: "spring",
            stiffness: 450,
            damping: 20,
            delay: hovered ? i * 0.06 : 0,
          }}
        />
      ))}
    </div>
  );
}

function VectorSpaceAnimation({ hovered }: { hovered: boolean }) {
  const dots = useRef([
    { id: 0, baseX: -12, baseY: -8, offsetX: -4, offsetY: -3 },
    { id: 1, baseX: 0, baseY: -12, offsetX: 2, offsetY: -5 },
    { id: 2, baseX: 12, baseY: -7, offsetX: 5, offsetY: 4 },
    { id: 3, baseX: -8, baseY: 4, offsetX: -6, offsetY: 3 },
    { id: 4, baseX: 4, baseY: 3, offsetX: 3, offsetY: -4 },
    { id: 5, baseX: 11, baseY: 10, offsetX: 5, offsetY: 5 },
    { id: 6, baseX: -4, baseY: 12, offsetX: -2, offsetY: 4 },
  ]).current;

  return (
    <div className="relative w-12 h-12 flex items-center justify-center">
      {/* Background radial glow on hover */}
      <motion.div
        className="absolute inset-0 rounded-full bg-[#C8F432]/10 blur-sm"
        animate={{ opacity: hovered ? 1 : 0, scale: hovered ? 1.2 : 0.8 }}
        transition={{ duration: 0.2 }}
      />
      {dots.map((dot, i) => (
        <motion.div
          key={dot.id}
          className={`absolute rounded-full ${
            i === 4 ? "w-[6px] h-[6px] bg-[#C8F432] shadow-[0_0_8px_#C8F432]" : "w-[4px] h-[4px] bg-white/50"
          }`}
          initial={false}
          animate={{
            x: dot.baseX + (hovered ? dot.offsetX : 0),
            y: dot.baseY + (hovered ? dot.offsetY : 0),
            scale: hovered && i === 4 ? 1.3 : 1,
          }}
          transition={{
            type: "spring",
            stiffness: 350,
            damping: 20,
            delay: i * 0.02,
          }}
        />
      ))}
    </div>
  );
}

function MultipleEmbeddingsAnimation({ hovered }: { hovered: boolean }) {
  // Grounded in our authentic production tech stack
  const models = ["all-MiniLM-L6-v2", "gemini-3.5-flash", "pgvector • 384d"];
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!hovered) {
      setIndex(0);
      return;
    }
    const interval = setInterval(() => {
      setIndex((prev) => (prev + 1) % models.length);
    }, 850);
    return () => clearInterval(interval);
  }, [hovered]);

  return (
    <div className="relative w-12 h-12 flex items-center justify-center overflow-hidden">
      <AnimatePresence mode="wait">
        <motion.span
          key={hovered ? index : "idle"}
          className="absolute text-[7px] font-mono font-semibold text-[#C8F432] whitespace-nowrap px-1.5 py-0.5 rounded bg-white/[0.06] border border-white/10"
          initial={{ opacity: 0, y: 8, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -8, scale: 0.95 }}
          transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
        >
          {hovered ? models[index] : models[0]}
        </motion.span>
      </AnimatePresence>
    </div>
  );
}

function ChatPlaygroundAnimation({ hovered }: { hovered: boolean }) {
  return (
    <div className="relative w-12 h-12 flex items-center justify-center">
      <div className="flex flex-col gap-1 items-start w-8">
        <div className="w-8 h-[3px] rounded-full bg-white/20" />
        <motion.div
          className="h-[3px] rounded-full"
          initial={false}
          animate={{
            width: hovered ? "100%" : "60%",
            backgroundColor: hovered
              ? "#C8F432"
              : "rgba(255, 255, 255, 0.25)",
            boxShadow: hovered ? "0 0 6px rgba(200, 244, 50, 0.5)" : "none",
          }}
          transition={{ duration: 0.25, ease: "easeOut" }}
        />
        <div className="w-5 h-[3px] rounded-full bg-white/20" />
      </div>
      <motion.div
        className="absolute right-1 top-3.5 w-[2px] h-3.5 bg-[#C8F432]"
        initial={false}
        animate={{
          opacity: hovered ? [1, 0, 1] : 0,
        }}
        transition={{
          duration: 0.7,
          repeat: hovered ? Infinity : 0,
          ease: "linear",
          times: [0, 0.5, 1],
        }}
      />
    </div>
  );
}

function ApiReadyAnimation({ hovered }: { hovered: boolean }) {
  const text = "POST /api/v1/query";
  const [chars, setChars] = useState(0);

  useEffect(() => {
    if (!hovered) {
      setChars(0);
      return;
    }
    let i = 0;
    const interval = setInterval(() => {
      i++;
      setChars(i);
      if (i >= text.length) clearInterval(interval);
    }, 35);
    return () => clearInterval(interval);
  }, [hovered]);

  return (
    <div className="relative w-12 h-12 flex items-center justify-center overflow-hidden">
      <span className="text-[6.5px] font-mono font-medium text-[#C8F432] whitespace-nowrap bg-black/40 px-1 py-0.5 rounded border border-white/10">
        {hovered ? text.slice(0, chars) : ">_ SDK"}
        {hovered && chars < text.length && (
          <motion.span
            className="text-white"
            animate={{ opacity: [1, 0] }}
            transition={{ duration: 0.4, repeat: Infinity }}
          >
            ▎
          </motion.span>
        )}
      </span>
    </div>
  );
}

// ─── Feature card data adhering to Miller's Law (Chunking into 6 items) ───

interface Feature {
  id: string;
  badge: string;
  title: string;
  description: string;
  Animation: React.ComponentType<{ hovered: boolean }>;
}

const features: Feature[] = [
  {
    id: "ingestion",
    badge: "01",
    title: "Multi-Source Ingestion",
    description:
      "Stream PDFs, DOCX, CSVs, and markdown through automated Trafilatura parsers.",
    Animation: MultiSourceAnimation,
  },
  {
    id: "chunking",
    badge: "02",
    title: "Smart Semantic Splitting",
    description:
      "LangChain recursive character chunking with dynamic overlap control and boundary preservation.",
    Animation: SmartChunkingAnimation,
  },
  {
    id: "vector-space",
    badge: "03",
    title: "Vector Space Inspector",
    description:
      "Explore 384-dimensional embeddings visually in PostgreSQL pgvector with real-time similarity metrics.",
    Animation: VectorSpaceAnimation,
  },
  {
    id: "embeddings",
    badge: "04",
    title: "Dual Model Pipelines",
    description:
      "Instant synthesis via Google Gemini and dense neural embeddings with sentence-transformers.",
    Animation: MultipleEmbeddingsAnimation,
  },
  {
    id: "chat-playground",
    badge: "05",
    title: "Verified Citations",
    description:
      "Sub-second RAG response generation backed by verbatim source chunks and cosine relevance confidence.",
    Animation: ChatPlaygroundAnimation,
  },
  {
    id: "api-ready",
    badge: "06",
    title: "Production REST & SDK",
    description:
      "FastAPI backend with streaming SSE endpoints, Bearer auth, and typed client libraries.",
    Animation: ApiReadyAnimation,
  },
];

function FeatureCard({
  feature,
  index,
}: {
  feature: Feature;
  index: number;
}) {
  const [hovered, setHovered] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 24 }}
      animate={inView ? { opacity: 1, y: 0 } : { opacity: 0, y: 24 }}
      transition={{
        duration: 0.45,
        ease: [0.16, 1, 0.3, 1],
        delay: index * 0.06,
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      whileHover={{ y: -5 }}
      whileTap={{ scaleX: 1.02, scaleY: 0.97 }} // Principle 1: Squash & Stretch
      className="group relative bg-[#0D0D0D]/90 border border-white/10 rounded-2xl p-6 md:p-7 transition-all duration-200 cursor-pointer overflow-hidden shadow-[0_8px_30px_rgba(0,0,0,0.6)] before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent"
    >
      {/* Principle 11: Solid Drawing in 3D & Radial Aura */}
      <motion.div
        className="pointer-events-none absolute -inset-px rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        style={{
          background:
            "radial-gradient(400px circle at 50% 0%, rgba(200, 244, 50, 0.12), transparent 70%)",
        }}
      />

      {/* Principle 8: Secondary Action Border Glow */}
      <motion.div
        className="pointer-events-none absolute inset-0 rounded-2xl border border-[#C8F432]/0 group-hover:border-[#C8F432]/30 transition-colors duration-200"
      />

      {/* Content wrapper */}
      <div className="relative z-10 flex flex-col h-full justify-between">
        <div>
          {/* Top Row: Icon + Badge Index */}
          <div className="flex items-center justify-between mb-5">
            {/* Tactile Icon Box */}
            <div className="w-12 h-12 rounded-xl bg-white/[0.04] border border-white/10 group-hover:border-[#C8F432]/40 group-hover:bg-[#C8F432]/[0.06] flex items-center justify-center transition-all duration-200 shadow-inner">
              <feature.Animation hovered={hovered} />
            </div>

            {/* Chunk Index (Principle 16: Miller's Law) */}
            <span className="font-mono text-xs font-semibold text-white/30 group-hover:text-[#C8F432] transition-colors duration-200">
              {feature.badge}
            </span>
          </div>

          {/* Title */}
          <h3 className="font-heading text-white text-base md:text-lg font-semibold mb-2.5 tracking-tight flex items-center justify-between">
            <span>{feature.title}</span>
            {/* Principle 2: Anticipation Wind-up on hover arrow */}
            <motion.span
              animate={{
                x: hovered ? 2 : 0,
                y: hovered ? -2 : 0,
                opacity: hovered ? 1 : 0.4,
              }}
              transition={{ type: "spring", stiffness: 400, damping: 20 }}
            >
              <ArrowUpRight className="w-4 h-4 text-[#C8F432]" />
            </motion.span>
          </h3>

          {/* Description */}
          <p className="font-body text-white/50 text-sm leading-relaxed group-hover:text-white/70 transition-colors duration-200">
            {feature.description}
          </p>
        </div>

        {/* Bottom subtle baseline status */}
        <div className="mt-5 pt-3.5 border-t border-white/[0.05] flex items-center justify-between text-[11px] font-mono text-white/30">
          <span className="group-hover:text-white/50 transition-colors">LOCUS CORE</span>
          <span className="text-[#C8F432]/80 opacity-0 group-hover:opacity-100 transition-opacity duration-200">Active</span>
        </div>
      </div>
    </motion.div>
  );
}

// ─── Features Grid Section ──────────────────────────────────────────

export default function FeaturesGrid() {
  const headerRef = useRef<HTMLDivElement>(null);
  const headerInView = useInView(headerRef, { once: true, margin: "-40px" });

  return (
    <section id="features" className="bg-[#080808] py-24 px-4 sm:px-6 relative border-t border-white/5">
      {/* Background ambient mesh */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(200,244,50,0.04),transparent)]" />

      <div className="max-w-6xl mx-auto relative z-10">
        {/* Header (Principle 3: Staging the Focus) */}
        <motion.div
          ref={headerRef}
          className="text-center max-w-2xl mx-auto mb-16"
          initial={{ opacity: 0, y: 16 }}
          animate={
            headerInView
              ? { opacity: 1, y: 0 }
              : { opacity: 0, y: 16 }
          }
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.05] border border-white/10 text-[#C8F432] text-xs font-mono mb-4">
            <Cpu className="w-3.5 h-3.5" />
            <span>ARCHITECTURAL CAPABILITIES</span>
          </div>

          <h2 className="font-heading text-3xl md:text-4xl font-bold text-white tracking-tight mb-4">
            Everything you need for verified RAG
          </h2>
          <p className="font-body text-white/50 text-sm md:text-base leading-relaxed">
            From ingestion pipelines to interactive vector inspection and low-latency inference, built for accuracy.
          </p>
        </motion.div>

        {/* Grid (Principle 16: Miller's Law - 6 chunked cards) */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((feature, i) => (
            <FeatureCard key={feature.id} feature={feature} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
