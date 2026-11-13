"use client";

import { motion } from "framer-motion";

const footerLinks = [
  { label: "GitHub", href: "https://github.com" },
  { label: "Documentation", href: "/docs" },
  { label: "API", href: "/api" },
  { label: "Status", href: "/status" },
];

function GitHubStarButton() {
  return (
    <motion.a
      href="https://github.com"
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-2 border border-white/10 rounded-full px-4 py-2 text-sm text-white/60 hover:text-white hover:border-white/20 transition-colors duration-200 font-body"
      animate={{ scale: [1, 1.05, 1] }}
      transition={{
        duration: 0.6,
        ease: "easeInOut",
        repeat: Infinity,
        repeatDelay: 2.4,
      }}
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 16 16"
        fill="currentColor"
        className="shrink-0"
      >
        <path d="M8 .2a8 8 0 0 0-2.53 15.59c.4.07.55-.17.55-.38l-.01-1.49c-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.42 7.42 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48l-.01 2.2c0 .21.15.46.55.38A8.01 8.01 0 0 0 8 .2Z" />
      </svg>
      Star on GitHub
    </motion.a>
  );
}

export default function Footer() {
  return (
    <footer className="bg-[#080808] border-t border-white/10">
      <div className="max-w-6xl mx-auto px-8 py-12">
        {/* Top row */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
          {/* Left — logo + tagline */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2.5">
              <img src="/locus-icon.svg" className="w-6 h-6" alt="LOCUS" />
              <span className="inline-flex items-baseline leading-none">
                <span
                  style={{ fontFamily: 'var(--font-locus-l, "Niconne", cursive)' }}
                  className="text-[25px] font-normal text-white -translate-y-[1px]"
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
            <span className="text-white/40 text-xs font-mono tracking-wider">
              TRAIN &bull; EMBED &bull; RETRIEVE
            </span>
          </div>

          {/* Center — links */}
          <div className="flex flex-wrap items-center gap-6">
            {footerLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-sm text-white/40 hover:text-white transition-colors duration-200 font-body"
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* Right — star + built for */}
          <div className="flex flex-col items-start md:items-end gap-3">
            <GitHubStarButton />
            <span className="text-xs text-white/30 font-body">
              Built for the exhibition
            </span>
          </div>
        </div>

        {/* Bottom row */}
        <div className="mt-10 pt-6 border-t border-white/5">
          <p className="text-xs text-white/30 font-body text-center font-mono">
            &copy; 2024 LOCUS &bull; Place where knowledge lives &bull; Open source under MIT.
          </p>
        </div>
      </div>
    </footer>
  );
}
