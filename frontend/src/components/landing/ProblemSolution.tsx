"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";
import { Layers, Split, ShieldAlert } from "lucide-react";

// Principle 16: Miller's Law (Chunking into 3 clear cards)
const cards = [
  {
    icon: Layers,
    title: "Data Scattered Everywhere",
    desc: "Your files, databases, and docs live in silos. Finding answers means searching across 5 disconnected tools.",
  },
  {
    icon: Split,
    title: "Manual Chunking is Pain",
    desc: "Splitting documents, cleaning noise, choosing token sizes — trial and error ruins retrieval accuracy.",
  },
  {
    icon: ShieldAlert,
    title: "RAG Without Citations is Guessing",
    desc: "AI answers without verified source citations aren't trustworthy. You need mathematical evidence gates.",
  },
];

// Principle 6: Slow In & Slow Out
const cardVariants: Variants = {
  hidden: { opacity: 0, y: 35 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: i * 0.12,
      duration: 0.5,
      ease: [0.16, 1, 0.3, 1],
    },
  }),
};

export default function ProblemSolution() {
  const prefersReduced = useReducedMotion();

  return (
    <section className="w-full bg-[#080808] px-6 py-24 md:py-32">
      <div className="mx-auto max-w-5xl">
        {/* Section heading with Principle 3: Staging Focus */}
        <div className="mb-16 flex items-center justify-center gap-3">
          <span className="inline-block h-2 w-2 rounded-full bg-[#C8F432] shadow-[0_0_8px_#C8F432]" />
          <h2 className="font-heading text-2xl font-bold text-white tracking-tight">
            The Problem
          </h2>
        </div>

        {/* Cards grid */}
        <div className="grid gap-6 md:grid-cols-3">
          {cards.map((card, i) => {
            const Icon = card.icon;
            return (
              <motion.div
                key={card.title}
                custom={i}
                initial={prefersReduced ? "visible" : "hidden"}
                whileInView="visible"
                viewport={{ once: true, margin: "-60px" }}
                variants={cardVariants}
                /* Principle 1: Squash & Stretch + Principle 2: Anticipation on hover */
                whileHover={{
                  y: -6,
                  borderColor: "rgba(200, 244, 50, 0.4)",
                  boxShadow: "0 20px 40px -15px rgba(0,0,0,0.8), 0 0 25px rgba(200,244,50,0.12)",
                  transition: { duration: 0.2, ease: [0.16, 1, 0.3, 1] },
                }}
                whileTap={{ scale: 0.98 }}
                className="group relative rounded-2xl border border-white/10 bg-white/[0.025] p-8 backdrop-blur-md transition-colors cursor-default overflow-hidden"
              >
                {/* Top edge sheen */}
                <div className="absolute inset-x-6 top-0 h-[1px] bg-gradient-to-r from-transparent via-white/15 to-transparent group-hover:via-[#C8F432]/40 transition-colors" />

                {/* Icon with Principle 8: Secondary Action flourish */}
                <motion.div
                  whileHover={{ rotate: [-2, 4, 0] }}
                  transition={{ duration: 0.3 }}
                  className="mb-5 inline-flex items-center justify-center w-11 h-11 rounded-xl bg-white/[0.05] border border-white/10 text-white/70 group-hover:text-[#C8F432] group-hover:border-[#C8F432]/40 group-hover:bg-[#C8F432]/10 transition-colors"
                >
                  <Icon className="w-5 h-5" strokeWidth={1.5} />
                </motion.div>

                {/* Title */}
                <h3 className="font-heading mb-3 text-lg font-semibold text-white">
                  {card.title}
                </h3>

                {/* Description */}
                <p className="font-body text-sm leading-relaxed text-white/55">
                  {card.desc}
                </p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
