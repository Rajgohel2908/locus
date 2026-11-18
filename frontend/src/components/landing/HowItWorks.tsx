"use client";

import { useRef, useEffect, useState } from "react";
import {
  motion,
  useScroll,
  useTransform,
  useSpring,
  AnimatePresence,
} from "framer-motion";
import { FileUp, Cpu, Sparkles, Check, ArrowRight } from "lucide-react";

/* ────────────────────────────────────────────────────────────────── */
/*  Micro-animation: Shimmer loading bar (Step 1)                     */
/* ────────────────────────────────────────────────────────────────── */
function IngestionProgress() {
  return (
    <div className="mt-4 space-y-2">
      <div className="flex items-center justify-between text-[11px] font-mono text-white/50">
        <span className="flex items-center gap-1.5 text-[#C8F432]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#C8F432] animate-pulse" />
          Trafilatura Parsing
        </span>
        <span>100% Parsed</span>
      </div>
      <div className="h-2 w-full rounded-full bg-white/10 overflow-hidden relative">
        <motion.div
          className="h-full rounded-full bg-[#C8F432]"
          initial={{ width: "0%" }}
          animate={{ width: "100%" }}
          transition={{
            duration: 1.8,
            repeat: Infinity,
            repeatDelay: 0.8,
            ease: [0.16, 1, 0.3, 1], // Slow in & slow out
          }}
        />
      </div>
      <div className="flex gap-2 text-[10px] font-mono text-white/40">
        <span className="px-1.5 py-0.5 rounded bg-white/[0.06] border border-white/10">research_paper.pdf</span>
        <span className="px-1.5 py-0.5 rounded bg-white/[0.06] border border-white/10">34,120 words</span>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────── */
/*  Micro-animation: Equalizer bars (Step 2)                          */
/* ────────────────────────────────────────────────────────────────── */
function EmbeddingTelemetry() {
  const barHeights = [
    [10, 26, 16, 28, 12],
    [22, 12, 28, 8, 24],
    [16, 30, 10, 22, 18],
    [28, 16, 24, 14, 26],
    [14, 28, 18, 30, 12],
  ];

  return (
    <div className="mt-4 space-y-3">
      <div className="flex items-end gap-1.5 h-8">
        {barHeights.map((heights, i) => (
          <motion.div
            key={i}
            className="w-1.5 rounded-full bg-[#C8F432]"
            animate={{ height: heights.map((h) => `${h}px`) }}
            transition={{
              duration: 1.4,
              repeat: Infinity,
              ease: "easeInOut",
              repeatType: "mirror",
              delay: i * 0.12,
            }}
          />
        ))}
        <div className="ml-3 flex flex-col justify-end">
          <span className="text-xs font-mono text-white/80 font-medium">sentence-transformers</span>
          <span className="text-[10px] font-mono text-[#C8F432]">all-MiniLM-L6-v2 • 384 dims</span>
        </div>
      </div>
      <div className="flex items-center justify-between text-[11px] font-mono text-white/40 pt-1 border-t border-white/5">
        <span>PostgreSQL pgvector</span>
        <span className="text-white/70">84 chunks stored</span>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────── */
/*  Micro-animation: Typewriter text with Citation (Step 3)           */
/* ────────────────────────────────────────────────────────────────── */
function SynthesisPreview() {
  const text = "Gemini synthesized answer with verbatim citation [paper.pdf #P4]";
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    let i = 0;
    setDisplayed("");
    setDone(false);
    const interval = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) {
        clearInterval(interval);
        setDone(true);
      }
    }, 35);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="mt-4 rounded-xl bg-black/40 border border-white/10 px-3.5 py-3">
      <p className="text-xs font-mono text-white/90 min-h-[1.5rem] leading-relaxed">
        {displayed}
        {!done && (
          <motion.span
            className="inline-block w-[2px] h-3.5 bg-[#C8F432] ml-1 align-middle"
            animate={{ opacity: [1, 0] }}
            transition={{ duration: 0.4, repeat: Infinity, repeatType: "mirror" }}
          />
        )}
      </p>
      {done && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-2 flex items-center justify-between text-[10px] font-mono text-[#C8F432] pt-2 border-t border-white/5"
        >
          <span>Confidence: 0.942</span>
          <span>Latency: 148ms</span>
        </motion.div>
      )}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────── */
/*  Step node (circle on the timeline)                                */
/* ────────────────────────────────────────────────────────────────── */
function StepNode({
  index,
  active,
}: {
  index: number;
  active: boolean;
}) {
  return (
    <div className="relative flex items-center justify-center w-12 h-12 z-10">
      {/* Principle 8: Secondary Action & Radar Ring */}
      <AnimatePresence>
        {active && (
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-[#C8F432]/60"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: [1, 1.8], opacity: [0.7, 0] }}
            transition={{
              duration: 1.8,
              repeat: Infinity,
              ease: "easeOut",
            }}
          />
        )}
      </AnimatePresence>

      {/* Circle Button with Squash and Stretch (Spring Physics with Overshoot) */}
      <motion.div
        className="w-10 h-10 rounded-full flex items-center justify-center font-heading font-bold text-sm shadow-xl border border-white/10"
        initial={false}
        animate={
          active
            ? {
                scale: 1.05,
                backgroundColor: "#C8F432",
                color: "#080808",
                borderColor: "#C8F432",
                boxShadow: "0 0 20px rgba(200, 244, 50, 0.5)",
              }
            : {
                scale: 0.92,
                backgroundColor: "rgba(255,255,255,0.06)",
                color: "rgba(245,245,240,0.4)",
                borderColor: "rgba(255,255,255,0.1)",
                boxShadow: "none",
              }
        }
        transition={{ type: "spring", stiffness: 450, damping: 16 }}
      >
        {index + 1}
      </motion.div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────── */
/*  Step Card Component                                               */
/* ────────────────────────────────────────────────────────────────── */
const steps = [
  {
    stepNumber: "01",
    title: "Ingest & Extract",
    description:
      "Upload PDFs, DOCX, CSVs or link PostgreSQL databases. Trafilatura and PyMuPDF extract clean body text without junk headers or advertising clutter.",
    icon: FileUp,
    animation: <IngestionProgress />,
  },
  {
    stepNumber: "02",
    title: "Chunk & Embed in pgvector",
    description:
      "LangChain splits your documents with semantic boundary awareness. Dense 384-dimensional vectors are generated by all-MiniLM-L6-v2 and stored directly in PostgreSQL.",
    icon: Cpu,
    animation: <EmbeddingTelemetry />,
  },
  {
    stepNumber: "03",
    title: "Retrieve & Synthesize",
    description:
      "Query with sub-second cosine similarity. Google Gemini analyzes matched chunks and synthesizes verified, hallucination-free answers with verbatim citations.",
    icon: Sparkles,
    animation: <SynthesisPreview />,
  },
];

function StepCard({
  step,
  active,
}: {
  step: (typeof steps)[number];
  active: boolean;
}) {
  const Icon = step.icon;

  return (
    <motion.div
      className={`group relative bg-[#0D0D0D]/95 border rounded-2xl p-6 md:p-7 max-w-md w-full transition-all duration-300 shadow-[0_12px_40px_rgba(0,0,0,0.6)] before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent ${
        active
          ? "border-[#C8F432]/40 shadow-[0_0_30px_rgba(200,244,50,0.1)]"
          : "border-white/10 opacity-60"
      }`}
      whileHover={{
        y: -5,
        scale: 1.01,
        borderColor: "rgba(200,244,50,0.5)",
        opacity: 1,
      }}
      whileTap={{ scale: 0.98 }} // Squash & Stretch
      transition={{ type: "spring", stiffness: 350, damping: 22 }}
    >
      {/* Icon + Step Title + Number */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-white text-black flex items-center justify-center shadow-md">
            <Icon className="w-4 h-4 text-black" strokeWidth={2} />
          </div>
          <h3 className="font-heading font-bold text-lg text-white">
            {step.title}
          </h3>
        </div>
        <span className="font-mono text-xs text-white/30 font-semibold group-hover:text-[#C8F432] transition-colors">
          {step.stepNumber}
        </span>
      </div>

      <p className="text-sm text-white/60 font-body leading-relaxed">
        {step.description}
      </p>

      {/* Micro-animation (Follow Through & Overlapping Action) */}
      {active && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {step.animation}
        </motion.div>
      )}
    </motion.div>
  );
}

function StepRow({
  step,
  index,
  active,
}: {
  step: (typeof steps)[number];
  index: number;
  active: boolean;
}) {
  const isEven = index % 2 === 0;

  return (
    <div className="relative grid grid-cols-[48px_1fr] md:grid-cols-[1fr_48px_1fr] gap-4 md:gap-10 items-start">
      {/* Desktop left column */}
      <div className="hidden md:flex justify-end">
        {isEven ? (
          <StepCard step={step} active={active} />
        ) : (
          <div />
        )}
      </div>

      {/* Node column */}
      <div className="flex justify-center">
        <StepNode index={index} active={active} />
      </div>

      {/* Desktop right column */}
      <div className="hidden md:flex justify-start">
        {!isEven ? (
          <StepCard step={step} active={active} />
        ) : (
          <div />
        )}
      </div>

      {/* Mobile card (always right of node) */}
      <div className="md:hidden">
        <StepCard step={step} active={active} />
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Main component                                                     */
/* ================================================================== */
export default function HowItWorks() {
  const containerRef = useRef<HTMLDivElement>(null);

  /* Scroll tracking */
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 0.75", "end 0.45"],
  });

  /* Smooth spring line height (Principle 6: Slow In & Slow Out) */
  const lineHeight = useSpring(useTransform(scrollYProgress, [0, 1], ["0%", "100%"]), {
    stiffness: 140,
    damping: 28,
  });

  const [activeSteps, setActiveSteps] = useState<boolean[]>([
    true,
    false,
    false,
  ]);

  useEffect(() => {
    const unsubscribe = scrollYProgress.on("change", (v) => {
      setActiveSteps([v >= 0, v > 0.32, v > 0.65]);
    });
    return unsubscribe;
  }, [scrollYProgress]);

  return (
    <section id="how-it-works" className="relative py-24 overflow-hidden bg-[#080808] border-t border-white/5">
      {/* Background ambient spotlight */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_50%_50%,rgba(200,244,50,0.03),transparent)]" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 relative z-10">
        {/* Section header (Principle 3: Staging the Focus) */}
        <motion.div
          className="text-center max-w-2xl mx-auto mb-20"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.05] border border-white/10 text-white/70 text-xs font-mono mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-[#C8F432]" />
            STEP-BY-STEP PIPELINE
          </div>
          <h2 className="text-3xl md:text-4xl font-heading font-bold text-white tracking-tight">
            How LOCUS indexes knowledge
          </h2>
          <p className="mt-3 text-white/50 font-body text-sm md:text-base leading-relaxed">
            Three deterministic stages: from raw heterogeneous documents to citation-backed intelligence.
          </p>
        </motion.div>

        {/* Steps container */}
        <div ref={containerRef} className="relative space-y-28 md:space-y-36">
          {/* Timeline track */}
          <div className="absolute left-[24px] md:left-1/2 md:-translate-x-1/2 top-4 bottom-4 w-[2px]">
            {/* Background track */}
            <div className="absolute inset-0 bg-white/10 rounded-full" />

            {/* Active lime line with glow */}
            <motion.div
              className="absolute top-0 left-0 w-full rounded-full bg-[#C8F432]"
              style={{
                height: lineHeight,
                boxShadow: "0 0 12px #C8F432",
              }}
            />
          </div>

          {/* Step rows */}
          {steps.map((step, i) => (
            <StepRow
              key={step.title}
              step={step}
              index={i}
              active={activeSteps[i]}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
