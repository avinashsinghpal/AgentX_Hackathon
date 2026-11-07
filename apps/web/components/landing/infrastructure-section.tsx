"use client";

import { useEffect, useState, useRef } from "react";

const operationPillars = [
  {
    name: "Multi-Warehouse Origin",
    status: "Routing",
    detail: "Origin-to-destination zone calculation across distributed hubs.",
  },
  {
    name: "PIN Code Validation",
    status: "Verification",
    detail: "Coverage checks against carrier serviceable lists across India.",
  },
  {
    name: "Payment Reconciliation",
    status: "Safety check",
    detail: "Pre-act check verifies gateway settlement status before refunds.",
  },
  {
    name: "Carrier Delay Tracking",
    status: "Proactive",
    detail: "Background jobs flag stalled scans before the buyer has to complain.",
  },
];

export function InfrastructureSection() {
  const [isVisible, setIsVisible] = useState(false);
  const [activePillar, setActivePillar] = useState(0);
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

  useEffect(() => {
    const interval = setInterval(() => {
      setActivePillar((prev) => (prev + 1) % operationPillars.length);
    }, 3500);
    return () => clearInterval(interval);
  }, []);

  return (
    <section id="operations" ref={sectionRef} className="relative py-24 lg:py-32 overflow-hidden">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header */}
        <div className="mb-16">
          <span
            className={`inline-flex items-center gap-4 text-sm font-mono text-muted-foreground mb-8 transition-all duration-700 ${
              isVisible ? "opacity-100" : "opacity-0"
            }`}
          >
            <span className="w-12 h-px bg-foreground/20" />
            Operational Architecture
          </span>

          <div className="grid lg:grid-cols-[auto_1fr] gap-8 lg:gap-16 items-center">
            {/* Visual illustration */}
            <div
              className={`w-48 lg:w-72 xl:w-80 shrink-0 transition-all duration-1000 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
              }`}
            >
              <img
                src="/visuals/fulfillment-map.svg"
                alt=""
                className="w-full h-full object-contain object-center"
              />
            </div>

            {/* Title & description */}
            <div className="flex flex-col justify-center">
              <h2
                className={`text-5xl md:text-6xl lg:text-[100px] font-display tracking-tight leading-[0.92] transition-all duration-1000 ${
                  isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
                }`}
              >
                Built for how
                <br />
                <span className="text-muted-foreground">Indian sellers ship.</span>
              </h2>

              <p
                className={`mt-6 text-lg lg:text-xl text-muted-foreground leading-relaxed max-w-xl transition-all duration-1000 delay-100 ${
                  isVisible ? "opacity-100" : "opacity-0"
                }`}
              >
                Small brands balance multiple courier partners, regional hubs, and COD settlements.
                SellerResolve embeds these operational constraints directly into policy decisions.
              </p>
            </div>
          </div>
        </div>

        {/* Operational mechanics cards (no fabricated stats) */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div
            className={`p-8 border border-foreground/10 bg-foreground/[0.02] rounded-sm transition-all duration-700 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground block mb-3">
              Logistics
            </span>
            <h3 className="text-2xl font-display mb-3">Multi-Warehouse Routing</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Considers dispatch origin, transit zones (Intracity, Regional, National, Remote), and carrier partner SLAs when evaluating delivery timelines.
            </p>
          </div>

          <div
            className={`p-8 border border-foreground/10 bg-foreground/[0.02] rounded-sm transition-all duration-700 delay-100 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground block mb-3">
              Payments
            </span>
            <h3 className="text-2xl font-display mb-3">COD &amp; Prepaid Safeguards</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Enforces distinct flows for Cash on Delivery versus prepaid orders. Never issues a refund on an unverified or disputed settlement.
            </p>
          </div>

          <div
            className={`p-8 border border-foreground/10 bg-foreground/[0.02] rounded-sm transition-all duration-700 delay-200 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground block mb-3">
              Proactive
            </span>
            <h3 className="text-2xl font-display mb-3">Background Delay Detection</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Scheduled background workers poll carrier webhooks and checkpoints. If a parcel is delayed past policy tolerance, the agent initiates proactive customer outreach.
            </p>
          </div>
        </div>

        {/* Operational Pillars Strip */}
        <div
          className={`mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 transition-all duration-1000 delay-300 ${
            isVisible ? "opacity-100" : "opacity-0"
          }`}
        >
          {operationPillars.map((pillar, index) => (
            <div
              key={pillar.name}
              className={`p-5 border transition-all duration-300 cursor-default rounded-sm ${
                activePillar === index
                  ? "border-foreground/30 bg-foreground/[0.04]"
                  : "border-foreground/10"
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span
                  className={`w-2 h-2 rounded-full transition-colors ${
                    activePillar === index ? "bg-[#eca8d6]" : "bg-foreground/20"
                  }`}
                />
                <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider">
                  {pillar.status}
                </span>
              </div>
              <span className="font-medium text-sm block mb-1">{pillar.name}</span>
              <span className="text-xs text-muted-foreground leading-normal block">
                {pillar.detail}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
