import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";

export const metadata: Metadata = {
  title: "Sift — Trustworthy RAG & Data Studio",
  description: "Audited, versioned, evidence-gated RAG & Data Quality Studio",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="font-body bg-obsidian text-fg min-h-screen flex antialiased">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0 bg-obsidian">
          <TopBar />
          <main className="flex-1 p-8 overflow-y-auto max-w-7xl w-full mx-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
