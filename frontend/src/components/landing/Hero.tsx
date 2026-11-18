"use client";

import { motion } from "framer-motion";
import { FileText, Sparkles, ArrowRight, Play, ChevronDown } from "lucide-react";

// Deterministic dot coordinates for the vector field
const DOT_COORDS = [
  { left: "32%", top: "18%", delay: 0.1, dur: 2.4 },
  { left: "44%", top: "12%", delay: 0.3, dur: 3.1 },
  { left: "56%", top: "22%", delay: 0.2, dur: 2.7 },
  { left: "70%", top: "15%", delay: 0.4, dur: 3.3 },
  { left: "82%", top: "25%", delay: 0.6, dur: 2.5 },
  { left: "38%", top: "35%", delay: 0.2, dur: 3.0 },
  { left: "50%", top: "30%", delay: 0.5, dur: 2.2 },
  { left: "68%", top: "36%", delay: 0.3, dur: 2.8 },
  { left: "85%", top: "42%", delay: 0.7, dur: 3.4 },
  { left: "35%", top: "52%", delay: 0.4, dur: 2.6 },
  { left: "48%", top: "48%", delay: 0.1, dur: 3.2 },
  { left: "72%", top: "54%", delay: 0.5, dur: 2.9 },
  { left: "88%", top: "60%", delay: 0.3, dur: 3.5 },
  { left: "40%", top: "68%", delay: 0.6, dur: 2.3 },
  { left: "54%", top: "65%", delay: 0.2, dur: 3.1 },
  { left: "65%", top: "72%", delay: 0.4, dur: 2.7 },
  { left: "78%", top: "78%", delay: 0.7, dur: 3.3 },
  { left: "30%", top: "82%", delay: 0.3, dur: 2.5 },
  { left: "46%", top: "80%", delay: 0.5, dur: 3.0 },
  { left: "62%", top: "86%", delay: 0.1, dur: 2.8 },
  { left: "84%", top: "85%", delay: 0.4, dur: 3.2 },
  { left: "58%", top: "40%", delay: 0.2, dur: 2.4 },
  { left: "76%", top: "28%", delay: 0.6, dur: 3.6 },
  { left: "90%", top: "32%", delay: 0.3, dur: 2.9 },
];

