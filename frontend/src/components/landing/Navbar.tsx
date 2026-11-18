"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

const navLinks = [
  { label: "Features", href: "#features" },
  { label: "How it Works", href: "#how-it-works" },
  { label: "Vector DB", href: "#vector-viewer" },
  { label: "Playground", href: "#playground" },
  { label: "Use Cases", href: "#use-cases" },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 32);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (href.startsWith("#")) {
      e.preventDefault();
      const id = href.replace("#", "");
      const el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        window.history.replaceState(null, "", href);
      }
    }
  };

  return (
    <motion.header
      className="fixed top-0 left-0 right-0 z-50 flex justify-center px-4 pt-4 pointer-events-none"
      initial={{ y: -60, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      /* Principle 6: Slow in & slow out with spring settle */
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
    >
      <nav
        className={[
          "pointer-events-auto flex items-center justify-between w-full max-w-5xl h-16 pl-6 pr-4 rounded-full border border-white/10 backdrop-blur-xl transition-all duration-300 shadow-[0_20px_50px_rgba(0,0,0,0.8)]",
          scrolled ? "bg-[#080808]/95 border-white/15" : "bg-[#080808]/80",
        ].join(" ")}
      >
        {/* Brand Logo with Principle 1: Squash & Stretch + Principle 2: Anticipation */}
        <Link href="/" className="flex items-center gap-[10px] shrink-0 group select-none relative py-2">
          <motion.img
            src="/locus-icon.svg"
            className="w-8 h-8"
            alt="LOCUS"
            whileHover={{ scale: 1.08, rotate: 4 }}
            whileTap={{ scaleX: 1.1, scaleY: 0.88 }}
            transition={{ type: "spring", stiffness: 450, damping: 20 }}
          />
          <span className="inline-flex items-baseline leading-none">
            <span
              style={{ fontFamily: 'var(--font-locus-l, "Niconne", cursive)' }}
              className="text-[29px] font-normal text-white -translate-y-[1px]"
            >
              L
            </span>
            <span
              style={{
                fontFamily: 'var(--font-locus-sans, "Satoshi", sans-serif)',
                fontWeight: 300,
                letterSpacing: "0.22em",
              }}
              className="text-[18px] ml-[3px] uppercase text-white/95 font-light"
            >
              OCUS
            </span>
          </span>
        </Link>

        {/* Nav links + CTA */}
        <div className="flex items-center gap-6">
          {/* Principle 14: Bigger Hit Areas & Principle 15: Hick's Law */}
          <div className="hidden lg:flex items-center gap-2">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={(e) => handleClick(e, link.href)}
                /* Hit area expanded with px-3 py-2 -my-2 relative for effortless clicking */
                className="relative px-3 py-2 text-xs font-mono text-white/60 hover:text-white rounded-lg transition-colors duration-150 hover:bg-white/[0.04] before:absolute before:-inset-1 before:content-['']"
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* Principle 13: Fitts's Law + Principle 1: Squash & Stretch + Principle 2: Anticipation */}
          <div className="flex items-center gap-2">
            <Link href="/sources">
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scaleX: 1.05, scaleY: 0.92 }}
                transition={{ type: "spring", stiffness: 500, damping: 22 }}
                className="group relative bg-[#C8F432] text-black text-xs font-semibold px-4 py-2.5 rounded-full font-body hover:brightness-110 active:brightness-95 transition-all shadow-[0_0_20px_rgba(200,244,50,0.3)] flex items-center gap-1.5 cursor-pointer overflow-hidden"
              >
                <span>Launch Studio</span>
                {/* Principle 2: Anticipation windup — arrow pulls back slightly then drives forward */}
                <motion.div
                  className="flex items-center"
                  initial={{ x: 0 }}
                  whileHover={{ x: [0, -2, 3] }}
                  transition={{ duration: 0.25, ease: "easeInOut" }}
                >
                  <ArrowUpRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </motion.div>
              </motion.button>
            </Link>
          </div>
        </div>
      </nav>
    </motion.header>
  );
}
