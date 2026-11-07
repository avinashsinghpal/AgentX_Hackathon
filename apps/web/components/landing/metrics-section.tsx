"use client";

import { useEffect, useState, useRef } from "react";

const decisionPaths = [
  {
    badge: "Autonomous Execution",
    badgeColor: "border-emerald-500/30 text-emerald-400 bg-emerald-500/10",
    title: "Execute Within Limits",
    criteria: "Low risk • Value under seller ceiling • Clear proof",
    description:
      "When order records, carrier tracking, and photo validation unambiguously satisfy policy rules, the agent generates return labels or triggers refunds immediately without human delay.",
    actions: ["Issue return shipping label", "Approve instant replacement", "Dispatch carrier status update"],
  },
  {
    badge: "Needs Approval",
    badgeColor: "border-amber-500/30 text-amber-400 bg-amber-500/10",
    title: "Route for Seller Review",
    criteria: "High value • Edge cases • Ambiguous claims",
    description:
      "When claim amount exceeds the seller-configured autonomous threshold or damage evidence requires human judgment, the case is queued with pre-summarized facts for 1-click decision.",
    actions: ["One-click approve / reject in dashboard", "Adjust partial refund amount", "Request additional unboxing photo"],
  },
  {
    badge: "Policy Explanation",
    badgeColor: "border-rose-500/30 text-rose-400 bg-rose-500/10",
    title: "Explain & De-escalate",
    criteria: "Policy ineligible • Expired window • Final sale",
    description:
      "When a request violates explicit seller terms (such as hygiene exclusions or post-window claims), the agent provides an empathetic, transparent explanation citing the exact clause.",
    actions: ["Reference exact policy clause", "Prevent duplicate claim resubmissions", "Offer troubleshooting or warranty support"],
  },
];

export function MetricsSection() {
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
    <section ref={sectionRef} className="relative py-24 lg:py-32 overflow-hidden border-t border-foreground/10">
      <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header */}
        <div className="max-w-3xl mb-16">
          <span
            className={`inline-flex items-center gap-4 text-sm font-mono text-muted-foreground mb-6 transition-all duration-700 ${
              isVisible ? "opacity-100" : "opacity-0"
            }`}
          >
            <span className="w-12 h-px bg-foreground/20" />
            Decision Taxonomy
          </span>

          <h2
            className={`text-5xl md:text-6xl lg:text-[100px] font-display tracking-tight leading-[0.92] transition-all duration-1000 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            Three paths.
            <br />
            <span className="text-muted-foreground">Zero guesswork.</span>
          </h2>

          <p
            className={`mt-6 text-lg lg:text-xl text-muted-foreground leading-relaxed transition-all duration-1000 delay-100 ${
              isVisible ? "opacity-100" : "opacity-0"
            }`}
          >
            The language model never decides eligibility or spending limits. Every resolution
            is governed by your deterministic rules into three explicit outcomes.
          </p>
        </div>

        {/* Visual illustration */}
        <div
          className={`w-full mb-12 transition-all duration-1000 delay-200 ${
            isVisible ? "opacity-100" : "opacity-0"
          }`}
        >
          <img
            src="/visuals/decision-paths.svg"
            alt=""
            aria-hidden="true"
            className="w-full h-auto object-contain max-h-[440px] rounded-sm border border-foreground/10 bg-foreground/[0.01] p-2 sm:p-6"
          />
        </div>

        {/* 3 Decision Paths */}
        <div className="grid lg:grid-cols-3 gap-6">
          {decisionPaths.map((path, index) => (
            <div
              key={path.title}
              className={`bg-foreground/[0.02] border border-foreground/10 p-8 flex flex-col justify-between rounded-sm transition-all duration-700 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-12"
              }`}
              style={{ transitionDelay: `${(index + 1) * 120}ms` }}
            >
              <div>
                <div className="flex items-center justify-between gap-3 mb-6">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded border ${path.badgeColor}`}
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-current" />
                    {path.badge}
                  </span>
                </div>

                <h3 className="text-2xl font-display mb-2">{path.title}</h3>
                <span className="text-xs font-mono text-muted-foreground block mb-4">
                  {path.criteria}
                </span>

                <p className="text-sm text-muted-foreground leading-relaxed mb-6">
                  {path.description}
                </p>
              </div>

              <div className="pt-6 border-t border-foreground/10">
                <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground block mb-3">
                  Permitted outcomes
                </span>
                <ul className="space-y-2">
                  {path.actions.map((act) => (
                    <li key={act} className="text-xs font-mono text-foreground/80 flex items-start gap-2">
                      <span className="text-[#eca8d6] select-none">-</span>
                      <span>{act}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
