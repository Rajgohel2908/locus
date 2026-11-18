"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import {
  Database,
  MessageSquare,
  GitCompare,
  Cpu,
  Activity,
  Menu,
} from "lucide-react";
import { motion } from "framer-motion";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  const isLanding = pathname === "/" || pathname === "/landing";

  if (isLanding) {
    return (
      <div className="min-h-screen bg-[#080808] text-[#F5F5F0] selection:bg-[#C8F432] selection:text-black overflow-x-hidden">
        {children}
      </div>
    );
  }

  const mobileNavItems = [
    { name: "Sources", href: "/sources", icon: Database },
    { name: "Ask", href: "/ask", icon: MessageSquare },
    { name: "Compare", href: "/compare", icon: GitCompare },
    { name: "Pipeline", href: "/pipeline", icon: Cpu },
    { name: "Doctor", href: "/doctor", icon: Activity },
  ];

  return (
    <div className="flex min-h-screen w-full bg-[#080808] text-fg selection:bg-[#C8F432] selection:text-black">
      {/* Sidebar: persistent on desktop, slide-out drawer on mobile */}
      <Sidebar
        isOpen={isMobileNavOpen}
        onClose={() => setIsMobileNavOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#080808]">
        {/* TopBar with health telemetry and mobile menu button */}
        <TopBar onOpenMobileNav={() => setIsMobileNavOpen(true)} />

        {/* Studio Page Content */}
        <main className="flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:p-8 pb-28 lg:pb-8 max-w-7xl w-full mx-auto overflow-x-hidden">
          {children}
        </main>

        {/* ─── Mobile Floating Bottom Navigation Bar (lg:hidden) ─── */}
        <nav
          aria-label="Mobile Navigation"
          className="lg:hidden fixed bottom-3 inset-x-3 z-30 bg-[#0E0E12]/90 backdrop-blur-xl border border-white/10 rounded-2xl p-1.5 shadow-[0_12px_40px_rgba(0,0,0,0.85)] max-w-md mx-auto"
        >
          <div className="grid grid-cols-6 gap-1 items-center">
            {mobileNavItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                pathname === item.href ||
                (item.href !== "/" && pathname?.startsWith(item.href));

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex flex-col items-center justify-center py-2 px-1 rounded-xl text-[10px] font-mono transition-all relative ${
                    isActive
                      ? "text-[#C8F432] font-semibold"
                      : "text-white/50 hover:text-white"
                  }`}
                >
                  {isActive && (
                    <motion.div
                      layoutId="mobileNavActivePill"
                      className="absolute inset-0 bg-[#C8F432]/10 border border-[#C8F432]/30 rounded-xl"
                      transition={{ type: "spring", stiffness: 450, damping: 30 }}
                    />
                  )}
                  <Icon
                    className={`w-4 h-4 mb-1 z-10 transition-colors ${
                      isActive ? "text-[#C8F432]" : "text-white/60"
                    }`}
                  />
                  <span className="z-10 leading-none truncate max-w-full">
                    {item.name}
                  </span>
                </Link>
              );
            })}

            {/* Menu Trigger to open full drawer */}
            <button
              onClick={() => setIsMobileNavOpen(true)}
              className="flex flex-col items-center justify-center py-2 px-1 rounded-xl text-[10px] font-mono text-white/50 hover:text-white transition-all cursor-pointer"
            >
              <Menu className="w-4 h-4 mb-1 text-white/60" />
              <span className="leading-none">More</span>
            </button>
          </div>
        </nav>
      </div>
    </div>
  );
}
