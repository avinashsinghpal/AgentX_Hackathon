"use client";

import React, { useEffect, useState, useTransition } from "react";
import {
  FileCode,
  CheckCircle2,
  AlertTriangle,
  History,
  Save,
  RefreshCw,
  Code2,
  Sliders,
  ShieldCheck,
  Check,
} from "lucide-react";
import { toast } from "sonner";

interface PolicyHistoryItem {
  id: string;
  version: number;
  is_active: boolean;
  created_at: string;
  activated_at: string | null;
}

export default function SellerPoliciesPage() {
  const [activeVersion, setActiveVersion] = useState<number>(1);
  const [activeCreatedAt, setActiveCreatedAt] = useState<string>("");
  const [history, setHistory] = useState<PolicyHistoryItem[]>([]);
  const [activeTab, setActiveTab] = useState<"form" | "yaml">("form");

  // Form states
  const [returnDays, setReturnDays] = useState(7);
  const [returnShippingBearer, setReturnShippingBearer] = useState<"seller" | "buyer">("seller");
  const [autoGenLabel, setAutoGenLabel] = useState(true);

  const [refundCeiling, setRefundCeiling] = useState(2000);
  const [instantRefundUnder, setInstantRefundUnder] = useState(500);

  const [delayTriggerDays, setDelayTriggerDays] = useState(3);
  const [delayCompPerDay, setDelayCompPerDay] = useState(50);
  const [maxDelayComp, setMaxDelayComp] = useState(250);

  const [requirePhoto, setRequirePhoto] = useState(true);
  const [maxDamageUnder, setMaxDamageUnder] = useState(1500);

  const [maxClaimsPerBuyer, setMaxClaimsPerBuyer] = useState(2);
  const [blockSuspiciousAddresses, setBlockSuspiciousAddresses] = useState(true);

  // YAML state
  const [yamlContent, setYamlContent] = useState("");
  const [yamlValidation, setYamlValidation] = useState<{
    valid: boolean;
    error: string | null;
  }>({ valid: true, error: null });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [, startTransition] = useTransition();

  // Helper to compile form state to YAML string
  const generateYamlFromForm = () => {
    return `# SellerResolve Deterministic Resolution Policy
# Version auto-incremented upon publishing
returns:
  window_days: ${returnDays}
  require_original_packaging: true
  eligible_categories:
    - apparel
    - electronics
    - footwear
    - accessories
  non_returnable_categories:
    - perishable
    - intimate
    - customized
  return_shipping_paid_by: "${returnShippingBearer}"
  auto_generate_shipping_label: ${autoGenLabel}

refunds:
  auto_approve_max_amount: ${refundCeiling}
  instant_refund_without_return_threshold: ${instantRefundUnder}
  restocking_fee_percentage: 0
  processing_sla_days: 2

delays:
  delay_threshold_days: ${delayTriggerDays}
  compensation_per_day_late: ${delayCompPerDay}
  max_delay_compensation: ${maxDelayComp}

damage_claims:
  photo_evidence_required: ${requirePhoto}
  auto_replacement_under_amount: ${maxDamageUnder}
  require_warehouse_inspection_above: 5000

fraud_checks:
  max_claims_per_buyer_90_days: ${maxClaimsPerBuyer}
  require_manual_review_for_high_value: true
  high_value_order_threshold: 5000
  block_suspicious_addresses: ${blockSuspiciousAddresses}
`;
  };

  const fetchActivePolicyAndHistory = async () => {
    try {
      setLoading(true);
      const [activeRes, historyRes] = await Promise.all([
        fetch("/api/v1/seller/policies/active"),
        fetch("/api/v1/seller/policies/history"),
      ]);

      if (activeRes.ok) {
        const activeData = await activeRes.json();
        setActiveVersion(activeData.version);
        setActiveCreatedAt(activeData.activated_at || activeData.created_at);
        setYamlContent(activeData.policy_yaml);

        // Parse into form if available
        if (activeData.parsed_rules) {
          const r = activeData.parsed_rules;
          if (r.returns) {
            setReturnDays(r.returns.window_days ?? 7);
            setReturnShippingBearer(r.returns.return_shipping_paid_by ?? "seller");
            setAutoGenLabel(r.returns.auto_generate_shipping_label ?? true);
          }
          if (r.refunds) {
            setRefundCeiling(r.refunds.auto_approve_max_amount ?? 2000);
            setInstantRefundUnder(r.refunds.instant_refund_without_return_threshold ?? 500);
          }
          if (r.delays) {
            setDelayTriggerDays(r.delays.delay_threshold_days ?? 3);
            setDelayCompPerDay(r.delays.compensation_per_day_late ?? 50);
            setMaxDelayComp(r.delays.max_delay_compensation ?? 250);
          }
          if (r.damage_claims) {
            setRequirePhoto(r.damage_claims.photo_evidence_required ?? true);
            setMaxDamageUnder(r.damage_claims.auto_replacement_under_amount ?? 1500);
          }
          if (r.fraud_checks) {
            setMaxClaimsPerBuyer(r.fraud_checks.max_claims_per_buyer_90_days ?? 2);
            setBlockSuspiciousAddresses(r.fraud_checks.block_suspicious_addresses ?? true);
          }
        }
      }

      if (historyRes.ok) {
        const historyData = await historyRes.json();
        setHistory(historyData);
      }
    } catch {
      toast.error("Failed to load policy configuration");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivePolicyAndHistory();
  }, []);

  // Validate YAML against backend whenever it changes in yaml mode
  const validateYaml = async (yamlText: string) => {
    try {
      const res = await fetch("/api/v1/seller/policies/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ policy_yaml: yamlText }),
      });
      const data = await res.json();
      setYamlValidation({
        valid: data.valid,
        error: data.error || null,
      });
    } catch {
      setYamlValidation({ valid: false, error: "Validation request failed" });
    }
  };

  const handleTabChange = (tab: "form" | "yaml") => {
    if (tab === "yaml" && activeTab === "form") {
      const generated = generateYamlFromForm();
      setYamlContent(generated);
      validateYaml(generated);
    }
    setActiveTab(tab);
  };

  const handleYamlChange = (val: string) => {
    setYamlContent(val);
    startTransition(() => {
      validateYaml(val);
    });
  };

  const handleSaveAndPublish = async () => {
    const payloadYaml = activeTab === "form" ? generateYamlFromForm() : yamlContent;

    try {
      setSaving(true);
      const res = await fetch("/api/v1/seller/policies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ policy_yaml: payloadYaml }),
      });

      if (res.ok) {
        const data = await res.json();
        toast.success(`Published Policy Version v${data.version} successfully`);
        fetchActivePolicyAndHistory();
      } else {
        const err = await res.json();
        toast.error(err.error?.message || "Failed to publish policy");
      }
    } catch {
      toast.error("Network error publishing policy");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-[11px] font-mono uppercase text-muted-foreground tracking-wider">
              Deterministic Decision Engine
            </span>
          </div>
          <h1 className="font-display text-3xl md:text-4xl tracking-tight text-foreground">
            Policy Manager
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchActivePolicyAndHistory}
            disabled={loading}
            className="h-10 px-4 rounded-full border border-border text-xs font-mono text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Reload</span>
          </button>
          <button
            type="button"
            onClick={handleSaveAndPublish}
            disabled={saving || (activeTab === "yaml" && !yamlValidation.valid)}
            className="h-10 px-6 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity flex items-center gap-2 disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{saving ? "Publishing..." : "Save & Publish"}</span>
          </button>
        </div>
      </div>

      {/* Active Version Info Banner */}
      <div className="p-4 rounded-md border border-border bg-card/40 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-sm border border-border bg-foreground/[0.02] flex items-center justify-center">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-medium text-foreground">
                Active Enforcing Policy
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                v{activeVersion}
              </span>
            </div>
            <p className="text-xs font-mono text-muted-foreground">
              Last updated: {activeCreatedAt ? new Date(activeCreatedAt).toLocaleString() : "Initial baseline"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 border border-border rounded-full p-1 bg-background">
          <button
            type="button"
            onClick={() => handleTabChange("form")}
            className={`px-3 py-1 rounded-full text-xs font-mono flex items-center gap-1.5 transition-colors ${
              activeTab === "form"
                ? "bg-foreground text-background font-medium"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Visual Form</span>
          </button>
          <button
            type="button"
            onClick={() => handleTabChange("yaml")}
            className={`px-3 py-1 rounded-full text-xs font-mono flex items-center gap-1.5 transition-colors ${
              activeTab === "yaml"
                ? "bg-foreground text-background font-medium"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Code2 className="w-3.5 h-3.5" />
            <span>Raw YAML</span>
          </button>
        </div>
      </div>

      {/* Main Policy Editor Section */}
      {activeTab === "form" ? (
        <div className="space-y-6">
          {/* Returns & Exchanges */}
          <div className="p-6 rounded-md border border-border bg-card/20 space-y-4">
            <div className="border-b border-border pb-3">
              <h2 className="font-display text-xl tracking-tight text-foreground">
                Return Eligibility & Shipping
              </h2>
              <p className="text-xs font-mono text-muted-foreground">
                Parameters applied autonomously to customer return and replacement requests.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
              <div>
                <label className="text-xs font-mono uppercase text-muted-foreground block mb-2">
                  Return Window (Days)
                </label>
                <input
                  type="number"
                  min={1}
                  max={90}
                  value={returnDays}
                  onChange={(e) => setReturnDays(Number(e.target.value))}
                  className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
                />
                <span className="text-[11px] text-muted-foreground mt-1.5 block">
                  Eligible timeframe from delivery date.
                </span>
              </div>

              <div>
                <label className="text-xs font-mono uppercase text-muted-foreground block mb-2">
                  Return Shipping Fee
                </label>
                <select
                  value={returnShippingBearer}
                  onChange={(e) => setReturnShippingBearer(e.target.value as "seller" | "buyer")}
                  className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
                >
                  <option value="seller">Seller Borne (Free for Customer)</option>
                  <option value="buyer">Deducted from Customer Refund</option>
                </select>
                <span className="text-[11px] text-muted-foreground mt-1.5 block">
                  Designates prepaid label billing liability.
                </span>
              </div>

              <div className="flex flex-col justify-center pt-2">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoGenLabel}
                    onChange={(e) => setAutoGenLabel(e.target.checked)}
                    className="rounded border-border text-foreground focus:ring-0"
                  />
                  <span className="text-xs font-mono text-foreground">
                    Auto-Generate Reverse Pickup Label
                  </span>
                </label>
                <span className="text-[11px] text-muted-foreground mt-1.5 block pl-7">
                  Generates reverse AWB tracking instantly upon claim approval.
                </span>
              </div>
            </div>
          </div>

          {/* Refund Limits & Escalation Ceiling */}
          <div className="p-6 rounded-md border border-border bg-card/20 space-y-4">
            <div className="border-b border-border pb-3">
              <h2 className="font-display text-xl tracking-tight text-foreground">
                Refund Ceilings & Escalation Thresholds
              </h2>
              <p className="text-xs font-mono text-muted-foreground">
                Guardrails ensuring AI agents cannot execute payouts exceeding your strict limits.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
              <div>
                <label className="text-xs font-mono uppercase text-muted-foreground block mb-2">
                  Autonomous Refund Ceiling (INR)
                </label>
                <input
                  type="number"
                  min={0}
                  step={100}
                  value={refundCeiling}
                  onChange={(e) => setRefundCeiling(Number(e.target.value))}
                  className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
                />
                <span className="text-[11px] text-muted-foreground mt-1.5 block">
                  Orders exceeding this amount automatically halt and request your 1-click approval.
                </span>
              </div>

              <div>
                <label className="text-xs font-mono uppercase text-muted-foreground block mb-2">
                  Instant Refund Without Return (INR)
                </label>
                <input
                  type="number"
                  min={0}
                  step={50}
                  value={instantRefundUnder}
                  onChange={(e) => setInstantRefundUnder(Number(e.target.value))}
                  className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
                />
                <span className="text-[11px] text-muted-foreground mt-1.5 block">
                  Items below this amount are refunded instantly without requiring return transit.
                </span>
              </div>
            </div>
          </div>

          {/* Transit Delays & Compensation */}
          <div className="p-6 rounded-md border border-border bg-card/20 space-y-4">
            <div className="border-b border-border pb-3">
              <h2 className="font-display text-xl tracking-tight text-foreground">
                Shipping Delays & Proactive Remedies
              </h2>
              <p className="text-xs font-mono text-muted-foreground">
                Rules executed by background monitor when shipments exceed estimated delivery dates.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
              <div>
                <label className="text-xs font-mono uppercase text-muted-foreground block mb-2">
                  Delay Trigger (Days Late)
                </label>
                <input
                  type="number"
                  min={1}
                  value={delayTriggerDays}
                  onChange={(e) => setDelayTriggerDays(Number(e.target.value))}
                  className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
                />
                <span className="text-[11px] text-muted-foreground mt-1.5 block">
                  Days past EDD before proactive inquiry triggers.
                </span>
              </div>

              <div>
                <label className="text-xs font-mono uppercase text-muted-foreground block mb-2">
                  Compensation Per Day (INR)
                </label>
                <input
                  type="number"
                  min={0}
                  value={delayCompPerDay}
                  onChange={(e) => setDelayCompPerDay(Number(e.target.value))}
                  className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
                />
                <span className="text-[11px] text-muted-foreground mt-1.5 block">
                  Store wallet credit per overdue business day.
                </span>
              </div>

              <div>
                <label className="text-xs font-mono uppercase text-muted-foreground block mb-2">
                  Max Compensation Cap (INR)
                </label>
                <input
                  type="number"
                  min={0}
                  value={maxDelayComp}
                  onChange={(e) => setMaxDelayComp(Number(e.target.value))}
                  className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
                />
                <span className="text-[11px] text-muted-foreground mt-1.5 block">
                  Upper ceiling for delay credit credits.
                </span>
              </div>
            </div>
          </div>

          {/* Damage Claims & Fraud Checks */}
          <div className="p-6 rounded-md border border-border bg-card/20 space-y-4">
            <div className="border-b border-border pb-3">
              <h2 className="font-display text-xl tracking-tight text-foreground">
                Damage Claims & Fraud Detection
              </h2>
              <p className="text-xs font-mono text-muted-foreground">
                Verification requirements for transit defect allegations and buyer velocity checks.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
              <div className="space-y-4">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={requirePhoto}
                    onChange={(e) => setRequirePhoto(e.target.checked)}
                    className="rounded border-border text-foreground focus:ring-0"
                  />
                  <span className="text-xs font-mono text-foreground">
                    Enforce photo upload evidence for damage claims
                  </span>
                </label>

                <div>
                  <label className="text-xs font-mono uppercase text-muted-foreground block mb-2">
                    Auto-Replacement Max Amount (INR)
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={maxDamageUnder}
                    onChange={(e) => setMaxDamageUnder(Number(e.target.value))}
                    className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
                  />
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-xs font-mono uppercase text-muted-foreground block mb-2">
                    Max Claims per Buyer in 90 Days
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={maxClaimsPerBuyer}
                    onChange={(e) => setMaxClaimsPerBuyer(Number(e.target.value))}
                    className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
                  />
                  <span className="text-[11px] text-muted-foreground mt-1.5 block">
                    Velocity check triggering escalation if exceeded.
                  </span>
                </div>

                <label className="flex items-center gap-3 cursor-pointer pt-2">
                  <input
                    type="checkbox"
                    checked={blockSuspiciousAddresses}
                    onChange={(e) => setBlockSuspiciousAddresses(e.target.checked)}
                    className="rounded border-border text-foreground focus:ring-0"
                  />
                  <span className="text-xs font-mono text-foreground">
                    Block high-risk PIN codes and unverified addresses
                  </span>
                </label>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Validation Feedback Bar */}
          <div
            className={`p-3 rounded-md border flex items-center justify-between text-xs font-mono ${
              yamlValidation.valid
                ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-300"
                : "border-destructive/30 bg-destructive/5 text-destructive"
            }`}
          >
            <div className="flex items-center gap-2">
              {yamlValidation.valid ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>YAML is syntactically valid and complies with Pydantic v2 PolicySchema.</span>
                </>
              ) : (
                <>
                  <AlertTriangle className="w-4 h-4 text-destructive" />
                  <span>Validation Error: {yamlValidation.error}</span>
                </>
              )}
            </div>
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Real-Time AST Validation
            </span>
          </div>

          {/* Raw Textarea */}
          <div className="rounded-md border border-border bg-background p-4">
            <textarea
              value={yamlContent}
              onChange={(e) => handleYamlChange(e.target.value)}
              rows={24}
              className="w-full bg-transparent font-mono text-xs text-foreground focus:outline-none resize-none leading-relaxed"
              spellCheck={false}
            />
          </div>
        </div>
      )}

      {/* Version History Table */}
      <div className="space-y-4 pt-6 border-t border-border">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-muted-foreground" />
          <h2 className="font-display text-xl tracking-tight text-foreground">
            Policy Version History
          </h2>
        </div>

        {history.length === 0 ? (
          <p className="text-xs font-mono text-muted-foreground">No historical versions on record.</p>
        ) : (
          <div className="border border-border rounded-md overflow-hidden bg-card/30">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-foreground/[0.02] border-b border-border text-muted-foreground uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="p-3.5">Version</th>
                  <th className="p-3.5">Created At</th>
                  <th className="p-3.5">Activated At</th>
                  <th className="p-3.5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {history.map((h) => (
                  <tr key={h.id} className="hover:bg-foreground/[0.02] transition-colors">
                    <td className="p-3.5 font-medium text-foreground">v{h.version}</td>
                    <td className="p-3.5 text-muted-foreground">
                      {new Date(h.created_at).toLocaleString()}
                    </td>
                    <td className="p-3.5 text-muted-foreground">
                      {h.activated_at ? new Date(h.activated_at).toLocaleString() : "-"}
                    </td>
                    <td className="p-3.5">
                      {h.is_active ? (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] border border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                          <span className="w-1 h-1 rounded-full bg-emerald-400" />
                          <span>Active</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] border border-border text-muted-foreground">
                          Archived
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
