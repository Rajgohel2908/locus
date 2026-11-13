"use client";

import React from "react";

interface LocusWordmarkProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

interface LocusLogoProps {
  showIcon?: boolean;
  iconSize?: number;
  size?: "sm" | "md" | "lg";
  className?: string;
  tagline?: boolean;
}

export function LocusWordmark({
  size = "md",
  className = "",
}: LocusWordmarkProps) {
  // Proportions tuned specifically for Niconne 'L' + Satoshi 'OCUS'
  const config = {
    sm: {
      lSize: "text-[23px]",
      ocusSize: "text-[14px]",
      spacing: "ml-[2px]",
      tracking: "tracking-[0.22em]",
      niconneOffset: "-translate-y-[0.5px]",
    },
    md: {
      lSize: "text-[29px]",
      ocusSize: "text-[18px]",
      spacing: "ml-[3px]",
      tracking: "tracking-[0.22em]",
      niconneOffset: "-translate-y-[1px]",
    },
    lg: {
      lSize: "text-[42px]",
      ocusSize: "text-[26px]",
      spacing: "ml-[4px]",
      tracking: "tracking-[0.24em]",
      niconneOffset: "-translate-y-[1.5px]",
    },
  }[size];

  return (
    <span
      className={`inline-flex items-baseline select-none text-white leading-none ${className}`}
    >
      <span
        style={{
          fontFamily: 'var(--font-locus-l, "Niconne", cursive)',
        }}
        className={`${config.lSize} font-normal text-white leading-none ${config.niconneOffset}`}
      >
        L
      </span>
      <span
        style={{
          fontFamily: 'var(--font-locus-sans, "Satoshi", sans-serif)',
          fontWeight: 300,
          letterSpacing: "0.22em",
        }}
        className={`${config.ocusSize} ${config.spacing} uppercase leading-none text-white/95 font-light`}
      >
        OCUS
      </span>
    </span>
  );
}

export function LocusLogo({
  showIcon = true,
  iconSize = 32,
  size = "md",
  className = "",
  tagline = false,
}: LocusLogoProps) {
  return (
    <div className={`inline-flex items-center gap-[10px] select-none ${className}`}>
      {showIcon && (
        <img
          src="/locus-icon.svg"
          width={iconSize}
          height={iconSize}
          className="shrink-0 transition-transform duration-200 group-hover:scale-105"
          alt="LOCUS"
        />
      )}
      <div className="flex flex-col">
        <LocusWordmark size={size} />
        {tagline && (
          <span
            style={{
              fontFamily: 'var(--font-locus-sans, "Satoshi", sans-serif)',
              letterSpacing: "0.24em",
            }}
            className="text-[8.5px] font-medium text-white/50 uppercase mt-1 tracking-widest font-mono"
          >
            TRAIN &bull; EMBED &bull; RETRIEVE
          </span>
        )}
      </div>
    </div>
  );
}

export default LocusLogo;

