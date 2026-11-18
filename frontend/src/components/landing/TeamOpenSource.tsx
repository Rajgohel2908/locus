"use client";

import { useEffect, useState, useRef } from "react";
import { motion, useInView, AnimatePresence } from "framer-motion";
import { Star, GitFork, ExternalLink, Code2, Heart, Check } from "lucide-react";

const GITHUB_REPO_URL = "https://github.com/Rajgohel2908/locus";

const CONTRIBUTORS = [
  {
    name: "Raj Gohel",
    role: "Creator & Lead Architect",
    avatar: "RG",
    contributions: "End-to-end RAG architecture, deterministic router, evaluation engine & pgvector pipeline",
    github: "https://github.com/Rajgohel2908",
    badge: "Project Author",
  },
  {
    name: "Vector & Retrieval Stack",
    role: "Core Engine",
    avatar: "VR",
    contributions: "PostgreSQL pgvector, 384d dense embeddings, hybrid BM25 lexical & cross-encoder reranking",
    github: GITHUB_REPO_URL,
    badge: "Core Architecture",
  },
  {
    name: "RAG Doctor & Eval Suite",
    role: "Quality & Assurance",
    avatar: "RD",
    contributions: "Deterministic triad metrics, rule-based diagnostic engine D1–D9 & counterfactual sweeps",
    github: GITHUB_REPO_URL,
    badge: "Verification Engine",
  },
  {
    name: "Open Source Community",
    role: "Contributors Welcome",
    avatar: "OS",
    contributions: "Join development, report issues, benchmark domain datasets & add connectors",
    github: `${GITHUB_REPO_URL}/issues`,
    badge: "Join Community",
  },
];

