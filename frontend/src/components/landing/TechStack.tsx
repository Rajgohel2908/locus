"use client";

import { useState, useRef } from "react";
import { motion } from "framer-motion";

interface TechItem {
  name: string;
  role: string;
  angle: number; // starting angle in degrees
}

const innerOrbit: TechItem[] = [
  { name: "Python", role: "Runtime", angle: 0 },
  { name: "FastAPI", role: "API Layer", angle: 120 },
  { name: "PostgreSQL", role: "Database", angle: 240 },
];

const outerOrbit: TechItem[] = [
  { name: "Qdrant", role: "Vector DB", angle: 0 },
  { name: "OpenAI", role: "LLM Provider", angle: 90 },
  { name: "Next.js", role: "Frontend", angle: 180 },
  { name: "LangChain", role: "Orchestration", angle: 270 },
];

const INNER_RADIUS = 120;
const OUTER_RADIUS = 200;
const INNER_SPEED = 30; // seconds
const OUTER_SPEED = 45; // seconds

function OrbitRing({
  radius,
  items,
  speed,
  reverse,
  paused,
}: {
  radius: number;
  items: TechItem[];
  speed: number;
  reverse?: boolean;
  paused: boolean;
}) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const direction = reverse ? "reverse" : "normal";

  return (
    <>
      {/* SVG connection lines — drawn in absolute center coords */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ zIndex: 0 }}
      >
        {/* Orbit circle track */}
        <circle
          cx="50%"
          cy="50%"
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.04)"
          strokeWidth="1"
        />
      </svg>

      {/* Rotating container */}
      <div
        className="absolute inset-0"
        style={{
          animation: `spin-orbit ${speed}s linear infinite ${direction}`,
          animationPlayState: paused ? "paused" : "running",
        }}
      >
        {items.map((item, i) => {
          const angleDeg = item.angle;
          const angleRad = (angleDeg * Math.PI) / 180;
          const x = Math.cos(angleRad) * radius;
          const y = Math.sin(angleRad) * radius;

          return (
            <div
              key={item.name}
              className="absolute"
              style={{
                left: "50%",
                top: "50%",
                transform: `translate(${x}px, ${y}px) translate(-50%, -50%)`,
              }}
            >
              {/* Connection line from center */}
              <svg
                className="absolute pointer-events-none"
                style={{
                  width: `${Math.abs(x) + 2}px`,
                  height: `${Math.abs(y) + 2}px`,
                  left: x > 0 ? `-${x}px` : "0px",
                  top: y > 0 ? `-${y}px` : "0px",
                  overflow: "visible",
                  zIndex: -1,
                }}
              >
                <line
                  x1={x > 0 ? x : 0}
                  y1={y > 0 ? y : 0}
                  x2={x > 0 ? 0 : Math.abs(x)}
                  y2={y > 0 ? 0 : Math.abs(y)}
                  stroke="rgba(200, 244, 50, 0.08)"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                />
              </svg>

              {/* Counter-rotating badge */}
              <div
                className="relative"
                style={{
                  animation: `spin-orbit ${speed}s linear infinite ${reverse ? "normal" : "reverse"}`,
                  animationPlayState: paused ? "paused" : "running",
                }}
                onMouseEnter={() => setHoveredIdx(i)}
                onMouseLeave={() => setHoveredIdx(null)}
              >
                <div
                  className={`
                    whitespace-nowrap select-none cursor-default
                    rounded-full border font-mono text-xs px-3 py-1.5
                    transition-all duration-300
                    ${hoveredIdx === i
                      ? "bg-[#C8F432]/15 border-[#C8F432]/40 text-[#C8F432] scale-110"
                      : "bg-white/[0.04] border-white/[0.08] text-white/60"
                    }
                  `}
                >
                  {item.name}
                </div>

                {/* Tooltip */}
                {hoveredIdx === i && (
                  <div className="absolute left-1/2 -translate-x-1/2 -top-9 whitespace-nowrap rounded-md bg-[#1a1a1a] border border-white/10 px-2.5 py-1 text-[11px] font-body text-white/70 shadow-lg pointer-events-none">
                    {item.role}
                    <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-[#1a1a1a]" />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}

function MobileGrid() {
  const allTech = [
    ...innerOrbit.map((t) => ({ ...t, ring: "core" })),
    ...outerOrbit.map((t) => ({ ...t, ring: "ecosystem" })),
  ];

  return (
    <div className="grid grid-cols-2 gap-3 max-w-xs mx-auto">
      {/* Center node */}
      <div className="col-span-2 flex justify-center mb-2">
        <div className="w-20 h-20 rounded-full bg-[#C8F432] flex items-center justify-center">
          <span className="font-heading font-bold text-black text-xs text-center leading-tight">
            LOCUS
            <br />
            Engine
          </span>
        </div>
      </div>
      {allTech.map((t) => (
        <div
          key={t.name}
          className="flex items-center gap-2.5 rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2.5"
        >
          <div className="w-2 h-2 rounded-full bg-[#C8F432]/40 shrink-0" />
          <div>
            <div className="font-mono text-xs text-white/80">{t.name}</div>
            <div className="font-body text-[10px] text-white/35">{t.role}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function TechStack() {
  const [paused, setPaused] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  return (
    <section className="bg-[#080808] py-20 overflow-hidden">
      <div className="mx-auto max-w-5xl px-6">
        {/* Header */}
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          <h2 className="font-heading text-3xl md:text-4xl font-semibold text-[#F5F5F0]">
            Built With
          </h2>
          <p className="mt-3 text-white/50 font-body text-sm md:text-base max-w-md mx-auto">
            Modern infrastructure for reliable, fast retrieval-augmented generation.
          </p>
        </motion.div>

        {/* Mobile grid */}
        <motion.div
          className="md:hidden"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease: "easeOut", delay: 0.15 }}
        >
          <MobileGrid />
        </motion.div>

        {/* Desktop orbit */}
        <motion.div
          className="hidden md:flex justify-center"
          initial={{ opacity: 0, scale: 0.92 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: "easeOut", delay: 0.1 }}
        >
          <div
            ref={containerRef}
            className="relative"
            style={{ width: `${OUTER_RADIUS * 2 + 100}px`, height: `${OUTER_RADIUS * 2 + 100}px` }}
            onMouseEnter={() => setPaused(true)}
            onMouseLeave={() => setPaused(false)}
          >
            {/* Center node */}
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
              <div className="w-24 h-24 rounded-full bg-[#C8F432] flex items-center justify-center shadow-[0_0_60px_rgba(200,244,50,0.15)]">
                <span className="font-heading font-bold text-black text-sm text-center leading-tight">
                  LOCUS
                  <br />
                  Engine
                </span>
              </div>
            </div>

            {/* Inner orbit */}
            <OrbitRing
              radius={INNER_RADIUS}
              items={innerOrbit}
              speed={INNER_SPEED}
              paused={paused}
            />

            {/* Outer orbit (reverse) */}
            <OrbitRing
              radius={OUTER_RADIUS}
              items={outerOrbit}
              speed={OUTER_SPEED}
              reverse
              paused={paused}
            />
          </div>
        </motion.div>
      </div>

      {/* Keyframes for orbit rotation */}
      <style jsx>{`
        @keyframes spin-orbit {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </section>
  );
}
