"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { Store, UserCheck, ArrowRight, ShieldCheck, FileCode } from "lucide-react";

const samplePolicyYaml = `version: 1
currency: INR

returns:
  window_days: 7
  non_returnable_categories:
    - innerwear
    - perishables

refunds:
  auto_approve_up_to: 500
  require_seller_approval_above: 500
  cod_refund_method: store_credit

delays:
  notify_after_days_late: 2
  allow_return_if_late_days_at_least: 3

damage_claims:
  require_photo: true
  report_within_days: 2

fraud_checks:
  max_refunds_per_buyer_per_30_days: 3
  require_seller_approval_if_exceeded: true`;

export function DevelopersSection() {
  const [activeTab, setActiveTab] = useState<"seller" | "buyer">("seller");
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
    <section id="roles" ref={sectionRef} className="relative py-24 lg:py-32 overflow-hidden border-t border-foreground/10">
      <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header */}
        <div
          className={`mb-16 transition-all duration-700 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
        >
          <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-6">
            <span className="w-8 h-px bg-foreground/30" />
            Roles &amp; Experience
          </span>
          <h2 className="text-5xl md:text-6xl lg:text-[100px] font-display tracking-tight leading-[0.92]">
            Two portals.
            <br />
            <span className="text-muted-foreground">One unified resolution engine.</span>
          </h2>
        </div>

        {/* Tab switchers */}
        <div className="flex items-center gap-2 mb-10 border-b border-foreground/10 pb-4">
          <button
            type="button"
            onClick={() => setActiveTab("seller")}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-mono transition-all ${
              activeTab === "seller"
                ? "bg-foreground text-background font-medium"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Store className="w-4 h-4" />
            For Sellers
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("buyer")}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-mono transition-all ${
              activeTab === "buyer"
                ? "bg-foreground text-background font-medium"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <UserCheck className="w-4 h-4" />
            For Buyers
          </button>
        </div>

        {/* Role Content Grid */}
        <div className="grid lg:grid-cols-12 gap-8 items-start">
          {/* Left panel: Role explanation */}
          <div className="lg:col-span-5 space-y-6">
            {activeTab === "seller" ? (
              <div className="space-y-6">
                <div>
                  <span className="text-xs font-mono uppercase tracking-wider text-[#eca8d6] block mb-2">
                    Merchant Command Center
                  </span>
                  <h3 className="text-3xl font-display mb-3">
                    Automate resolutions without giving up sovereignty.
                  </h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    Set up your business rules in minutes. Define exact refund limits, allowed return windows, and photo requirements. Review high-value cases with 1-click approvals.
                  </p>
                </div>

                <div className="space-y-3 pt-2">
                  <div className="p-4 border border-foreground/10 bg-foreground/[0.02] rounded-sm">
                    <span className="text-xs font-mono font-medium block mb-1">
                      4-Step Onboarding Wizard
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Connect mock store, configure operations &amp; PIN codes, define YAML policies, and activate.
                    </span>
                  </div>

                  <div className="p-4 border border-foreground/10 bg-foreground/[0.02] rounded-sm">
                    <span className="text-xs font-mono font-medium block mb-1">
                      1-Click Approval Queue
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Cases exceeding auto-approve limits wait for merchant decision with structured investigation summaries.
                    </span>
                  </div>

                  <div className="p-4 border border-foreground/10 bg-foreground/[0.02] rounded-sm">
                    <span className="text-xs font-mono font-medium block mb-1">
                      Tamper-Evident Audit Log
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Every tool invocation, carrier scan, and decision is signed and exportable to CSV.
                    </span>
                  </div>
                </div>

                <div className="pt-4">
                  <Link
                    href="/register/seller"
                    className="inline-flex items-center gap-2 h-12 px-6 rounded-full bg-foreground text-background font-medium text-sm hover:opacity-90 transition-opacity"
                  >
                    Open Seller Account
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                <div>
                  <span className="text-xs font-mono uppercase tracking-wider text-[#67e8f9] block mb-2">
                    Customer Experience
                  </span>
                  <h3 className="text-3xl font-display mb-3">
                    Resolution in minutes, not days of ticket ping-pong.
                  </h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    Select your merchant, pick your recent order, and describe the issue. Our policy-aware agent inspects the order, verifies eligibility, and resolves the issue directly.
                  </p>
                </div>

                <div className="space-y-3 pt-2">
                  <div className="p-4 border border-foreground/10 bg-foreground/[0.02] rounded-sm">
                    <span className="text-xs font-mono font-medium block mb-1">
                      Order-Scoped Interaction
                    </span>
                    <span className="text-xs text-muted-foreground">
                      No repeating order IDs or tracking numbers. Context is bound to your authenticated account.
                    </span>
                  </div>

                  <div className="p-4 border border-foreground/10 bg-foreground/[0.02] rounded-sm">
                    <span className="text-xs font-mono font-medium block mb-1">
                      Live Investigation Drawer
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Inspect every step in real-time as the agent queries carrier APIs and validates policy conditions.
                    </span>
                  </div>

                  <div className="p-4 border border-foreground/10 bg-foreground/[0.02] rounded-sm">
                    <span className="text-xs font-mono font-medium block mb-1">
                      Immediate Verified Outcome
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Receive instant return labels, replacement confirmations, or clear explanations based on merchant policy.
                    </span>
                  </div>
                </div>

                <div className="pt-4">
                  <Link
                    href="/register/buyer"
                    className="inline-flex items-center gap-2 h-12 px-6 rounded-full bg-foreground text-background font-medium text-sm hover:opacity-90 transition-opacity"
                  >
                    Resolve an Order Issue
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            )}
          </div>

          {/* Right panel: Live Policy Engine YAML Display */}
          <div className="lg:col-span-7">
            <div className="border border-foreground/15 rounded-sm bg-black/90 overflow-hidden shadow-2xl">
              <div className="flex items-center justify-between px-4 py-3 border-b border-foreground/10 bg-foreground/[0.03]">
                <div className="flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-muted-foreground" />
                  <span className="text-xs font-mono text-muted-foreground">seller-policy.yaml</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span className="text-[11px] font-mono text-emerald-400">Strict Schema v1</span>
                </div>
              </div>

              <div className="p-5 font-mono text-xs overflow-x-auto text-foreground/90 leading-relaxed max-h-[460px] scrollbar-thin">
                <pre className="text-white/80">{samplePolicyYaml}</pre>
              </div>

              <div className="px-4 py-3 border-t border-foreground/10 bg-foreground/[0.02] flex items-center justify-between text-[11px] font-mono text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  Evaluated deterministically by policy engine
                </span>
                <span>Pydantic v2 validated</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
