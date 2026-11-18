"use client";

import { useState } from "react";
import { motion } from "framer-motion";

interface TechIcon {
  name: string;
  category: string;
  icon: () => JSX.Element;
}

const TECH_ECOSYSTEM: TechIcon[] = [
  {
    name: "Google Gemini",
    category: "Primary Reasoning LLM",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 md:w-7 md:h-7">
        <path d="M11.04 19.32Q12 21.51 12 24q0-2.49.93-4.68.96-2.19 2.58-3.81t3.81-2.55Q21.51 12 24 12q-2.49 0-4.68-.93a12.3 12.3 0 0 1-3.81-2.58 12.3 12.3 0 0 1-2.58-3.81Q12 2.49 12 0q0 2.49-.96 4.68-.93 2.19-2.55 3.81a12.3 12.3 0 0 1-3.81 2.58Q2.49 12 0 12q2.49 0 4.68.96 2.19.93 3.81 2.58t3.57 3.78Z" />
      </svg>
    ),
  },
  {
    name: "PostgreSQL",
    category: "pgvector Vector DB",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 md:w-7 md:h-7">
        <path d="M23.5594 14.7228a.5269.5269 0 0 0-.0563-.1191c-.139-.2632-.4768-.3418-1.0074-.2321-1.6533.3411-2.2935.1312-2.5256-.0191 1.342-2.0482 2.445-4.522 3.0411-6.8297.2714-1.0507.7982-3.5237.1222-4.7316a1.5641 1.5641 0 0 0-.1509-.235C21.6931.9086 19.8007.0248 17.5099.0005c-1.4947-.0158-2.7705.3461-3.1161.4794a9.449 9.449 0 0 0-.5159-.0816 8.044 8.044 0 0 0-1.3114-.1278c-1.1822-.0184-2.2038.2642-3.0498.8406-.8573-.3211-4.7888-1.645-7.2219.0788C.9359 2.1526.3086 3.8733.4302 6.3043c.0409.818.5069 3.334 1.2423 5.7436.4598 1.5065.9387 2.7019 1.4334 3.582.553.9942 1.1259 1.5933 1.7143 1.7895.4474.1491 1.1327.1441 1.8581-.7279.8012-.9635 1.5903-1.8258 1.9446-2.2069.4351.2355.9064.3625 1.39.3772a.0569.0569 0 0 0 .0004.0041 11.0312 11.0312 0 0 0-.2472.3054c-.3389.4302-.4094.5197-1.5002.7443-.3102.064-1.1344.2339-1.1464.8115-.0025.1224.0329.2309.0919.3268.2269.4231.9216.6097 1.015.6331 1.3345.3335 2.5044.092 3.3714-.6787-.017 2.231.0775 4.4174.3454 5.0874.2212.5529.7618 1.9045 2.4692 1.9043.2505 0 .5263-.0291.8296-.0941 1.7819-.3821 2.5557-1.1696 2.855-2.9059.1503-.8707.4016-2.8753.5388-4.1012.0169-.0703.0357-.1207.057-.1362.0007-.0005.0697-.0471.4272.0307a.3673.3673 0 0 0 .0443.0068l.2539.0223.0149.001c.8468.0384 1.9114-.1426 2.5312-.4308.6438-.2988 1.8057-1.0323 1.5951-1.6698z" />
      </svg>
    ),
  },
  {
    name: "Hugging Face",
    category: "Sentence-Transformers & Reranking",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 md:w-7 md:h-7">
        <path d="M12.025 1.13c-5.77 0-10.449 4.647-10.449 10.378 0 1.112.178 2.181.503 3.185.064-.222.203-.444.416-.577a.96.96 0 0 1 .524-.15c.293 0 .584.124.84.284.278.173.48.408.71.694.226.282.458.611.684.951v-.014c.017-.324.106-.622.264-.874s.403-.487.762-.543c.3-.047.596.06.787.203s.31.313.4.467c.189.34.341.705.452 1.09.434 1.514 1.83 2.616 3.486 2.616 1.656 0 3.053-1.102 3.486-2.616.111-.385.263-.75.452-1.09.09-.154.21-.324.4-.467s.487-.25.787-.203c.359.056.604.291.762.543s.247.55.264.874v.014c.226-.34.458-.669.684-.951.23-.286.432-.521.71-.694.256-.16.547-.284.84-.284s.379.057.524.15c.213.133.352.355.416.577.325-1.004.503-2.073.503-3.185 0-5.731-4.679-10.378-10.449-10.378zm-3.882 6.08a1.69 1.69 0 0 1 1.691 1.691 1.69 1.69 0 0 1-1.69 1.691 1.69 1.69 0 0 1-1.691-1.69 1.69 1.69 0 0 1 1.69-1.692zm7.754 0a1.69 1.69 0 0 1 1.691 1.691 1.69 1.69 0 0 1-1.69 1.691 1.69 1.69 0 0 1-1.691-1.69 1.69 1.69 0 0 1 1.69-1.692zM7.5 15v1.5h1.5v6H4.5V24h15v-1.5H15v-6h1.5V15Zm3 1.5h3v6h-3z" />
      </svg>
    ),
  },
  {
    name: "LangChain",
    category: "AST & Recursive Chunking",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 md:w-7 md:h-7">
        <path d="M13.796 0a6.93 6.93 0 0 0-4.91 2.019L5.451 5.455l3.273 3.27 3.432-3.432a2.284 2.284 0 0 1 3.277 0 2.28 2.28 0 0 1 0 3.275L12 12.001l3.273 3.273 3.433-3.435c2.692-2.692 2.692-7.127 0-9.82A6.92 6.92 0 0 0 13.796 0m-5.07 8.728-3.433 3.434c-2.692 2.693-2.692 7.126 0 9.819A6.92 6.92 0 0 0 10.203 24a6.93 6.93 0 0 0 4.911-2.019l3.433-3.434-3.273-3.27-3.433 3.432a2.284 2.284 0 0 1-3.277 0 2.28 2.28 0 0 1 0-3.275L12 11.999l-3.273-3.272-3.433 3.435c-2.692 2.692-2.692 7.127 0 9.82A6.92 6.92 0 0 0 13.796 24Z" />
      </svg>
    ),
  },
  {
    name: "FastAPI",
    category: "Async API Engine",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 md:w-7 md:h-7">
        <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm-.92 18.75l1.67-6.25H9.5l3.42-7.25h1.58l-1.67 6.25h3.25l-3.42 7.25h-1.58z" />
      </svg>
    ),
  },
  {
    name: "Python",
    category: "Core Computing Runtime",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 md:w-7 md:h-7">
        <path d="M11.914 0C5.82 0 6.2 2.656 6.2 2.656l.007 2.752h5.814v.826H3.89S0 5.77 0 11.895c0 6.126 3.4 5.92 3.4 5.92h2.029v-2.856s-.11-3.4 3.344-3.4h5.758s3.235.053 3.235-3.13V3.13S18.33 0 11.914 0zm-3.14 1.836a1.01 1.01 0 1 1 0 2.02 1.01 1.01 0 0 1 0-2.02zm3.312 22.164c6.094 0 5.714-2.656 5.714-2.656l-.007-2.752h-5.814v-.826h8.131s3.89.464 3.89-5.661c0-6.126-3.4-5.92-3.4-5.92h-2.029v2.856s.11 3.4-3.344 3.4H9.619s-3.235-.053-3.235 3.13v5.305s-.564 3.124 5.85 3.124zm3.14-1.836a1.01 1.01 0 1 1 0-2.02 1.01 1.01 0 0 1 0 2.02z" />
      </svg>
    ),
  },
  {
    name: "Next.js",
    category: "React App Framework",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 md:w-7 md:h-7">
        <path d="M18.665 21.978C16.758 23.255 14.465 24 12 24 5.377 24 0 18.623 0 12S5.377 0 12 0s12 5.377 12 12c0 3.583-1.574 6.801-4.067 9.001L9.219 7.2H7.2v9.596h1.615V9.251l9.85 12.727Zm-3.332-8.533 1.6 2.061V7.2h-1.6v6.245Z" />
      </svg>
    ),
  },
  {
    name: "Pandas",
    category: "Tabular Profiler & Doctor",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 md:w-7 md:h-7">
        <path d="M4 3h3.5v18H4zm6.25 0h3.5v7h-3.5zm0 9h3.5v9h-3.5zm6.25-9H20v18h-3.5z" />
      </svg>
    ),
  },
  {
    name: "OpenAI / ChatGPT",
    category: "LLM Connector",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 md:w-7 md:h-7">
        <path d="M22.282 9.821a6 6 0 0 0-.516-4.91a6.05 6.05 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a6 6 0 0 0-3.998 2.9a6.05 6.05 0 0 0 .743 7.097a5.98 5.98 0 0 0 .51 4.911a6.05 6.05 0 0 0 6.515 2.9A6 6 0 0 0 13.26 24a6.06 6.06 0 0 0 5.772-4.206a6 6 0 0 0 3.997-2.9a6.06 6.06 0 0 0-.747-7.073M13.26 22.43a4.48 4.48 0 0 1-2.876-1.04l.141-.081l4.779-2.758a.8.8 0 0 0 .392-.681v-6.737l2.02 1.168a.07.07 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494M3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085l4.783 2.759a.77.77 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646M2.34 7.896a4.5 4.5 0 0 1 2.366-1.973V11.6a.77.77 0 0 0 .388.677l5.815 3.354l-2.02 1.168a.08.08 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.08.08 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667m2.01-3.023l-.141-.085l-4.774-2.782a.78.78 0 0 0-.785 0L9.409 9.23V6.897a.07.07 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.8.8 0 0 0-.393.681zm1.097-2.365l2.602-1.5l2.607 1.5v2.999l-2.597 1.5l-2.607-1.5Z" />
      </svg>
    ),
  },
  {
    name: "Anthropic Claude",
    category: "LLM Connector",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 md:w-7 md:h-7">
        <path d="M17.304 3.541h-3.672l6.696 16.918H24Zm-10.608 0L0 20.459h3.744l1.37-3.553h7.005l1.369 3.553h3.744L10.536 3.541Zm-.371 10.223L8.616 7.82l2.291 5.945Z" />
      </svg>
    ),
  },
  {
    name: "PyMuPDF (PDF)",
    category: "Native Document Parser",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="w-6 h-6 md:w-7 md:h-7">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <line x1="10" y1="9" x2="8" y2="9" />
      </svg>
    ),
  },
  {
    name: "Web Crawler / HTTPX",
    category: "Live URL Ingest",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="w-6 h-6 md:w-7 md:h-7">
        <circle cx="12" cy="12" r="10" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>
    ),
  },
];

