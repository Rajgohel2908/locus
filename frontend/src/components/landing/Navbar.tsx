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
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <nav
        className={[
          "pointer-events-auto flex items-center justify-between w-full max-w-5xl h-16 pl-6 pr-4 rounded-full border border-white/10 backdrop-blur-xl transition-colors duration-500 shadow-2xl",
          scrolled ? "bg-[#080808]/95" : "bg-[#080808]/80",
        ].join(" ")}
      >
        {/* Brand Logo */}
        <Link href="/" className="flex items-center gap-[10px] shrink-0 group select-none">
          <img src="/locus-icon.svg" className="w-8 h-8 group-hover:scale-105 transition-transform" alt="LOCUS" />
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
          <div className="hidden lg:flex items-center gap-5">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={(e) => handleClick(e, link.href)}
                className="text-xs font-mono text-white/60 hover:text-white transition-colors duration-200"
              >
                {link.label}
              </a>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/sources"
              className="bg-[#C8F432] text-black text-xs font-semibold px-4 py-2 rounded-full font-body hover:brightness-110 active:scale-[0.97] transition-all duration-200 flex items-center gap-1 shadow-[0_0_15px_rgba(200,244,50,0.3)]"
            >
              <span>Launch Studio</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </nav>
    </motion.header>
  );
}
