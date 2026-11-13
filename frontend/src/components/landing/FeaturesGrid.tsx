"use client";

import { useState, useEffect, useRef } from "react";
import { motion, useInView, AnimatePresence } from "framer-motion";

// ─── Micro-interaction components ───────────────────────────────────

function MultiSourceAnimation({ hovered }: { hovered: boolean }) {
  const files = [
    { label: "PDF", x: -18, y: -14 },
    { label: "CSV", x: 0, y: -18 },
    { label: "DOC", x: 18, y: -14 },
  ];

  return (
    <div className="relative w-10 h-10 flex items-center justify-center">
      {/* Folder icon */}
      <svg
        width="18"
        height="16"
        viewBox="0 0 18 16"
        fill="none"
        className="absolute z-10"
      >
        <path
          d="M1 4V13C1 14.1 1.9 15 3 15H15C16.1 15 17 14.1 17 13V6C17 4.9 16.1 4 15 4H9L7 2H3C1.9 2 1 2.9 1 4Z"
          stroke="currentColor"
          strokeWidth="1.2"
          className="text-white/40"
        />
      </svg>
      {/* Flying file icons */}
      {files.map((file, i) => (
        <motion.div
          key={file.label}
          className="absolute z-20"
          initial={false}
          animate={{
            x: hovered ? 0 : file.x,
            y: hovered ? 0 : file.y,
            opacity: hovered ? 0 : 1,
            scale: hovered ? 0.3 : 1,
          }}
          transition={{
            duration: 0.45,
            ease: "easeOut",
            delay: hovered ? i * 0.06 : 0,
          }}
        >
          <div className="w-4 h-5 rounded-[2px] bg-white/10 border border-white/20 flex items-center justify-center">
            <span className="text-[5px] font-mono text-white/50 leading-none">
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
    <div className="relative w-10 h-10 flex items-center justify-center">
      <div className="w-8 h-2 bg-white/10 rounded-full relative overflow-hidden">
        <motion.div
          className="absolute inset-0 bg-white/[0.07]"
          initial={false}
          animate={{ opacity: hovered ? 1 : 0 }}
          transition={{ duration: 0.3 }}
        />
      </div>
      {slicePositions.map((pos, i) => (
        <motion.div
          key={pos}
          className="absolute h-5 w-[1.5px] bg-[#C8F432]/60"
          style={{ left: `calc(${pos}% - 0.75px)` }}
          initial={false}
          animate={{
            scaleY: hovered ? 1 : 0,
            opacity: hovered ? 1 : 0,
          }}
          transition={{
            duration: 0.35,
            ease: "easeOut",
            delay: hovered ? i * 0.08 : 0,
          }}
        />
      ))}
    </div>
  );
}

function VectorSpaceAnimation({ hovered }: { hovered: boolean }) {
  const dots = useRef(
    Array.from({ length: 7 }, (_, i) => ({
      id: i,
      baseX: (i % 3) * 10 - 10,
      baseY: Math.floor(i / 3) * 10 - 8,
      offsetX: (Math.random() - 0.5) * 12,
      offsetY: (Math.random() - 0.5) * 12,
    }))
  ).current;

  return (
    <div className="relative w-10 h-10 flex items-center justify-center">
      {dots.map((dot) => (
        <motion.div
          key={dot.id}
          className="absolute w-[4px] h-[4px] rounded-full bg-white/40"
          initial={false}
          animate={{
            x: dot.baseX + (hovered ? dot.offsetX : 0),
            y: dot.baseY + (hovered ? dot.offsetY : 0),
          }}
          transition={{
            duration: 0.5,
            ease: "easeOut",
          }}
        />
      ))}
    </div>
  );
}

function MultipleEmbeddingsAnimation({ hovered }: { hovered: boolean }) {
  const models = ["text-embedding-3", "bge-small-en", "embed-v3"];
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!hovered) {
      setIndex(0);
      return;
    }
    const interval = setInterval(() => {
      setIndex((prev) => (prev + 1) % models.length);
    }, 900);
    return () => clearInterval(interval);
  }, [hovered]);

  return (
    <div className="relative w-10 h-10 flex items-center justify-center overflow-hidden">
      <AnimatePresence mode="wait">
        <motion.span
          key={hovered ? index : "idle"}
          className="absolute text-[6px] font-mono text-white/50 whitespace-nowrap"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
        >
          {hovered ? models[index] : models[0]}
        </motion.span>
      </AnimatePresence>
    </div>
  );
}

