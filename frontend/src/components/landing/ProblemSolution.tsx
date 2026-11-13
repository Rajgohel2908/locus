"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";
import { Layers, Split, ShieldAlert } from "lucide-react";

const cards = [
  {
    icon: Layers,
    title: "Data Scattered Everywhere",
    desc: "Your files, databases, and docs live in silos. Finding answers means searching 5 tools.",
  },
  {
    icon: Split,
    title: "Manual Chunking is Pain",
    desc: "Splitting documents, cleaning data, choosing chunk sizes — it's all trial and error.",
  },
  {
    icon: ShieldAlert,
    title: "RAG Without Citations is Guessing",
    desc: "AI answers without sources aren't trustworthy. You need evidence-gated responses.",
  },
];

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 40 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: i * 0.1,
      duration: 0.5,
      ease: "easeOut",
    },
  }),
};

const iconShake: Variants = {
  hidden: { x: 0 },
  visible: {
    x: [0, -4, 4, -4, 0],
    transition: {
      duration: 0.4,
      ease: "easeOut",
      delay: 0.3,
    },
  },
};

export default function ProblemSolution() {
  const prefersReduced = useReducedMotion();

  return (
    <section className="w-full bg-[#080808] px-6 py-24 md:py-32">
      <div className="mx-auto max-w-5xl">
        {/* Section heading */}
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
                whileHover={{
                  y: -4,
                  borderColor: "rgba(200,244,50,0.3)",
                  transition: { duration: 0.3, ease: "easeOut" },
                }}
                className="group rounded-2xl border border-white/10 bg-white/[0.03] p-8 backdrop-blur"
              >
                {/* Icon with shake */}
                <motion.div
                  variants={iconShake}
                  className="mb-5 inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/[0.06] border border-white/10 text-white/70 group-hover:text-[#C8F432] group-hover:border-[#C8F432]/30 transition-colors"
                >
                  <Icon className="w-5 h-5" strokeWidth={1.5} />
                </motion.div>

                {/* Title */}
                <h3 className="font-heading mb-3 text-lg font-semibold text-white">
                  {card.title}
                </h3>

                {/* Description */}
                <p className="font-body text-sm leading-relaxed text-white/50">
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
