"use client";

import { motion } from "framer-motion";
import { Star } from "lucide-react";

const footerLinks = [
  { label: "Documentation", href: "#features" },
  { label: "Vector Studio", href: "/playground" },
  { label: "Architecture", href: "#how-it-works" },
  { label: "Open Source", href: "#open-source" },
];

function GitHubStarButton() {
  return (
    <motion.a
      href="https://github.com/Rajgohel2908/locus"
      target="_blank"
      rel="noopener noreferrer"
      whileHover={{ scale: 1.04 }}
      whileTap={{ scaleX: 1.05, scaleY: 0.92 }} // Principle 1: Squash & Stretch
      transition={{ type: "spring", stiffness: 400, damping: 20 }}
      className="relative inline-flex items-center gap-2 border border-white/10 hover:border-[#C8F432]/50 bg-white/[0.04] hover:bg-white/[0.08] rounded-full px-5 py-2.5 text-xs text-white/70 hover:text-white transition-colors duration-200 font-mono shadow-md before:absolute before:-inset-1 before:content-['']"
    >
      <Star className="w-3.5 h-3.5 text-[#C8F432] fill-[#C8F432]" />
      <span>Star LOCUS on GitHub</span>
    </motion.a>
  );
}

export default function Footer() {
  return (
    <footer className="bg-[#080808] border-t border-white/10 relative overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-gradient-to-r before:from-transparent before:via-[#C8F432]/30 before:to-transparent">
      <div className="max-w-6xl mx-auto px-6 sm:px-8 py-14">
        {/* Top row */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
          {/* Left — logo + tagline */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2.5">
              <img src="/locus-icon.svg" className="w-6 h-6" alt="LOCUS" />
              <span className="inline-flex items-baseline leading-none">
                <span
                  style={{ fontFamily: 'var(--font-locus-l, "Niconne", cursive)' }}
                  className="text-[26px] font-normal text-white -translate-y-[1px]"
                >
                  L
                </span>
                <span
                  style={{
                    fontFamily: 'var(--font-locus-sans, "Satoshi", sans-serif)',
                    fontWeight: 300,
                    letterSpacing: "0.22em",
                  }}
                  className="text-[15px] ml-[2.5px] uppercase text-white/95 font-light"
                >
                  OCUS
                </span>
              </span>
            </div>
            <span className="text-white/40 text-[11px] font-mono tracking-widest">
              TRAIN &bull; EMBED &bull; RETRIEVE
            </span>
          </div>

          {/* Center — links with Principle 14: Bigger Hit Areas */}
          <div className="flex flex-wrap items-center gap-7">
            {footerLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="relative text-xs font-mono text-white/50 hover:text-[#C8F432] transition-colors duration-150 py-1 before:absolute before:-inset-2 before:content-['']"
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* Right — star + built info */}
          <div className="flex flex-col items-start md:items-end gap-2.5">
            <GitHubStarButton />
            <span className="text-[11px] text-white/30 font-mono">
              Designed for verifiable knowledge retrieval
            </span>
          </div>
        </div>

        {/* Bottom row */}
        <div className="mt-12 pt-6 border-t border-white/5 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-[11px] text-white/30 font-mono text-center sm:text-left">
            &copy; 2024 LOCUS &bull; Place where knowledge lives &bull; Open source under MIT.
          </p>
          <div className="flex items-center gap-2 text-[11px] font-mono text-white/40">
            <span className="w-1.5 h-1.5 rounded-full bg-[#C8F432] animate-pulse" />
            <span>PostgreSQL pgvector • Gemini • FastAPI</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
