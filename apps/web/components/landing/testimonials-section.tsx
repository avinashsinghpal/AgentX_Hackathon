"use client";

import { useEffect, useState, useRef } from "react";
import { AlertCircle, Split, ShieldAlert, GitFork, History } from "lucide-react";

const frictions = [
  {
    number: "01",
    title: "Fragmented Information",
    icon: Split,
    description:
      "Customer support teams constantly toggle between store admin, courier dashboards, and payment gateways. Critical order context is scattered across disparate screens.",
  },
  {
    number: "02",
    title: "Complex Indian Fulfillment",
    icon: GitFork,
    description:
      "Multiple courier partners, regional PIN code serviceability, transit zones, and COD settlements create operational edge cases where generic bots fail completely.",
  },
  {
    number: "03",
    title: "Inconsistent Decisions",
    icon: AlertCircle,
    description:
      "Manual agents make ad-hoc exceptions without enforcing policy return windows or spending limits, causing customer confusion and unexpected merchant losses.",
  },
  {
    number: "04",
    title: "Return & Refund Risks",
    icon: ShieldAlert,
    description:
      "Blindly automating refunds creates exposure to duplicate submissions, invalid damage claims, and missing transit verification without evidence checks.",
  },
  {
    number: "05",
    title: "Zero Traceability",
    icon: History,
    description:
      "Traditional support tickets close with no immutable audit trail of what was checked, who approved the exception, or which carrier scan validated the claim.",
  },
];

export function TestimonialsSection() {
  const [activeFriction, setActiveFriction] = useState(0);
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);

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

  return (
    <section
      ref={sectionRef}
      className="relative py-24 lg:py-36 bg-foreground text-background overflow-hidden"
    >
      <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header */}
        <div className="mb-16 lg:mb-20">
          <span className="inline-flex items-center gap-3 text-sm font-mono text-background/60 mb-6">
            <span className="w-12 h-px bg-background/30" />
            The Operational Reality
          </span>

          <h2
            className={`text-4xl md:text-6xl lg:text-[88px] font-display tracking-tight leading-[0.92] max-w-4xl transition-all duration-1000 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            Answering a query is not the same as{" "}
            <span className="italic underline underline-offset-8 decoration-background/30">
              resolving it.
            </span>
          </h2>

          <p className="mt-6 text-lg lg:text-xl text-background/70 max-w-2xl leading-relaxed">
            Generic chatbots reply with polite platitudes while orders remain stuck. Small online merchants face five fundamental operational breakdowns every day:
          </p>
        </div>

        {/* Frictions Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {frictions.map((item, idx) => {
            const Icon = item.icon;
            const isFeatured = idx === 0;
            return (
              <div
                key={item.number}
                className={`p-8 border rounded-sm transition-all duration-300 ${
                  isFeatured
                    ? "border-background/40 bg-background/10 lg:col-span-2"
                    : "border-background/20 bg-background/5 hover:border-background/30"
                }`}
                onMouseEnter={() => setActiveFriction(idx)}
              >
                <div className="flex items-center justify-between mb-6">
                  <span className="text-2xl font-display text-background/40">
                    {item.number}
                  </span>
                  <div className="w-8 h-8 rounded-full border border-background/20 flex items-center justify-center text-background/80">
                    <Icon className="w-4 h-4" />
                  </div>
                </div>

                <h3 className="text-2xl font-display mb-3 text-background">
                  {item.title}
                </h3>
                <p className="text-sm text-background/70 leading-relaxed">
                  {item.description}
                </p>
              </div>
            );
          })}

          {/* Solution Callout Card */}
          <div className="p-8 border border-background/40 bg-background text-foreground rounded-sm flex flex-col justify-between">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground block mb-3">
                The SellerResolve Answer
              </span>
              <h3 className="text-2xl font-display mb-3">
                Investigate. Decide. Act. Verify.
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                We combine deep tool execution with deterministic policy validation so issues are actually resolved without merchant burnout.
              </p>
            </div>
            <div className="pt-6 border-t border-border mt-6">
              <span className="text-xs font-mono text-foreground font-medium">
                Production-Bound Prototype • Break The Bug
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