function ChatPlaygroundAnimation({ hovered }: { hovered: boolean }) {
  return (
    <div className="relative w-10 h-10 flex items-center justify-center">
      {/* Text lines */}
      <div className="flex flex-col gap-[3px] items-start">
        <div className="w-7 h-[3px] rounded-full bg-white/10" />
        <motion.div
          className="w-5 h-[3px] rounded-full"
          initial={false}
          animate={{
            backgroundColor: hovered
              ? "rgba(200, 244, 50, 0.3)"
              : "rgba(255, 255, 255, 0.1)",
          }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        />
        <div className="w-6 h-[3px] rounded-full bg-white/10" />
      </div>
      {/* Cursor blink */}
      <motion.div
        className="absolute right-[6px] top-[10px] w-[1.5px] h-3 bg-[#C8F432]"
        initial={false}
        animate={{
          opacity: hovered ? [1, 0, 1] : 0,
        }}
        transition={{
          duration: 0.8,
          repeat: hovered ? Infinity : 0,
          ease: "linear",
          times: [0, 0.5, 1],
        }}
      />
    </div>
  );
}

function ApiReadyAnimation({ hovered }: { hovered: boolean }) {
  const text = 'GET /api/v1/query';
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
    }, 45);
    return () => clearInterval(interval);
  }, [hovered]);

  return (
    <div className="relative w-10 h-10 flex items-center justify-center overflow-hidden">
      <span className="text-[5.5px] font-mono text-[#C8F432]/70 whitespace-nowrap">
        {hovered ? text.slice(0, chars) : ">_"}
      </span>
      {hovered && chars < text.length && (
        <motion.span
          className="text-[5.5px] font-mono text-white/60"
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.5, repeat: Infinity }}
        >
          ▎
        </motion.span>
      )}
    </div>
  );
}

// ─── Feature card ───────────────────────────────────────────────────

interface Feature {
  title: string;
  description: string;
  Animation: React.ComponentType<{ hovered: boolean }>;
}

const features: Feature[] = [
  {
    title: "Multi-Source Ingestion",
    description:
      "Connect PDFs, databases, CSVs, DOCX — all in one pipeline.",
    Animation: MultiSourceAnimation,
  },
  {
    title: "Smart Chunking",
    description:
      "Intelligent splitting with overlap control and token-aware boundaries.",
    Animation: SmartChunkingAnimation,
  },
  {
    title: "Vector Space Viewer",
    description:
      "Explore your embeddings visually. See clusters, search by similarity.",
    Animation: VectorSpaceAnimation,
  },
  {
    title: "Multiple Embeddings",
    description:
      "Switch between OpenAI, BGE, Cohere models with one click.",
    Animation: MultipleEmbeddingsAnimation,
  },
  {
    title: "Chat Playground",
    description:
      "Test RAG queries with citation highlighting and source tracking.",
    Animation: ChatPlaygroundAnimation,
  },
  {
    title: "API Ready",
    description:
      "Production REST API with auth, rate limiting, and SDKs.",
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
        duration: 0.5,
        ease: "easeOut",
        delay: index * 0.08,
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="group relative bg-white/[0.03] border border-white/10 rounded-2xl p-6 transition-colors duration-300 hover:border-white/20"
    >
      {/* Subtle lift on hover */}
      <motion.div
        className="absolute inset-0 rounded-2xl"
        initial={false}
        animate={{ y: hovered ? -2 : 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
      />

      {/* Content sits above the lift layer */}
      <motion.div
        className="relative z-10"
        initial={false}
        animate={{ y: hovered ? -2 : 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
      >
        {/* Icon area */}
        <div className="w-10 h-10 bg-white/[0.06] rounded-lg flex items-center justify-center mb-4">
          <feature.Animation hovered={hovered} />
        </div>

        {/* Title */}
        <h3 className="font-heading text-white text-[15px] font-semibold mb-2 tracking-[-0.01em]">
          {feature.title}
        </h3>

        {/* Description */}
        <p className="font-body text-white/40 text-sm leading-relaxed">
          {feature.description}
        </p>
      </motion.div>
    </motion.div>
  );
}

// ─── Features Grid Section ──────────────────────────────────────────

export default function FeaturesGrid() {
  const headerRef = useRef<HTMLDivElement>(null);
  const headerInView = useInView(headerRef, { once: true, margin: "-40px" });

  return (
    <section id="features" className="bg-[#080808] py-20 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <motion.div
          ref={headerRef}
          className="text-center mb-14"
          initial={{ opacity: 0, y: 16 }}
          animate={
            headerInView
              ? { opacity: 1, y: 0 }
              : { opacity: 0, y: 16 }
          }
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          <h2 className="font-heading text-3xl font-semibold text-white tracking-[-0.02em] mb-3">
            Everything you need
          </h2>
          <p className="font-body text-white/50 text-base">
            Built for developers who want RAG that works.
          </p>
        </motion.div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((feature, i) => (
            <FeatureCard key={feature.title} feature={feature} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
