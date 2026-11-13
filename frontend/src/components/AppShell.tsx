"use client";

import React from "react";
import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLanding = pathname === "/" || pathname === "/landing";

  if (isLanding) {
    return (
      <div className="min-h-screen bg-[#080808] text-[#F5F5F0] selection:bg-[#C8F432] selection:text-black overflow-x-hidden">
        {children}
      </div>
    );
  }

  return (
    <div className="flex min-h-screen w-full bg-obsidian text-fg">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 bg-obsidian">
        <TopBar />
        <main className="flex-1 p-8 overflow-y-auto max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

