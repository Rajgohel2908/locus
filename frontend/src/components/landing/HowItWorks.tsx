"use client";

import { useRef, useEffect, useState } from "react";
import {
  motion,
  useScroll,
  useTransform,
  useInView,
  useMotionValue,
  useSpring,
  AnimatePresence,
} from "framer-motion";
import { Database, Scissors, MessageSquareDot, type LucideIcon } from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Micro-animation: Shimmer loading bar (Step 1)                     */
/* ------------------------------------------------------------------ */
function ShimmerBar() {
  return (
    <div className="mt-4 h-2 w-full rounded-full bg-white/10 overflow-hidden">
      <motion.div
        className="h-full w-1/3 rounded-full bg-[#C8F432]"
        animate={{ x: ["-100%", "300%"] }}
        transition={{
          duration: 1.8,
          repeat: Infinity,
          ease: "easeInOut",
          repeatDelay: 0.4,
        }}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Micro-animation: Equalizer bars (Step 2)                          */
/* ------------------------------------------------------------------ */
function EqualizerBars() {
  const barHeights = [
    [12, 28, 18, 32, 14],
    [24, 14, 30, 10, 26],
    [18, 32, 12, 24, 20],
    [30, 18, 26, 16, 28],
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
              duration: 1.6,
              repeat: Infinity,
              ease: "easeInOut",
              repeatType: "mirror",
              delay: i * 0.15,
            }}
          />
        ))}
      </div>
      <p className="text-xs font-mono text-white/40">
        Embedding 1,234 chunks...
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Micro-animation: Typewriter text (Step 3)                         */
/* ------------------------------------------------------------------ */
function TypewriterText() {
  const text = "→ Answer with citation [report.pdf]";
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
    }, 45);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="mt-4 rounded-xl bg-[#F5F5F0]/[0.08] px-4 py-3">
      <p className="text-sm font-mono text-[#F5F5F0]/80 min-h-[1.25rem]">
        {displayed}
        {!done && (
          <motion.span
            className="inline-block w-[2px] h-4 bg-[#C8F432] ml-0.5 align-middle"
            animate={{ opacity: [1, 0] }}
            transition={{ duration: 0.5, repeat: Infinity, repeatType: "mirror" }}
          />
        )}
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step node (circle on the timeline)                                */
/* ------------------------------------------------------------------ */
function StepNode({
  index,
  active,
}: {
  index: number;
  active: boolean;
}) {
  return (
    <div className="relative flex items-center justify-center w-10 h-10 z-10">
      {/* Pulsing ring */}
      <AnimatePresence>
        {active && (
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-[#C8F432]/60"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: [1, 1.6], opacity: [0.6, 0] }}
            transition={{
              duration: 1.6,
              repeat: Infinity,
              ease: "easeOut",
            }}
          />
        )}
      </AnimatePresence>

      {/* Circle */}
      <motion.div
        className="w-10 h-10 rounded-full flex items-center justify-center font-heading font-bold text-sm"
        initial={{ scale: 0, backgroundColor: "rgba(255,255,255,0.1)" }}
        animate={
          active
            ? {
                scale: 1,
                backgroundColor: "#C8F432",
                color: "#080808",
              }
            : {
                scale: 1,
                backgroundColor: "rgba(255,255,255,0.1)",
                color: "rgba(245,245,240,0.5)",
              }
        }
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        {index + 1}
      </motion.div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step card                                                          */
/* ------------------------------------------------------------------ */
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
      className="bg-white/[0.04] backdrop-blur border border-white/10 rounded-2xl p-6 max-w-md w-full"
      initial={{ opacity: 0, y: 24 }}
      animate={active ? { opacity: 1, y: 0 } : { opacity: 0.4, y: 0 }}
      whileHover={{
        y: -4,
        borderColor: "rgba(200,244,50,0.4)",
        transition: { duration: 0.25 },
      }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      {/* Icon + Title */}
      <div className="flex items-center gap-3 mb-2">
        <div className="w-8 h-8 rounded-lg bg-white text-black flex items-center justify-center shadow-md">
          <Icon className="w-4 h-4" strokeWidth={1.5} />
        </div>
        <h3 className="font-heading font-bold text-lg text-[#F5F5F0]">
          {step.title}
        </h3>
      </div>

      <p className="text-sm text-[#F5F5F0]/60 font-body leading-relaxed">
        {step.description}
      </p>

      {/* Micro-animation */}
      {active && step.animation}
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step data                                                          */
/* ------------------------------------------------------------------ */
const steps = [
  {
    title: "Connect",
    description:
      "Drop PDFs, DOCX, CSV or connect Postgres / MongoDB. We auto-detect schema.",
    icon: Database,
    animation: <ShimmerBar />,
  },
  {
    title: "Vectorize",
    description:
      "Smart chunking, cleaning, embedding. See tokens & vectors live.",
    icon: Scissors,
    animation: <EqualizerBars />,
  },
  {
    title: "Chat & Deploy",
    description:
      "Test in playground with citations. Get API key or embed widget.",
    icon: MessageSquareDot,
    animation: <TypewriterText />,
  },
];

/* ------------------------------------------------------------------ */
/*  Single step row                                                    */
/* ------------------------------------------------------------------ */
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
    <div className="relative grid grid-cols-[40px_1fr] md:grid-cols-[1fr_40px_1fr] gap-4 md:gap-8 items-start">
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
  const timelineRef = useRef<HTMLDivElement>(null);

  /* Scroll tracking */
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 0.7", "end 0.5"],
  });

  /* Smooth line height */
  const lineHeight = useSpring(useTransform(scrollYProgress, [0, 1], ["0%", "100%"]), {
    stiffness: 120,
    damping: 30,
  });

  /* Determine which steps are active based on scroll progress */
  const [activeSteps, setActiveSteps] = useState<boolean[]>([
    false,
    false,
    false,
  ]);

  useEffect(() => {
    const unsubscribe = scrollYProgress.on("change", (v) => {
      setActiveSteps([v > 0.05, v > 0.35, v > 0.65]);
    });
    return unsubscribe;
  }, [scrollYProgress]);

  return (
    <section id="how-it-works" className="relative py-20 overflow-hidden bg-[#080808]">
      <div className="max-w-5xl mx-auto px-4 sm:px-6">
        {/* Section header */}
        <motion.h2
          className="text-3xl font-heading font-bold text-center text-[#F5F5F0] mb-20"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          How it works
        </motion.h2>

        {/* Steps container */}
        <div ref={containerRef} className="relative space-y-32">
          {/* Timeline track */}
          <div
            ref={timelineRef}
            className="absolute left-[20px] md:left-1/2 md:-translate-x-1/2 top-0 bottom-0 w-[2px]"
          >
            {/* Background track */}
            <div className="absolute inset-0 bg-white/10 rounded-full" />

            {/* Active lime line */}
            <motion.div
              className="absolute top-0 left-0 w-full rounded-full bg-[#C8F432]"
              style={{
                height: lineHeight,
                boxShadow: "0 0 10px #C8F432",
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
