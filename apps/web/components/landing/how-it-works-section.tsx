"use client";

import { useEffect, useRef, useState } from "react";

const steps = [
  {
    number: "01",
    title: "Customer request",
    tag: "Ingest",
    description:
      "A buyer submits an issue via chat with order context and photo evidence, or the system proactively detects an in-transit delivery SLA breach.",
  },
  {
    number: "02",
    title: "Verify & identify",
    tag: "Authenticate",
    description:
      "Backend authenticates buyer session, verifies order ownership, scopes data access, and blocks duplicate active cases for the same item.",
  },
  {
    number: "03",
    title: "Investigate",
    tag: "Read-only tools",
    description:
      "Agent executes deterministic read-only tools: fetches order line items, live carrier tracking timestamps, warehouse status, and seller policies.",
  },
  {
    number: "04",
    title: "Evaluate policy",
    tag: "Deterministic rule check",
    description:
      "Deterministic policy engine checks delivery dates, return windows, damage proof requirements, refund ceilings, and restocking rules. LLM never decides policy.",
  },
  {
    number: "05",
    title: "Decision path",
    tag: "Execute or Escalate",
    description:
      "Within pre-authorized limits: autonomous action is prepared. If value exceeds ceiling or proof is ambiguous: queued for seller 1-click approval.",
  },
  {
    number: "06",
    title: "Verify, notify & log",
    tag: "Audit trail",
    description:
      "Outcome is verified against carrier/payment API, buyer is notified with next steps, and complete investigation is written to the immutable audit log.",
  },
];

export function HowItWorksSection() {
  const [activeStep, setActiveStep] = useState(0);
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true);
      },
      { threshold: 0.1 }
    );

    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % steps.length);
    }, 4500);
    return () => clearInterval(interval);
  }, []);

  return (
    <section
      id="how-it-works"
      ref={sectionRef}
      className="relative py-24 lg:py-32 bg-[oklch(0.09_0.01_260)] text-white overflow-hidden"
    >
      <div className="absolute bottom-0 left-0 w-[400px] h-[400px] rounded-full bg-white/[0.02] blur-[100px] pointer-events-none" />

      <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header */}
        <div className="relative mb-12 lg:mb-16 grid lg:grid-cols-2 gap-4 lg:gap-12 items-end">
          <div className="overflow-hidden pb-0 lg:pb-12">
            <div
              className={`transition-all duration-1000 ${
                isVisible ? "translate-x-0 opacity-100" : "-translate-x-12 opacity-0"
              }`}
            >
              <span className="inline-flex items-center gap-3 text-sm font-mono text-white/40 mb-8">
                <span className="w-12 h-px bg-white/20" />
                Autonomous Resolution Loop
              </span>
            </div>

            <h2
              className={`text-6xl md:text-7xl lg:text-[110px] font-display tracking-tight leading-[0.88] transition-all duration-1000 delay-100 ${
                isVisible ? "translate-y-0 opacity-100" : "translate-y-16 opacity-0"
              }`}
            >
              <span className="block">Investigate.</span>
              <span className="block text-white/30">Decide.</span>
              <span className="block text-white/10">Act &amp; Verify.</span>
            </h2>
          </div>

          <div
            className={`relative h-[320px] lg:h-[560px] overflow-hidden transition-all duration-1000 delay-200 ${
              isVisible ? "opacity-100" : "opacity-0"
            }`}
          >
            <img
              src="/images/tree.png"
              alt=""
              aria-hidden="true"
              className="absolute bottom-0 left-0 w-full h-full object-contain object-bottom"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-[oklch(0.09_0.01_260)] via-transparent to-transparent pointer-events-none" />
          </div>
        </div>

        {/* 6-step customer journey grid (3x2 desktop, 2x3 tablet, 1x6 mobile) */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {steps.map((step, index) => (
            <button
              key={step.number}
              type="button"
              onClick={() => setActiveStep(index)}
              className={`relative text-left p-6 lg:p-8 border transition-all duration-300 rounded-sm ${
                activeStep === index
                  ? "bg-black border-white/60"
                  : "bg-black/60 border-white/15 hover:border-white/40"
              }`}
            >
              {/* Step number and tag */}
              <div className="flex items-center justify-between gap-4 mb-6">
                <div className="flex items-center gap-3">
                  <span
                    className={`text-2xl lg:text-3xl font-display transition-colors duration-300 ${
                      activeStep === index ? "text-[#eca8d6]" : "text-white/30"
                    }`}
                  >
                    {step.number}
                  </span>
                  <div className="w-8 h-px bg-white/10" />
                </div>
                <span className="text-[11px] font-mono tracking-wider uppercase text-white/50 px-2 py-0.5 rounded border border-white/10 bg-white/[0.02]">
                  {step.tag}
                </span>
              </div>

              {/* Title */}
              <h3 className="text-xl lg:text-2xl font-display text-white mb-3">
                {step.title}
              </h3>

              {/* Description */}
              <p
                className={`text-sm text-white/65 leading-relaxed transition-opacity duration-300 ${
                  activeStep === index ? "opacity-100" : "opacity-75"
                }`}
              >
                {step.description}
              </p>

              {/* Active indicator */}
              <div
                className={`absolute bottom-0 left-0 right-0 h-0.5 bg-[#eca8d6] transition-transform duration-300 origin-left ${
                  activeStep === index ? "scale-x-100" : "scale-x-0"
                }`}
              />
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
