"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const tabs = [
  {
    id: "student",
    label: "Student",
    title: "Study Smarter",
    desc: "Upload your textbooks and notes. Ask questions, get cited answers from your own materials. Perfect for exam prep.",
    features: ["PDF & DOCX support", "Citation tracking", "Fast retrieval"],
    pattern: "student",
  },
  {
    id: "researcher",
    label: "Researcher",
    title: "Literature Review",
    desc: "Feed in papers, patents, datasets. Cross-reference findings across 100+ documents in seconds.",
    features: ["Multi-document RAG", "Similarity search", "Export citations"],
    pattern: "researcher",
  },
  {
    id: "support",
    label: "Support Bot",
    title: "Instant Support",
    desc: "Connect your docs and FAQ database. Deploy a chat widget that answers customer questions with sources.",
    features: ["API & Widget", "Custom branding", "Analytics dashboard"],
    pattern: "support",
  },
] as const;

function PatternVisual({ pattern }: { pattern: string }) {
  if (pattern === "student") {
    // Scattered dots in a grid-like study pattern
    return (
      <svg
        viewBox="0 0 200 200"
        className="w-full h-full"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {Array.from({ length: 6 }).map((_, row) =>
          Array.from({ length: 6 }).map((_, col) => {
            const x = 20 + col * 32;
            const y = 20 + row * 32;
            const opacity = ((row + col) % 3 === 0) ? 0.6 : 0.2;
            const r = ((row * col) % 3 === 0) ? 4 : 2.5;
            return (
              <circle
                key={`${row}-${col}`}
                cx={x}
                cy={y}
                r={r}
                fill="#C8F432"
                opacity={opacity}
              />
            );
          })
        )}
        {/* Connecting lines for some dots */}
        <line x1="20" y1="20" x2="84" y2="20" stroke="#C8F432" strokeOpacity="0.15" strokeWidth="1" />
        <line x1="20" y1="20" x2="20" y2="84" stroke="#C8F432" strokeOpacity="0.15" strokeWidth="1" />
        <line x1="84" y1="84" x2="148" y2="84" stroke="#C8F432" strokeOpacity="0.15" strokeWidth="1" />
        <line x1="84" y1="84" x2="84" y2="148" stroke="#C8F432" strokeOpacity="0.15" strokeWidth="1" />
        <line x1="148" y1="148" x2="148" y2="180" stroke="#C8F432" strokeOpacity="0.15" strokeWidth="1" />
      </svg>
    );
  }

  if (pattern === "researcher") {
    // Network/constellation pattern
    const nodes = [
      { x: 100, y: 30 },
      { x: 40, y: 70 },
      { x: 160, y: 60 },
      { x: 70, y: 130 },
      { x: 140, y: 120 },
      { x: 100, y: 170 },
      { x: 30, y: 160 },
      { x: 170, y: 160 },
    ];
    const edges = [
      [0, 1], [0, 2], [1, 3], [2, 4], [3, 5], [4, 5],
      [3, 6], [4, 7], [1, 4], [0, 4],
    ];
    return (
      <svg
        viewBox="0 0 200 200"
        className="w-full h-full"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {edges.map(([a, b], i) => (
          <line
            key={`e-${i}`}
            x1={nodes[a].x}
            y1={nodes[a].y}
            x2={nodes[b].x}
            y2={nodes[b].y}
            stroke="#C8F432"
            strokeOpacity="0.2"
            strokeWidth="1"
          />
        ))}
        {nodes.map((n, i) => (
          <circle
            key={`n-${i}`}
            cx={n.x}
            cy={n.y}
            r={i % 3 === 0 ? 5 : 3}
            fill="#C8F432"
            opacity={i % 2 === 0 ? 0.7 : 0.35}
          />
        ))}
      </svg>
    );
  }

  // Support bot — chat bubble / wave pattern
  return (
    <svg
      viewBox="0 0 200 200"
      className="w-full h-full"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Horizontal wave lines */}
      {[50, 90, 130, 170].map((y, i) => (
        <path
          key={`w-${i}`}
          d={`M 10 ${y} Q 55 ${y - 12 + i * 3} 100 ${y} T 190 ${y}`}
          stroke="#C8F432"
          strokeOpacity={0.12 + i * 0.06}
          strokeWidth="1.5"
          fill="none"
        />
      ))}
      {/* Chat bubble shapes */}
      <rect x="30" y="30" width="60" height="28" rx="8" fill="#C8F432" opacity="0.15" />
      <rect x="110" y="70" width="70" height="28" rx="8" fill="#C8F432" opacity="0.1" />
      <rect x="40" y="120" width="50" height="28" rx="8" fill="#C8F432" opacity="0.2" />
      {/* Small dots inside bubbles */}
      <circle cx="45" cy="44" r="2" fill="#C8F432" opacity="0.5" />
      <circle cx="55" cy="44" r="2" fill="#C8F432" opacity="0.5" />
      <circle cx="65" cy="44" r="2" fill="#C8F432" opacity="0.5" />
    </svg>
  );
}

