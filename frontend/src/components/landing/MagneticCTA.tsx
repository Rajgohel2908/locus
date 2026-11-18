"use client";

import { useRef, useState, useCallback } from "react";
import { motion, useAnimationFrame } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";

function DotGrid() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const offsetRef = useRef(0);

  useAnimationFrame((_, delta) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;

    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.scale(dpr, dpr);
    }

    offsetRef.current += delta * 0.008;
    const offset = offsetRef.current;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "rgba(255,255,255,0.04)";

    const spacing = 40;
    const dotR = 1.2;

    for (let x = -spacing; x < w + spacing; x += spacing) {
      for (let y = -spacing; y < h + spacing; y += spacing) {
        const dx = x + Math.sin((y + offset) * 0.01) * 6;
        const dy = y + Math.cos((x + offset) * 0.01) * 6;
        ctx.beginPath();
        ctx.arc(dx, dy, dotR, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  });

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      aria-hidden="true"
    />
  );
}

export default function MagneticCTA() {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });

  // Principle 2: Anticipation + Principle 13: Fitts's Law (Magnetic pull tracks the cursor)
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLButtonElement>) => {
      const btn = buttonRef.current;
      if (!btn) return;
      const rect = btn.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = e.clientX - cx;
      const dy = e.clientY - cy;
      const maxDist = Math.max(rect.width, rect.height);
      const clamp = 14;
      setTranslate({
        x: (dx / maxDist) * clamp * 2,
        y: (dy / maxDist) * clamp * 2,
      });
    },
    []
  );

  // Principle 5: Follow through (Snaps back with spring overshoot)
  const handleMouseLeave = useCallback(() => {
    setTranslate({ x: 0, y: 0 });
  }, []);

  return (
    <section id="get-started" className="relative w-full py-32 overflow-hidden bg-[#080808]">
      <DotGrid />

      {/* Atmospheric Focus Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-[radial-gradient(circle_at_center,rgba(200,244,50,0.12)_0%,transparent_65%)] blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center text-center px-6">
        <motion.h2
          className="font-heading text-4xl md:text-5xl lg:text-6xl font-bold text-white max-w-2xl tracking-tight leading-[1.1]"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        >
          Ready to build your RAG pipeline?
        </motion.h2>

        <motion.p
          className="mt-5 text-white/50 font-body text-base md:text-lg max-w-lg"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1], delay: 0.08 }}
        >
          Connect your data, vectorize, and start chatting — in 5 minutes.
        </motion.p>

        {/* Principle 13: Fitts's Law + Principle 1: Squash & Stretch + Principle 10: Exaggerated Feedback */}
        <motion.div
          className="mt-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1], delay: 0.16 }}
        >
          <motion.button
            ref={buttonRef}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            onClick={() => {
              window.location.href = "/sources";
            }}
            /* Magnetic translation with spring physics */
            animate={{
              x: translate.x,
              y: translate.y,
            }}
            /* Principle 1: Squash and stretch on tap */
            whileTap={{ scaleX: 1.06, scaleY: 0.91 }}
            transition={{
              type: "spring",
              stiffness: 350,
              damping: 18,
            }}
            className="group relative bg-[#C8F432] text-black px-9 py-4.5 rounded-full text-base md:text-lg font-semibold font-body cursor-pointer select-none shadow-[0_0_35px_rgba(200,244,50,0.4)] hover:brightness-105 active:brightness-95 transition-all flex items-center gap-2.5 overflow-hidden"
          >
            <span>Start Building — Free</span>
            {/* Principle 2: Anticipation arrow recoil & jump */}
            <motion.div
              className="flex items-center"
              initial={{ x: 0 }}
              whileHover={{ x: [0, -3, 4] }}
              transition={{ duration: 0.22, ease: "easeInOut" }}
            >
              <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" strokeWidth={2} />
            </motion.div>
          </motion.button>
        </motion.div>

        {/* Principle 14: Bigger Hit Area on Link */}
        <motion.a
          href="/sources"
          className="relative mt-7 text-sm font-mono text-white/50 hover:text-white transition-colors duration-150 p-2 -m-2"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1], delay: 0.25 }}
        >
          Explore Sandbox Sources →
        </motion.a>
      </div>
    </section>
  );
}