export default function Hero() {
  const scrollToPlayground = () => {
    const el = document.getElementById("playground");
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  const scrollToHowItWorks = () => {
    const el = document.getElementById("how-it-works");
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section className="relative min-h-[90vh] bg-[#080808] overflow-hidden flex items-center pt-24 pb-16">
      {/* 1. Subtle grid background - full hero, not boxed */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: `
            linear-gradient(to right, rgba(255, 255, 255, 0.035) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255, 255, 255, 0.035) 1px, transparent 1px)
          `,
          backgroundSize: "48px 48px",
        }}
      />

      {/* Principle 3: Staging the Focus — Ambient glow centers the eye on hero centerpiece */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[850px] h-[850px] bg-[radial-gradient(circle_at_center,rgba(200,244,50,0.11)_0%,transparent_60%)] blur-3xl pointer-events-none" />

      {/* Bottom gradient fade so the hero seamlessly melts into the Social Proof strip */}
      <div className="absolute bottom-0 left-0 right-0 h-36 bg-gradient-to-t from-[#080808] to-transparent z-10 pointer-events-none" />

      <div className="relative z-20 max-w-7xl mx-auto w-full px-6 grid md:grid-cols-2 gap-12 lg:gap-16 items-center">
        {/* ---- LEFT: Copy ---- */}
        <div>
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            /* Principle 6: Slow in & slow out */
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            className="inline-flex items-center gap-2 bg-white/[0.06] border border-white/10 rounded-full px-3.5 py-1 text-xs text-white/70 mb-6 font-mono"
          >
            <span className="w-2 h-2 bg-[#C8F432] rounded-full animate-pulse shadow-[0_0_8px_#C8F432]" />
            Final Year Project • Live at Exhibition
          </motion.div>

          {/* Heading with Principle 16: Miller's Law (Chunked structure) */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
            className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-white font-heading leading-[1.05]"
          >
            Turn your files
            <br />
            into a RAG
            <br />
            <span className="text-white/40">that answers.</span>
          </motion.h1>

          {/* Subtext */}
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.16, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
            className="mt-6 text-white/60 text-base md:text-lg max-w-md font-body leading-relaxed"
          >
            Connect DBs, PDFs, CSVs. We chunk, embed, and make it chat-ready with citations.
          </motion.p>

          {/* CTA Buttons — Principle 13: Fitts's Law + Principle 15: Hick's Law (Clear choice) */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.24, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="mt-8 flex flex-wrap items-center gap-3.5"
          >
            {/* Primary CTA with Principle 1: Squash & stretch + Principle 2: Anticipation */}
            <motion.button
              onClick={scrollToPlayground}
              whileHover={{ scale: 1.025 }}
              whileTap={{ scaleX: 1.06, scaleY: 0.92 }}
              transition={{ type: "spring", stiffness: 500, damping: 22 }}
              className="group relative bg-[#C8F432] text-black px-7 py-3.5 rounded-full font-semibold font-body text-sm hover:brightness-105 active:brightness-95 transition-all shadow-[0_0_24px_rgba(200,244,50,0.35)] flex items-center gap-2 cursor-pointer overflow-hidden"
            >
              <span>Try Playground</span>
              {/* Principle 2: Anticipation wind-up on arrow */}
              <motion.div
                className="flex items-center"
                initial={{ x: 0 }}
                whileHover={{ x: [0, -2, 4] }}
                transition={{ duration: 0.22, ease: "easeInOut" }}
              >
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" strokeWidth={1.8} />
              </motion.div>
            </motion.button>

            {/* Secondary CTA — Principle 14: Bigger Hit Area */}
            <motion.button
              onClick={scrollToHowItWorks}
              whileHover={{ scale: 1.02, backgroundColor: "rgba(255, 255, 255, 0.14)" }}
              whileTap={{ scaleX: 1.04, scaleY: 0.94 }}
              transition={{ type: "spring", stiffness: 500, damping: 25 }}
              className="relative bg-white/10 border border-white/15 text-white px-6 py-3.5 rounded-full text-sm font-medium font-body backdrop-blur-md transition-colors flex items-center gap-2 cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 text-white/70" strokeWidth={1.5} />
              <span>How it Works</span>
            </motion.button>
          </motion.div>
        </div>

        {/* ---- RIGHT: Blended Animation Canvas ---- */}
        <div className="relative h-[420px] md:h-[500px] w-full flex items-center justify-center select-none">
          {/* Principle 7: Moving in arcs + Principle 11: Solid drawing in 3D (Floating file card) */}
          <motion.div
            animate={{
              y: [-8, 8, -8],
              x: [-4, 4, -4],
              rotate: [-2.5, 2.5, -2.5],
            }}
            transition={{ repeat: Infinity, duration: 5.5, ease: "easeInOut" }}
            className="absolute top-8 left-4 md:left-12 w-24 h-28 bg-white rounded-xl p-3.5 shadow-[0_20px_50px_rgba(0,0,0,0.8),0_0_0_1px_rgba(255,255,255,0.15)] flex flex-col justify-between z-10 border border-white/20"
          >
            <FileText className="w-5 h-5 text-black/70" strokeWidth={1.5} />
            <div className="space-y-1.5">
              <div className="w-full h-1.5 bg-black/20 rounded-full" />
              <div className="w-4/5 h-1.5 bg-black/15 rounded-full" />
              <div className="w-3/5 h-1.5 bg-black/10 rounded-full" />
            </div>
          </motion.div>

          {/* Dots field - living directly in the hero background */}
          {DOT_COORDS.map((dot, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0 }}
              animate={{ opacity: [0.12, 0.65, 0.12] }}
              transition={{
                delay: dot.delay,
                repeat: Infinity,
                duration: dot.dur,
                ease: "easeInOut",
              }}
              className="absolute w-1.5 h-1.5 bg-white rounded-full pointer-events-none"
              style={{
                left: dot.left,
                top: dot.top,
              }}
            />
          ))}

          {/* Principle 3: Staging the Focus + Principle 10: Exaggerated feedback (The ONE vibrant lime node) */}
          <motion.div
            animate={{
              scale: [1, 1.15, 1],
              boxShadow: [
                "0 0 10px rgba(200,244,50,0.4)",
                "0 0 35px rgba(200,244,50,0.85)",
                "0 0 10px rgba(200,244,50,0.4)",
              ],
            }}
            whileHover={{ scale: 1.25 }}
            whileTap={{ scale: 0.9 }}
            transition={{ repeat: Infinity, duration: 2.2, ease: "easeInOut" }}
            className="absolute top-[48%] left-[58%] w-9 h-9 bg-[#C8F432] rounded-full flex items-center justify-center z-10 cursor-pointer"
          >
            <Sparkles className="w-4 h-4 text-black" strokeWidth={1.8} />
          </motion.div>

          {/* Principle 7: Moving in arcs — Curved connecting SVG lines between file, vectors, and chat */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible">
            <motion.path
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 0.25 }}
              transition={{ duration: 1.6, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
              d="M 120 120 Q 220 180 320 250"
              stroke="white"
              strokeWidth="1"
              strokeDasharray="4 4"
              fill="none"
            />
            <motion.path
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 0.45 }}
              transition={{ duration: 1.6, delay: 0.6, ease: [0.16, 1, 0.3, 1] }}
              d="M 320 250 Q 380 300 420 370"
              stroke="#C8F432"
              strokeWidth="1.2"
              fill="none"
            />
          </svg>

          {/* Principle 5: Follow Through & Overlapping Action (Chat bubble + delayed badge spring) */}
          <motion.div
            initial={{ opacity: 0, y: 24, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ delay: 0.65, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="absolute bottom-6 right-0 md:right-4 bg-white/[0.94] backdrop-blur-xl border border-white/40 rounded-2xl p-4 w-[280px] shadow-[0_25px_60px_rgba(0,0,0,0.7),0_0_0_1px_rgba(255,255,255,0.2)] z-20"
          >
            <div className="flex items-center gap-1.5 mb-2">
              <span className="w-1.5 h-1.5 rounded-full bg-black/30" />
              <span className="w-1.5 h-1.5 rounded-full bg-black/30" />
              <span className="w-1.5 h-1.5 rounded-full bg-black/30" />
              <motion.span
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.9, type: "spring", stiffness: 400, damping: 18 }}
                className="ml-auto text-[9px] font-mono text-black/60 font-semibold bg-black/5 px-2 py-0.5 rounded-full"
              >
                94% match
              </motion.span>
            </div>
            <div className="text-[12px] text-black font-medium leading-snug font-body">
              Based on your file, the answer is on page 3 with verified cosine evidence.
            </div>
            {/* Principle 5: Follow-through settlement */}
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.05, duration: 0.3 }}
              className="mt-3 text-[10px] text-black/60 flex items-center gap-2 font-mono"
            >
              <span className="bg-black text-[#C8F432] px-2 py-0.5 rounded-full font-medium shadow-sm">
                report.pdf
              </span>
              <span>p.3 • citation</span>
            </motion.div>
          </motion.div>
        </div>
      </div>

      {/* Subtle Scroll Down Indicator — Principle 14: Bigger hit area */}
      <div
        className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 hidden md:flex flex-col items-center gap-1 opacity-40 hover:opacity-100 transition-opacity p-2 -m-2 cursor-pointer"
        onClick={scrollToHowItWorks}
      >
        <span className="text-[10px] font-mono text-white tracking-widest uppercase">Scroll</span>
        <ChevronDown className="w-3.5 h-3.5 text-white animate-bounce" strokeWidth={1.5} />
      </div>
    </section>
  );
}
