"use client";

import { motion } from "framer-motion";

const techs = [
  "PostgreSQL",
  "MongoDB",
  "PDF",
  "CSV",
  "Qdrant",
  "OpenAI",
  "LangChain",
  "DOCX",
];

export default function SocialProof() {
  return (
    <>
      <style>{`
        @keyframes marquee-scroll {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
      `}</style>

      <section className="relative w-full bg-[#080808] border-y border-white/5 py-6 overflow-hidden">
        {/* Gradient fade masks on edges */}
        <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-24 bg-gradient-to-r from-[#080808] to-transparent" />
        <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-24 bg-gradient-to-l from-[#080808] to-transparent" />

        {/* Marquee track */}
        <div
          className="flex w-max gap-5"
          style={{
            animation: "marquee-scroll 30s linear infinite",
          }}
        >
          {/* Two identical sets for seamless loop */}
          {[0, 1].map((set) => (
            <div key={set} className="flex shrink-0 gap-5">
              {techs.map((tech) => (
                <motion.span
                  key={`${set}-${tech}`}
                  whileHover={{ scale: 1.1 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                  className="inline-flex cursor-default select-none items-center rounded-xl border border-white/10 bg-white/[0.05] px-5 py-3 font-mono text-sm text-white/70 whitespace-nowrap"
                >
                  {tech}
                </motion.span>
              ))}
            </div>
          ))}
        </div>
      </section>

      {/* Slower speed on mobile via media query override */}
      <style>{`
        @media (max-width: 767px) {
          .flex.w-max {
            animation-duration: 45s !important;
          }
        }
      `}</style>
    </>
  );
}
