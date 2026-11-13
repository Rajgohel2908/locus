"use client";

import { useRef, useState, useCallback } from "react";
import { motion, useAnimationFrame } from "framer-motion";

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
    ctx.fillStyle = "rgba(255,255,255,0.05)";

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
      const clamp = 10;
      setTranslate({
        x: (dx / maxDist) * clamp * 2,
        y: (dy / maxDist) * clamp * 2,
      });
    },
    []
  );

  const handleMouseLeave = useCallback(() => {
    setTranslate({ x: 0, y: 0 });
  }, []);

  return (
    <section id="get-started" className="relative w-full py-32 overflow-hidden bg-[#080808]">
      <DotGrid />

      <div className="relative z-10 flex flex-col items-center text-center px-6">
        <motion.h2
          className="font-heading text-4xl md:text-5xl font-bold text-white max-w-2xl"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          Ready to build your RAG pipeline?
        </motion.h2>

        <motion.p
          className="mt-5 text-white/50 font-body text-base md:text-lg max-w-lg"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease: "easeOut", delay: 0.1 }}
        >
          Connect your data, vectorize, and start chatting — in 5 minutes.
        </motion.p>

        <motion.div
          className="mt-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease: "easeOut", delay: 0.2 }}
        >
          <motion.button
            ref={buttonRef}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            animate={{
              x: translate.x,
              y: translate.y,
              boxShadow: [
                "0 0 30px rgba(200,244,50,0.3)",
                "0 0 60px rgba(200,244,50,0.5)",
                "0 0 30px rgba(200,244,50,0.3)",
              ],
            }}
            transition={{
              x: { type: "tween", duration: 0.2, ease: "easeOut" },
              y: { type: "tween", duration: 0.2, ease: "easeOut" },
              boxShadow: {
                duration: 3,
                repeat: Infinity,
                ease: "easeInOut",
              },
            }}
            className="bg-[#C8F432] text-black px-8 py-4 rounded-full text-lg font-semibold font-body cursor-pointer select-none hover:brightness-110 active:scale-[0.97] transition-[filter,transform] duration-200"
          >
            Start Building — Free
          </motion.button>
        </motion.div>

        <motion.a
          href="/docs"
          className="mt-6 text-sm text-white/40 hover:text-white/60 transition-colors duration-300 font-body"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease: "easeOut", delay: 0.35 }}
        >
          View Documentation →
        </motion.a>
      </div>
    </section>
  );
}