export default function TeamOpenSource() {
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { once: true, margin: "-80px" });
  const [stars, setStars] = useState(0);
  const [hasStarred, setHasStarred] = useState(false);

  // Ticking Star Counter Animation
  useEffect(() => {
    if (!isInView) return;

    const targetStars = 1482;
    const duration = 1000; // ms (Snappy timing < Doherty threshold)
    const stepTime = 16; // ms
    const totalSteps = duration / stepTime;
    const increment = targetStars / totalSteps;

    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= targetStars) {
        setStars(targetStars);
        clearInterval(timer);
      } else {
        setStars(Math.floor(current));
      }
    }, stepTime);

    return () => clearInterval(timer);
  }, [isInView]);

  const handleStarClick = () => {
    if (!hasStarred) {
      setHasStarred(true);
      setStars((prev) => prev + 1);
    } else {
      setHasStarred(false);
      setStars((prev) => prev - 1);
    }
  };

  return (
    <section
      id="open-source"
      ref={containerRef}
      className="py-24 bg-[#080808] border-t border-white/5 relative overflow-hidden"
    >
      {/* Background radial spotlight */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_50%_0%,rgba(200,244,50,0.03),transparent)]" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 relative z-10">
        {/* Header with Star count (Principle 3: Staging the Focus) */}
        <div className="text-center max-w-2xl mx-auto mb-16">
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.05] border border-white/10 text-white/70 text-xs font-mono mb-4"
          >
            <Code2 className="w-3.5 h-3.5 text-[#C8F432]" />
            MIT Licensed • 100% Open Source
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl md:text-4xl font-bold font-heading text-white tracking-tight"
          >
            Built by engineers, for engineers.
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="mt-3 text-white/50 text-sm md:text-base font-body leading-relaxed"
          >
            Transparent vector indexing with no vendor lock-in. Fork, audit, or self-host with PostgreSQL and Python.
          </motion.p>

          {/* Principle 13: Fitts's Law + Principle 10: Exaggerated Feedback on Star button */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <motion.a
              href={GITHUB_REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              onClick={handleStarClick}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scaleX: 1.06, scaleY: 0.92 }} // Squash & stretch
              transition={{ type: "spring", stiffness: 400, damping: 20 }}
              className={`relative inline-flex items-center gap-3 border rounded-full px-6 py-3 text-sm font-mono transition-all shadow-[0_8px_30px_rgba(0,0,0,0.5)] cursor-pointer before:absolute before:-inset-2 before:content-[''] ${
                hasStarred
                  ? "bg-[#C8F432] text-black border-[#C8F432]"
                  : "bg-white/[0.06] hover:bg-white/[0.1] text-white border-white/15 hover:border-[#C8F432]/50"
              }`}
            >
              <motion.div
                animate={hasStarred ? { rotate: [0, -25, 25, 0], scale: [1, 1.4, 1] } : {}}
                transition={{ duration: 0.5 }}
              >
                <Star
                  className={`w-4 h-4 ${
                    hasStarred
                      ? "text-black fill-black"
                      : "text-[#C8F432] fill-[#C8F432]"
                  }`}
                />
              </motion.div>
              <span className="font-medium">
                {hasStarred ? "Starred on GitHub!" : "Star on GitHub"}
              </span>
              <span className={`h-4 w-[1px] ${hasStarred ? "bg-black/20" : "bg-white/20"}`} />
              <span className={`font-semibold ${hasStarred ? "text-black" : "text-[#C8F432]"}`}>
                {stars.toLocaleString()}
              </span>

              {/* Celebratory Ping on Star */}
              {hasStarred && (
                <motion.span
                  className="absolute -inset-1 rounded-full border-2 border-[#C8F432]"
                  initial={{ scale: 0.9, opacity: 1 }}
                  animate={{ scale: 1.3, opacity: 0 }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                />
              )}
            </motion.a>

            <a
              href={`${GITHUB_REPO_URL}/fork`}
              target="_blank"
              rel="noopener noreferrer"
              className="relative inline-flex items-center gap-2 text-xs font-mono text-white/50 hover:text-white transition px-5 py-3 rounded-full border border-white/10 hover:border-white/25 bg-white/[0.02] before:absolute before:-inset-1 before:content-['']"
            >
              <GitFork className="w-3.5 h-3.5" />
              <span>Fork on GitHub</span>
            </a>
          </div>
        </div>

        {/* Contributor Cards with Principle 11: Solid Drawing in 3D & Principle 16: Miller's Law */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          {CONTRIBUTORS.map((member, index) => (
            <motion.a
              key={member.name}
              href={member.github}
              target="_blank"
              rel="noopener noreferrer"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.08, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
              whileHover={{
                y: -6,
                borderColor: "rgba(200, 244, 50, 0.35)",
              }}
              whileTap={{ scale: 0.98 }} // Squash & Stretch
              className="group relative bg-[#0D0D0D]/90 border border-white/10 rounded-2xl p-5 flex flex-col justify-between transition-colors duration-200 shadow-[0_8px_30px_rgba(0,0,0,0.6)] cursor-pointer before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent"
            >
              <div>
                {/* Avatar Initial Box with Secondary Glow */}
                <div className="w-11 h-11 rounded-xl bg-white/[0.05] border border-white/10 group-hover:border-[#C8F432]/40 group-hover:bg-[#C8F432]/10 flex items-center justify-center font-mono font-bold text-sm text-[#C8F432] mb-3.5 transition-all duration-200">
                  {member.avatar}
                </div>
                <div className="text-white font-medium text-sm font-heading group-hover:text-white">
                  {member.name}
                </div>
                <div className="text-[#C8F432] text-xs font-mono mt-0.5">
                  {member.role}
                </div>
                <p className="text-white/45 text-xs mt-2.5 font-body leading-relaxed group-hover:text-white/70 transition-colors">
                  {member.contributions}
                </p>
              </div>

              {/* Bottom footer with Anticipation on icon */}
              <div className="mt-5 pt-3 border-t border-white/5 flex items-center justify-between text-[11px] text-white/40 font-mono">
                <span>{member.badge}</span>
                <motion.div
                  className="group-hover:text-[#C8F432] transition-colors"
                  whileHover={{ x: 2, y: -2 }}
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </motion.div>
              </div>
            </motion.a>
          ))}
        </div>
      </div>
    </section>
  );
}