const contentVariants = {
  enter: { opacity: 0, y: 16 },
  center: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -12 },
};

export default function UseCases() {
  const [active, setActive] = useState(0);
  const tab = tabs[active];

  return (
    <section id="use-cases" className="relative bg-[#080808] py-20 overflow-hidden">
      {/* Noise grain overlay */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 z-0"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E")`,
          backgroundRepeat: "repeat",
          backgroundSize: "128px 128px",
        }}
      />

      <div className="relative z-10 mx-auto max-w-5xl px-6">
        {/* Section header */}
        <motion.div
          className="text-center mb-12"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          <h2 className="font-heading text-3xl md:text-4xl font-semibold text-[#F5F5F0]">
            One engine, many uses
          </h2>
          <p className="mt-3 text-white/50 font-body max-w-lg mx-auto text-sm md:text-base">
            LOCUS adapts to your workflow &mdash; whether you&apos;re studying, researching, or building products.
          </p>
        </motion.div>

        {/* Tab bar */}
        <motion.div
          className="flex justify-center mb-10"
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease: "easeOut", delay: 0.1 }}
        >
          <div className="inline-flex bg-white/[0.05] rounded-full p-1 gap-1">
            {tabs.map((t, i) => (
              <button
                key={t.id}
                onClick={() => setActive(i)}
                className={`
                  relative rounded-full px-5 py-2 text-sm font-body font-medium transition-colors duration-300
                  ${active === i
                    ? "bg-white text-black"
                    : "text-white/60 hover:text-white/80"
                  }
                `}
              >
                {t.label}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Tab content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={tab.id}
            variants={contentVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="grid md:grid-cols-2 gap-8 items-center"
          >
            {/* Text side */}
            <div className="order-2 md:order-1">
              <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-8">
                <h3 className="font-heading text-2xl font-semibold text-[#F5F5F0] mb-3">
                  {tab.title}
                </h3>
                <p className="font-body text-white/50 text-sm leading-relaxed mb-6">
                  {tab.desc}
                </p>
                <ul className="space-y-3">
                  {tab.features.map((f) => (
                    <li
                      key={f}
                      className="flex items-center gap-3 text-sm font-body text-white/70"
                    >
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#C8F432]/10">
                        <svg
                          width="10"
                          height="10"
                          viewBox="0 0 10 10"
                          fill="none"
                          className="text-[#C8F432]"
                        >
                          <path
                            d="M2 5.5L4 7.5L8 3"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </span>
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Visual side */}
            <div className="order-1 md:order-2 flex items-center justify-center">
              <div className="w-full max-w-[280px] aspect-square rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 flex items-center justify-center">
                <PatternVisual pattern={tab.pattern} />
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}
