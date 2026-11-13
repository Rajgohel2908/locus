"use client";

import { useEffect, useState, useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Star, GitFork, Users, ExternalLink, Code2, ShieldCheck, Heart } from "lucide-react";

const CONTRIBUTORS = [
  {
    name: "Alex Rivera",
    role: "Vector Pipeline Lead",
    avatar: "AR",
    contributions: "Chunking algorithms & Qdrant engine",
    github: "https://github.com",
  },
  {
    name: "Devon Chen",
    role: "Evaluation & Benchmarks",
    avatar: "DC",
    contributions: "RAG triad metrics & Doctor audit",
    github: "https://github.com",
  },
  {
    name: "Siddharth Rao",
    role: "Core Retrieval Architect",
    avatar: "SR",
    contributions: "Hybrid sparse-dense retrieval",
    github: "https://github.com",
  },
  {
    name: "Elena Rostova",
    role: "Interactive Visuals & UX",
    avatar: "ER",
    contributions: "Vector space canvas & animations",
    github: "https://github.com",
  },
];

export default function TeamOpenSource() {
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { once: true, margin: "-80px" });
  const [stars, setStars] = useState(0);

  // Ticking Star Counter Animation
  useEffect(() => {
    if (!isInView) return;

    const targetStars = 1482;
    const duration = 1200; // ms
    const stepTime = 20; // ms
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

  return (
    <section
      id="open-source"
      ref={containerRef}
      className="py-24 bg-[#080808] border-t border-white/5 relative"
    >
      <div className="max-w-5xl mx-auto px-6">
        {/* Header with Star count */}
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
            className="mt-3 text-white/50 text-sm md:text-base font-body"
          >
            Transparent vector indexing with no vendor lock-in. Fork, audit, or deploy on your own
            infrastructure.
          </motion.p>

          {/* GitHub Star Button with 3s Pulse Animation */}
          <div className="mt-8 flex items-center justify-center gap-4">
            <motion.a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="relative inline-flex items-center gap-3 bg-white/[0.06] hover:bg-white/[0.1] border border-white/15 hover:border-[#C8F432]/40 rounded-full px-5 py-2.5 text-sm font-mono text-white transition-all shadow-lg group"
              animate={{
                scale: [1, 1.04, 1],
                borderColor: [
                  "rgba(255, 255, 255, 0.15)",
                  "rgba(200, 244, 50, 0.5)",
                  "rgba(255, 255, 255, 0.15)",
                ],
              }}
              transition={{
                repeat: Infinity,
                duration: 3,
                ease: "easeInOut",
              }}
            >
              <Star className="w-4 h-4 text-[#C8F432] fill-[#C8F432]" />
              <span>Star on GitHub</span>
              <span className="h-4 w-[1px] bg-white/20" />
              <span className="text-[#C8F432] font-semibold">
                {stars.toLocaleString()}
              </span>
            </motion.a>

            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-xs font-mono text-white/50 hover:text-white transition px-4 py-2.5 rounded-full border border-white/5 hover:border-white/20"
            >
              <GitFork className="w-3.5 h-3.5" />
              <span>248 forks</span>
            </a>
          </div>
        </div>

        {/* Contributor Cards with Lift on Hover */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          {CONTRIBUTORS.map((member, index) => (
            <motion.div
              key={member.name}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1, duration: 0.5, ease: "easeOut" }}
              whileHover={{
                y: -6,
                boxShadow: "0 12px 30px -10px rgba(200, 244, 50, 0.15)",
                borderColor: "rgba(200, 244, 50, 0.3)",
              }}
              className="bg-white/[0.03] backdrop-blur-sm border border-white/10 rounded-2xl p-5 flex flex-col justify-between transition-colors duration-200"
            >
              <div>
                {/* Avatar Initial Circle */}
                <div className="w-11 h-11 rounded-xl bg-white/[0.06] border border-white/10 flex items-center justify-center font-mono font-bold text-sm text-[#C8F432] mb-3">
                  {member.avatar}
                </div>
                <div className="text-white font-medium text-sm font-heading">
                  {member.name}
                </div>
                <div className="text-[#C8F432] text-xs font-mono mt-0.5">
                  {member.role}
                </div>
                <p className="text-white/40 text-xs mt-2 font-body leading-relaxed">
                  {member.contributions}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-[11px] text-white/40 font-mono">
                <span>Core Contributor</span>
                <ExternalLink className="w-3 h-3 text-white/30" />
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

