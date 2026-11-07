"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  CheckCircle2,
  Store,
  SlidersHorizontal,
  FileCode,
  ShieldCheck,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  Plus,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const DEFAULT_YAML = `version: 1
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

export default function OnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  // Step 2 State
  const [warehousePins, setWarehousePins] = useState(["560001", "110001"]);
  const [newPin, setNewPin] = useState("");
  const [codEnabled, setCodEnabled] = useState(true);
  const [supportEmail, setSupportEmail] = useState("support@artisanstore.in");

  // Step 3 State
  const [policyMode, setPolicyMode] = useState<"form" | "yaml">("form");
  const [policyYaml, setPolicyYaml] = useState(DEFAULT_YAML);
  const [returnDays, setReturnDays] = useState(7);
  const [refundCeiling, setRefundCeiling] = useState(500);
  const [requirePhoto, setRequirePhoto] = useState(true);
  const [yamlError, setYamlError] = useState<string | null>(null);

  const addWarehousePin = () => {
    if (newPin.trim() && !warehousePins.includes(newPin.trim())) {
      setWarehousePins([...warehousePins, newPin.trim()]);
      setNewPin("");
    }
  };

  const removeWarehousePin = (pin: string) => {
    if (warehousePins.length > 1) {
      setWarehousePins(warehousePins.filter((p) => p !== pin));
    }
  };

  const handleNextStep2 = () => {
    if (warehousePins.length === 0) {
      setFeedbackMsg("Please specify at least one warehouse dispatch PIN code.");
      return;
    }
    setFeedbackMsg(null);
    setCurrentStep(3);
  };

  const handleNextStep3 = () => {
    setFeedbackMsg(null);
    setCurrentStep(4);
  };

  const handleActivate = async () => {
    setIsSubmitting(true);
    setFeedbackMsg(null);
    try {
      // Transition seller to active
      setTimeout(() => {
        setIsSubmitting(false);
        router.push("/seller/dashboard");
      }, 800);
    } catch {
      setIsSubmitting(false);
      setFeedbackMsg("Activation failed. Please ensure operations and policies are configured.");
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8">
      {/* Wizard Header */}
      <div className="mb-10">
        <span className="text-xs font-mono uppercase tracking-widest text-muted-foreground block mb-2">
          Setup Wizard &bull; 4 Steps
        </span>
        <h1 className="text-4xl md:text-5xl font-display tracking-tight mb-3">
          Configure Your Resolution Engine
        </h1>
        <p className="text-sm text-muted-foreground">
          Complete the four onboarding steps below to calibrate store logistics, connect fulfillment channels, and declare your deterministic policies.
        </p>
      </div>

      {/* Step Indicators */}
      <div className="grid grid-cols-4 gap-2 mb-12 border-b border-border pb-6">
        {[
          { num: 1, label: "Store", icon: Store },
          { num: 2, label: "Operations", icon: SlidersHorizontal },
          { num: 3, label: "Policy", icon: FileCode },
          { num: 4, label: "Activate", icon: ShieldCheck },
        ].map((s) => {
          const isDone = currentStep > s.num;
          const isCurrent = currentStep === s.num;
          return (
            <div
              key={s.num}
              className={`flex items-center gap-2 p-2 rounded-sm text-xs font-mono transition-all ${
                isCurrent
                  ? "border border-foreground bg-foreground/[0.04] text-foreground font-medium"
                  : isDone
                  ? "text-emerald-400"
                  : "text-muted-foreground opacity-50"
              }`}
            >
              <span
                className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                  isDone
                    ? "bg-emerald-500/20 text-emerald-400"
                    : isCurrent
                    ? "bg-foreground text-background"
                    : "border border-border"
                }`}
              >
                {isDone ? <CheckCircle2 className="w-3.5 h-3.5" /> : s.num}
              </span>
              <span className="hidden sm:inline">{s.label}</span>
            </div>
          );
        })}
      </div>

      {feedbackMsg && (
        <div className="p-4 mb-6 border border-destructive/30 bg-destructive/10 text-xs font-mono text-destructive rounded-sm">
          {feedbackMsg}
        </div>
      )}

      {/* Step 1: Connect Store */}
      {currentStep === 1 && (
        <div className="space-y-6 p-8 border border-border bg-card/30 rounded-sm">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground block mb-1">
                Step 1
              </span>
              <h2 className="text-2xl font-display">Connect Store Channel</h2>
            </div>
            <span className="px-2.5 py-1 text-xs font-mono border border-emerald-500/30 text-emerald-400 bg-emerald-500/10 rounded">
              Ready
            </span>
          </div>

          <p className="text-sm text-muted-foreground leading-relaxed">
            SellerResolve includes a built-in commerce engine for rapid testing. Your demo storefront is initialized with mock product inventory and test shipments.
          </p>

          <div className="p-5 border border-border bg-foreground/[0.02] rounded-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-muted-foreground uppercase">Store Connector</span>
              <span className="text-xs font-mono text-foreground font-medium">Built-in Demo Commerce</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-muted-foreground uppercase">Integration Status</span>
              <span className="text-xs font-mono text-emerald-400 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Active &bull; Synced
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-muted-foreground uppercase">Default Currency</span>
              <span className="text-xs font-mono text-foreground">INR (&#8377;)</span>
            </div>
          </div>

          <div className="flex justify-end pt-4">
            <Button
              type="button"
              onClick={() => setCurrentStep(2)}
              className="rounded-full px-6 gap-2 bg-foreground text-background hover:opacity-90 font-mono text-xs"
            >
              Continue to Operations
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Configure Operations */}
      {currentStep === 2 && (
        <div className="space-y-6 p-8 border border-border bg-card/30 rounded-sm">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground block mb-1">
                Step 2
              </span>
              <h2 className="text-2xl font-display">Logistics &amp; Operations</h2>
            </div>
            <span className="text-xs font-mono text-muted-foreground">Fulfillment</span>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-mono uppercase text-muted-foreground mb-2">
                Warehouse Dispatch PIN Codes
              </label>
              <div className="flex gap-2 mb-3">
                <input
                  type="text"
                  placeholder="e.g. 560001"
                  value={newPin}
                  onChange={(e) => setNewPin(e.target.value)}
                  className="w-40 h-10 px-3 bg-background border border-border rounded-sm text-xs font-mono focus:outline-none focus:border-foreground"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addWarehousePin}
                  className="rounded-sm font-mono text-xs gap-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add PIN
                </Button>
              </div>
              <div className="flex flex-wrap gap-2">
                {warehousePins.map((pin) => (
                  <span
                    key={pin}
                    className="inline-flex items-center gap-2 px-3 py-1 bg-foreground/[0.04] border border-border rounded text-xs font-mono"
                  >
                    {pin}
                    <button
                      type="button"
                      onClick={() => removeWarehousePin(pin)}
                      className="text-muted-foreground hover:text-destructive"
                      aria-label={`Remove PIN ${pin}`}
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-mono uppercase text-muted-foreground mb-1.5">
                Support Email for Escalations
              </label>
              <input
                type="email"
                value={supportEmail}
                onChange={(e) => setSupportEmail(e.target.value)}
                className="w-full h-10 px-3 bg-background border border-border rounded-sm text-xs font-mono focus:outline-none focus:border-foreground"
              />
            </div>

            <div className="pt-2">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={codEnabled}
                  onChange={(e) => setCodEnabled(e.target.checked)}
                  className="rounded border-border text-foreground focus:ring-0"
                />
                <span className="text-xs font-mono">
                  Enable Cash on Delivery (COD) specific settlement workflows
                </span>
              </label>
            </div>
          </div>

          <div className="flex justify-between pt-4 border-t border-border">
            <Button
              type="button"
              variant="outline"
              onClick={() => setCurrentStep(1)}
              className="rounded-full px-5 font-mono text-xs gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </Button>
            <Button
              type="button"
              onClick={handleNextStep2}
              className="rounded-full px-6 gap-2 bg-foreground text-background hover:opacity-90 font-mono text-xs"
            >
              Continue to Policies
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: Define Policies */}
      {currentStep === 3 && (
        <div className="space-y-6 p-8 border border-border bg-card/30 rounded-sm">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground block mb-1">
                Step 3
              </span>
              <h2 className="text-2xl font-display">Define Resolution Policies</h2>
            </div>
            <div className="flex gap-1 p-1 border border-border rounded bg-foreground/[0.02]">
              <button
                type="button"
                onClick={() => setPolicyMode("form")}
                className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
                  policyMode === "form" ? "bg-foreground text-background font-medium" : "text-muted-foreground"
                }`}
              >
                Form Editor
              </button>
              <button
                type="button"
                onClick={() => setPolicyMode("yaml")}
                className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
                  policyMode === "yaml" ? "bg-foreground text-background font-medium" : "text-muted-foreground"
                }`}
              >
                Raw YAML
              </button>
            </div>
          </div>

          {policyMode === "form" ? (
            <div className="space-y-4">
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono uppercase text-muted-foreground mb-1.5">
                    Return Window (Days)
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={30}
                    value={returnDays}
                    onChange={(e) => setReturnDays(Number(e.target.value))}
                    className="w-full h-10 px-3 bg-background border border-border rounded-sm text-xs font-mono focus:outline-none focus:border-foreground"
                  />
                  <span className="text-[11px] text-muted-foreground mt-1 block">
                    Days after confirmed delivery to request a return.
                  </span>
                </div>

                <div>
                  <label className="block text-xs font-mono uppercase text-muted-foreground mb-1.5">
                    Auto-Approve Refund Ceiling (&#8377;)
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={10000}
                    value={refundCeiling}
                    onChange={(e) => setRefundCeiling(Number(e.target.value))}
                    className="w-full h-10 px-3 bg-background border border-border rounded-sm text-xs font-mono focus:outline-none focus:border-foreground"
                  />
                  <span className="text-[11px] text-muted-foreground mt-1 block">
                    Higher amounts are automatically routed for your 1-click approval.
                  </span>
                </div>
              </div>

              <div className="pt-2">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={requirePhoto}
                    onChange={(e) => setRequirePhoto(e.target.checked)}
                    className="rounded border-border text-foreground focus:ring-0"
                  />
                  <span className="text-xs font-mono">
                    Require unboxing / damage photo evidence for broken item claims
                  </span>
                </label>
              </div>
            </div>
          ) : (
            <div>
              <textarea
                value={policyYaml}
                onChange={(e) => {
                  setPolicyYaml(e.target.value);
                  setYamlError(null);
                }}
                rows={14}
                className="w-full p-4 bg-black border border-border rounded-sm font-mono text-xs leading-relaxed focus:outline-none focus:border-foreground"
              />
              {yamlError && <span className="text-xs font-mono text-destructive block mt-1">{yamlError}</span>}
            </div>
          )}

          <div className="flex justify-between pt-4 border-t border-border">
            <Button
              type="button"
              variant="outline"
              onClick={() => setCurrentStep(2)}
              className="rounded-full px-5 font-mono text-xs gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </Button>
            <Button
              type="button"
              onClick={handleNextStep3}
              className="rounded-full px-6 gap-2 bg-foreground text-background hover:opacity-90 font-mono text-xs"
            >
              Review &amp; Summary
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 4: Review & Activate */}
      {currentStep === 4 && (
        <div className="space-y-6 p-8 border border-border bg-card/30 rounded-sm">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground block mb-1">
                Step 4
              </span>
              <h2 className="text-2xl font-display">Review &amp; Activate Agent</h2>
            </div>
            <span className="text-xs font-mono text-emerald-400">Ready to Launch</span>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div className="p-4 border border-border bg-foreground/[0.02] rounded-sm space-y-2">
              <span className="text-xs font-mono uppercase text-muted-foreground block">Logistics Settings</span>
              <div className="text-xs font-mono">
                <div>Warehouses: {warehousePins.join(", ")}</div>
                <div>Couriers: Delhivery, Bluedart, Shadowfax</div>
                <div>COD: {codEnabled ? "Enabled" : "Disabled"}</div>
              </div>
            </div>

            <div className="p-4 border border-border bg-foreground/[0.02] rounded-sm space-y-2">
              <span className="text-xs font-mono uppercase text-muted-foreground block">Policy Guardrails</span>
              <div className="text-xs font-mono">
                <div>Return Window: {returnDays} Days</div>
                <div>Autonomous Ceiling: &#8377;{refundCeiling}</div>
                <div>Photo Proof: {requirePhoto ? "Mandatory" : "Optional"}</div>
              </div>
            </div>
          </div>

          <div className="p-4 border border-amber-500/30 bg-amber-500/5 text-amber-200/90 text-xs font-mono rounded-sm">
            Upon activation, your resolution agent will autonomously evaluate incoming customer claims according to these strict rules. High-value exceptions will appear in your Approvals queue.
          </div>

          <div className="flex justify-between pt-4 border-t border-border">
            <Button
              type="button"
              variant="outline"
              onClick={() => setCurrentStep(3)}
              className="rounded-full px-5 font-mono text-xs gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </Button>
            <Button
              type="button"
              onClick={handleActivate}
              disabled={isSubmitting}
              className="rounded-full px-8 gap-2 bg-foreground text-background hover:opacity-90 font-mono text-xs"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Activating...
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  Activate Resolution Agent
                </>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