export default function SocialProof() {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <>
      <style>{`
        /* 4 identical sets translate by exactly -25% for a seamless, 100% gapless loop */
        @keyframes marquee-infinite-loop {
          0% {
            transform: translate3d(0, 0, 0);
          }
          100% {
            transform: translate3d(-25%, 0, 0);
          }
        }

        .marquee-track {
          will-change: transform;
          animation: marquee-infinite-loop 34s linear infinite;
        }

        /* Instant pause on hover via CSS */
        .marquee-container:hover .marquee-track,
        .marquee-track:hover,
        .marquee-card:hover {
          animation-play-state: paused !important;
        }
      `}</style>

      <section
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className="marquee-container relative w-full bg-[#080808] border-y border-white/[0.08] py-8 overflow-hidden group select-none"
      >
        {/* Subtle Section Label */}
        <div className="max-w-7xl mx-auto px-6 mb-4 text-center">
          <p className="text-[11px] font-mono uppercase tracking-[0.25em] text-white/35">
            Ingest &bull; Embed &bull; Connect With Any Provider
          </p>
        </div>

        {/* Gradient edge masks so icons fade smoothly in and out */}
        <div className="pointer-events-none absolute inset-y-0 left-0 z-20 w-24 md:w-44 bg-gradient-to-r from-[#080808] via-[#080808]/90 to-transparent" />
        <div className="pointer-events-none absolute inset-y-0 right-0 z-20 w-24 md:w-44 bg-gradient-to-l from-[#080808] via-[#080808]/90 to-transparent" />

        {/* Marquee Track: 4 duplicate sets guarantee it NEVER runs empty on any screen */}
        <div
          className="marquee-track flex w-max gap-4 sm:gap-6 items-center"
          style={{
            animationPlayState: isHovered ? "paused" : "running",
          }}
        >
          {[0, 1, 2, 3].map((setIndex) => (
            <div
              key={`set-${setIndex}`}
              className="flex shrink-0 gap-4 sm:gap-6 items-center"
            >
              {TECH_ECOSYSTEM.map((tech) => (
                <motion.div
                  key={`set-${setIndex}-${tech.name}`}
                  whileHover={{ scale: 1.15, y: -3 }}
                  transition={{ duration: 0.18, ease: "easeOut" }}
                  className="marquee-card group/card relative flex items-center justify-center w-14 h-14 sm:w-16 sm:h-16 rounded-2xl border border-white/[0.08] bg-white/[0.025] hover:bg-[#C8F432]/[0.08] hover:border-[#C8F432]/50 hover:shadow-[0_0_25px_rgba(200,244,50,0.22)] backdrop-blur-md transition-all duration-300 cursor-pointer"
                  title={`${tech.name} • ${tech.category}`}
                  aria-label={tech.name}
                >
                  {/* Subtle top reflection sheen */}
                  <div className="absolute inset-x-2 top-0 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent group-hover/card:via-[#C8F432]/50" />

                  {/* Icon Only — Authentic verified SVGs */}
                  <div className="text-white/55 group-hover/card:text-[#C8F432] transition-colors duration-200">
                    <tech.icon />
                  </div>
                </motion.div>
              ))}
            </div>
          ))}
        </div>
      </section>

      {/* Mobile speed adjustment */}
      <style>{`
        @media (max-width: 768px) {
          .marquee-track {
            animation-duration: 28s !important;
          }
        }
      `}</style>
    </>
  );
}
