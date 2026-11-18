"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Database,
  MessageSquare,
  GitCompare,
  Cpu,
  CheckSquare,
  Activity,
  Sparkles,
  X,
  Layers,
  ShieldCheck,
  ChevronRight,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const pathname = usePathname();

  // Close mobile drawer on route change
  useEffect(() => {
    if (onClose) onClose();
  }, [pathname]);

  // Lock body scroll when mobile drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  const navItems = [
    { name: "Sources & Data", href: "/sources", icon: Database, badge: "Data" },
    { name: "Chat & Ask", href: "/ask", icon: MessageSquare, badge: "RAG" },
    { name: "Strategy Compare", href: "/compare", icon: GitCompare, badge: "Eval" },
    { name: "Pipeline Architecture", href: "/pipeline", icon: Cpu, badge: "Core" },
    { name: "Evaluation Suites", href: "/evaluation", icon: CheckSquare, badge: "Triad" },
    { name: "RAG Doctor", href: "/doctor", icon: Activity, badge: "Audit" },
  ];

  const sidebarContent = (
    <div className="flex flex-col h-full justify-between">
      {/* Top Section: Brand & Nav */}
      <div>
        {/* Brand Header */}
        <div className="h-16 px-5 flex items-center justify-between border-b border-graphite/80 bg-carbon/50">
          <Link href="/landing" className="flex items-center gap-3 group">
            <img
              src="/locus-icon.svg"
              className="w-8 h-8 shrink-0 transition-transform duration-200 group-hover:scale-105"
              alt="LOCUS"
            />
            <div className="flex flex-col">
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
                  className="text-[16px] ml-[2.5px] uppercase text-white/95 font-light"
                >
                  OCUS
                </span>
              </span>
              <span className="text-[9px] text-[#C8F432]/70 font-mono tracking-wider font-semibold">
                STUDIO CONSOLE
              </span>
            </div>
          </Link>

          {/* Mobile Close Button */}
          {onClose && (
            <button
              onClick={onClose}
              aria-label="Close Navigation"
              className="lg:hidden p-2 -mr-2 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Navigation Items */}
        <div className="px-3 py-5 space-y-6 overflow-y-auto">
          {/* Landing / Showcase Link */}
          <div className="space-y-1">
            <div className="px-3 pb-1.5 text-[10px] font-semibold tracking-wider text-muted/60 uppercase font-mono">
              Public Portal
            </div>
            <Link
              href="/landing"
              className="flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all text-[#C8F432] bg-[#C8F432]/10 border border-[#C8F432]/30 hover:bg-[#C8F432]/20 hover:border-[#C8F432]/50 shadow-[0_0_15px_rgba(200,244,50,0.1)] group"
            >
              <div className="flex items-center gap-3">
                <Sparkles className="w-4 h-4 flex-shrink-0 text-[#C8F432] transition-transform duration-200 group-hover:rotate-12" />
                <span className="font-semibold">Product Landing</span>
              </div>
              <ChevronRight className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
            </Link>
          </div>

          {/* Studio Navigation Links */}
          <div className="space-y-1">
            <div className="px-3 pb-1.5 text-[10px] font-semibold tracking-wider text-muted/60 uppercase font-mono">
              Studio Workspace
            </div>
            <div className="space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/" && pathname?.startsWith(item.href));

                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 relative ${
                      isActive
                        ? "bg-[#C8F432]/12 text-[#C8F432] font-semibold border border-[#C8F432]/30 shadow-[0_0_15px_rgba(200,244,50,0.08)]"
                        : "text-muted hover:text-fg hover:bg-white/[0.04] border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon
                        className={`w-4 h-4 flex-shrink-0 transition-colors ${
                          isActive ? "text-[#C8F432]" : "text-muted/80"
                        }`}
                      />
                      <span>{item.name}</span>
                    </div>

                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                        isActive
                          ? "bg-[#C8F432]/20 text-[#C8F432] font-semibold"
                          : "bg-white/[0.04] text-muted/60"
                      }`}
                    >
                      {item.badge}
                    </span>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-graphite/80 bg-carbon/50 text-xs text-muted/70 flex flex-col gap-2 font-mono">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#C8F432] animate-pulse shadow-[0_0_8px_#C8F432]"></span>
            <span className="text-white/80 font-medium text-xs">Engine Active</span>
          </div>
          <span className="text-[10px] text-[#C8F432] bg-[#C8F432]/10 px-2 py-0.5 rounded border border-[#C8F432]/20">
            pgvector • 384d
          </span>
        </div>
        <div className="text-[10px] text-muted/50 flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-[#C8F432]/70" />
          <span>Evidence Gate Enforced</span>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* ─── Desktop Persistent Sidebar ─────────────────────────────── */}
      <aside className="hidden lg:flex w-64 bg-carbon border-r border-graphite flex-col min-h-screen select-none shrink-0 sticky top-0 h-screen z-20">
        {sidebarContent}
      </aside>

      {/* ─── Mobile Slide-out Drawer ─────────────────────────────────── */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={onClose}
              className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 lg:hidden"
              aria-hidden="true"
            />

            {/* Drawer */}
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 380, damping: 30 }}
              className="fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] bg-[#0E0E11] border-r border-white/10 flex flex-col shadow-[0_0_50px_rgba(0,0,0,0.9)] lg:hidden"
            >
              {sidebarContent}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

export default Sidebar;
