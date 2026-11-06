"use client";

import React, { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

export default function MermaidRenderer({ chart }: { chart: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: "dark",
      securityLevel: "strict",
      themeVariables: {
        darkMode: true,
        background: "#09090B",
        primaryColor: "#111113",
        primaryTextColor: "#FAFAFA",
        primaryBorderColor: "#3B82F6",
        lineColor: "#A1A1AA",
        secondaryColor: "#18181B",
        tertiaryColor: "#2A2A2E",
      },
    });

    let isMounted = true;
    const renderChart = async () => {
      try {
        if (!chart || !containerRef.current) return;
        const id = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
        const { svg: renderedSvg } = await mermaid.render(id, chart);

        if (isMounted && containerRef.current) {
          const parser = new DOMParser();
          const doc = parser.parseFromString(renderedSvg, "image/svg+xml");
          const svgElem = doc.documentElement;
          containerRef.current.replaceChildren(svgElem);
          setError(null);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || "Failed to render graph");
        }
      }
    };

    renderChart();
    return () => {
      isMounted = false;
    };
  }, [chart]);

  if (error) {
    return (
      <div className="p-4 rounded bg-obsidian border border-crimson/30 text-crimson text-xs font-mono">
        Mermaid Render Error: {error}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="overflow-x-auto p-4 flex justify-center bg-obsidian rounded-lg border border-graphite"
    />
  );
}

