"use client";

import Navbar from "@/components/landing/Navbar";
import Hero from "@/components/landing/Hero";
import SocialProof from "@/components/landing/SocialProof";
import ProblemSolution from "@/components/landing/ProblemSolution";
import HowItWorks from "@/components/landing/HowItWorks";
import FeaturesGrid from "@/components/landing/FeaturesGrid";
import VectorViewer from "@/components/landing/VectorViewer";
import Playground from "@/components/landing/Playground";
import UseCases from "@/components/landing/UseCases";
import TechStack from "@/components/landing/TechStack";
import TeamOpenSource from "@/components/landing/TeamOpenSource";
import MagneticCTA from "@/components/landing/MagneticCTA";
import Footer from "@/components/landing/Footer";

export default function LandingPage() {
  return (
    <div className="relative w-full min-h-screen bg-[#080808] text-[#F5F5F0] overflow-x-hidden selection:bg-[#C8F432] selection:text-black">
      {/* Floating Pill Navbar */}
      <Navbar />

      {/* 1. Hero: File-to-Vector Morph */}
      <Hero />

      {/* 2. Social Proof Strip: Infinite Marquee */}
      <SocialProof />

      {/* 3. Problem -> Solution: 3 Cards */}
      <ProblemSolution />

      {/* 4. How It Works: Connected Stepper Line */}
      <HowItWorks />

      {/* 5. Features Grid: Micro-interactions */}
      <FeaturesGrid />

      {/* Vector Space Viewer: Interactive Qdrant Inspector */}
      <VectorViewer />

      {/* 6. Live Demo / Playground: Real-time feedback & Citations */}
      <Playground />

      {/* 7. Use Cases: Tab Switch Morph */}
      <UseCases />

      {/* 8. Tech Stack: Central Node & Logo Orbit */}
      <TechStack />

      {/* 9. Team / Open Source: Ticking GitHub Stars & Contributors */}
      <TeamOpenSource />

      {/* 10. Final CTA: Magnetic Button + Breathing Lime Glow */}
      <MagneticCTA />

      {/* Footer */}
      <Footer />
    </div>
  );
}

