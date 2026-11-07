"use client";

import { useEffect, useState, useRef } from "react";
import { ShieldCheck, KeyRound, CopySlash, SlidersHorizontal, ScrollText } from "lucide-react";

const safeguards = [
  {
    icon: ShieldCheck,
    title: "Policy-First Determinism",
    subtitle: "Zero LLM hallucinations on rules",
    description: "Eligibility, return windows, damage claims, and refund amounts are evaluated by strict code. The AI model never decides policy or alters amounts.",
  },
  {
    icon: KeyRound,
    title: "Server-Side Scope Injection",
    subtitle: "Hard identity boundaries",
    description: "The buyer identity, allowed order IDs, and tenant boundaries are injected server-side. The agent cannot query or touch another customer's data.",
  },
  {
    icon: CopySlash,
    title: "Duplicate & Race Condition Blocking",
    subtitle: "Idempotent resolution keys",
    description: "Each complaint item acquires an idempotent lock. Concurrent or repeated claims on the same order item are blocked automatically.",
  },
  {
    icon: SlidersHorizontal,
    title: "Configurable Approval Gates",
    subtitle: "Seller retains full authority",
    description: "Claims above your autonomous refund ceiling or flagged with ambiguous evidence require one-click merchant approval in your dashboard.",
  },
  {
    icon: ScrollText,
    title: "Hash-Chained Audit Trail",
    subtitle: "Verifiable record of every step",
    description: "Every tool call, carrier scan timestamp, policy evaluation branch, and issued action is immutably logged with SHA-256 hash chaining.",
  },
];

const architecturalGuarantees = [
  "Deterministic Rule Evaluation",
  "Zero LLM Policy Authority",
  "Idempotent Action Execution",
  "Scoped Data Access",
  "Immutable Audit Trail",
];

export function SecuritySection() {
  const [isVisible, setIsVisible] = useState(false);
  const [activeSafeguard, setActiveSafeguard] = useState(0);
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
    <section id="security" ref={sectionRef} className="relative py-24 lg:py-32 overflow-hidden border-t border-foreground/10">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header */}
        <div className="mb-16">
          <span
            className={`inline-flex items-center gap-4 text-sm font-mono text-muted-foreground mb-6 transition-all duration-700 ${
              isVisible ? "opacity-100" : "opacity-0"
            }`}
          >
            <span className="w-12 h-px bg-foreground/20" />
            Trust &amp; Safeguards
          </span>

          <h2
            className={`text-5xl md:text-6xl lg:text-[100px] font-display tracking-tight leading-[0.92] mb-6 transition-all duration-1000 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            Autonomous,
            <br />
            <span className="text-muted-foreground">never unconstrained.</span>
          </h2>

          <p
            className={`text-lg lg:text-xl text-muted-foreground leading-relaxed max-w-2xl transition-all duration-1000 delay-100 ${
              isVisible ? "opacity-100" : "opacity-0"
            }`}
          >
            Autonomous execution without safety boundaries is a liability. SellerResolve pairs LLM conversational reasoning with deterministic guardrails.
          </p>
        </div>

        {/* Safeguards Grid */}
        <div className="grid lg:grid-cols-12 gap-8 items-start">
          {/* Visual Showcase Card */}
          <div
            className={`lg:col-span-6 relative p-8 lg:p-12 border border-foreground/10 bg-foreground/[0.02] rounded-sm overflow-hidden transition-all duration-700 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            <div className="mb-8">
              <img
                src="/visuals/policy-shield.svg"
                alt=""
                aria-hidden="true"
                className="w-full h-auto max-h-[260px] object-contain object-left mb-6"
              />
              <span className="font-mono text-xs text-muted-foreground uppercase tracking-wider block mb-2">
                Defense in depth
              </span>
              <h3 className="text-2xl font-display text-foreground mb-2">
                {safeguards[activeSafeguard].title}
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {safeguards[activeSafeguard].description}
              </p>
            </div>

            {/* Architectural Guarantees */}
            <div className="pt-6 border-t border-foreground/10 flex flex-wrap gap-2">
              {architecturalGuarantees.map((item) => (
                <span
                  key={item}
                  className="px-2.5 py-1 border border-foreground/10 bg-foreground/[0.02] text-xs font-mono text-muted-foreground rounded-sm"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>

          {/* Interactive Stack */}
          <div className="lg:col-span-6 flex flex-col gap-3">
            {safeguards.map((item, index) => {
              const Icon = item.icon;
              const isActive = activeSafeguard === index;
              return (
                <button
                  key={item.title}
                  type="button"
                  onClick={() => setActiveSafeguard(index)}
                  onMouseEnter={() => setActiveSafeguard(index)}
                  className={`text-left p-5 border rounded-sm transition-all duration-200 cursor-pointer ${
                    isActive
                      ? "border-foreground/30 bg-foreground/[0.04]"
                      : "border-foreground/10 hover:border-foreground/20"
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div
                      className={`shrink-0 w-9 h-9 rounded-sm flex items-center justify-center border transition-colors ${
                        isActive
                          ? "border-foreground bg-foreground text-background"
                          : "border-foreground/20 text-muted-foreground"
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="font-medium text-sm text-foreground mb-0.5">{item.title}</h4>
                      <p className="text-xs text-muted-foreground">{item.subtitle}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
