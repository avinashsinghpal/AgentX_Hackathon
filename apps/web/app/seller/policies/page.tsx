"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Code2,
  FileCode,
  History,
  Lock,
  RefreshCw,
  Save,
  ShieldCheck,
  Sliders,
  Undo2,
  X,
} from "lucide-react";
import { toast } from "sonner";

import {
  PolicyApiError,
  createDefaultPolicyConfig,
  formatCategoryList,
  formatMinorUnits,
  formatMoney,
  formatPaise,
  getErrorMessage,
  parseCategoryList,
  policyRequest,
  shortHash,
  toInteger,
  type PolicyConfig,
  type PolicyDocumentResponse,
  type PolicyHistoryItem,
  type PolicyMonetaryMinor,
  type PolicyPreviewResponse,
  type PolicyPublishResponse,
  type PolicyYamlValidationResponse,
} from "@/lib/policy";

interface ReviewPreview {
  config: PolicyConfig;
  monetary: PolicyMonetaryMinor;
  yaml: string;
  warnings: string[];
  source: "structured" | "yaml";
}

function cloneConfig(config: PolicyConfig): PolicyConfig {
  return JSON.parse(JSON.stringify(config)) as PolicyConfig;
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "—";
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div>
      <label className="text-xs font-mono uppercase text-muted-foreground block mb-2">
        {label}
      </label>
      {children}
      {hint ? (
        <span className="text-[11px] text-muted-foreground mt-1.5 block">{hint}</span>
      ) : null}
    </div>
  );
}

function NumberInput({
  value,
  onChange,
  min = 0,
  max,
  step = 1,
  prefix,
}: {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  prefix?: string;
}) {
  return (
    <div className="relative">
      {prefix ? (
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-mono text-muted-foreground">
          {prefix}
        </span>
      ) : null}
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(toInteger(event.target.value, value))}
        className={`w-full h-10 ${
          prefix ? "pl-8" : "pl-3"
        } pr-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50`}
      />
    </div>
  );
}

function Toggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-3 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-0.5 rounded border-border text-foreground focus:ring-0"
      />
      <span>
        <span className="text-xs font-mono text-foreground block">{label}</span>
        {description ? (
          <span className="text-[11px] text-muted-foreground mt-1 block">{description}</span>
        ) : null}
      </span>
    </label>
  );
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <div className="p-6 rounded-md border border-border bg-card/20 space-y-4">
      <div className="border-b border-border pb-3">
        <h2 className="font-display text-xl tracking-tight text-foreground">{title}</h2>
        <p className="text-xs font-mono text-muted-foreground">{description}</p>
      </div>
      <div className="pt-2">{children}</div>
    </div>
  );
}

export default function SellerPoliciesPage() {
  const [active, setActive] = useState<PolicyDocumentResponse | null>(null);
  const [history, setHistory] = useState<PolicyHistoryItem[]>([]);
  const [config, setConfig] = useState<PolicyConfig | null>(null);
  const [baseline, setBaseline] = useState<PolicyConfig | null>(null);

  const [tab, setTab] = useState<"form" | "yaml">("form");
  const [yamlContent, setYamlContent] = useState("");
  const [yamlEdited, setYamlEdited] = useState(false);
  const [yamlConfig, setYamlConfig] = useState<PolicyConfig | null>(null);
  const [yamlValidation, setYamlValidation] = useState<{ valid: boolean; error: string | null }>(
    { valid: true, error: null },
  );

  const [eligibleText, setEligibleText] = useState("");
  const [nonReturnableText, setNonReturnableText] = useState("");

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [viewingVersion, setViewingVersion] = useState<number | null>(null);

  const [review, setReview] = useState<ReviewPreview | null>(null);
  const [showReview, setShowReview] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  const validationTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const applyDocument = useCallback((document: PolicyDocumentResponse) => {
    const next = document.config ?? createDefaultPolicyConfig(document.currency);
    setConfig(next);
    setBaseline(cloneConfig(next));
    setYamlContent(document.policy_yaml);
    setYamlEdited(false);
    setYamlConfig(null);
    setYamlValidation({ valid: true, error: null });
    setEligibleText(formatCategoryList(next.returns.eligible_categories));
    setNonReturnableText(formatCategoryList(next.returns.non_returnable_categories));
  }, []);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [activeDocument, historyItems] = await Promise.all([
        policyRequest<PolicyDocumentResponse>("/active"),
        policyRequest<PolicyHistoryItem[]>("/history"),
      ]);
      setActive(activeDocument);
      setHistory(historyItems);
      applyDocument(activeDocument);
      setViewingVersion(null);
      setReview(null);
      setShowReview(false);
      setTab("form");
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [applyDocument]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(
    () => () => {
      if (validationTimer.current) clearTimeout(validationTimer.current);
    },
    [],
  );

  const patchReturns = (patch: Partial<PolicyConfig["returns"]>) => {
    setConfig((current) =>
      current ? { ...current, returns: { ...current.returns, ...patch } } : current,
    );
    setYamlEdited(false);
    setReview(null);
  };

  const patchRefunds = (patch: Partial<PolicyConfig["refunds"]>) => {
    setConfig((current) =>
      current ? { ...current, refunds: { ...current.refunds, ...patch } } : current,
    );
    setYamlEdited(false);
    setReview(null);
  };

  const patchDelays = (patch: Partial<PolicyConfig["delays"]>) => {
    setConfig((current) =>
      current ? { ...current, delays: { ...current.delays, ...patch } } : current,
    );
    setYamlEdited(false);
    setReview(null);
  };

  const patchDamage = (patch: Partial<PolicyConfig["damage_claims"]>) => {
    setConfig((current) =>
      current
        ? { ...current, damage_claims: { ...current.damage_claims, ...patch } }
        : current,
    );
    setYamlEdited(false);
    setReview(null);
  };

  const patchFraud = (patch: Partial<PolicyConfig["fraud_checks"]>) => {
    setConfig((current) =>
      current
        ? { ...current, fraud_checks: { ...current.fraud_checks, ...patch } }
        : current,
    );
    setYamlEdited(false);
    setReview(null);
  };

  // The autonomous ceiling and the seller-approval ceiling are the same decision
  // boundary; the UI edits them together so they can never contradict.
  const setRefundCeiling = (value: number) =>
    patchRefunds({
      auto_approve_up_to: value,
      require_seller_approval_above: value,
    });

  const generatePreview = async (value: PolicyConfig) => {
    try {
      setBusy(true);
      const preview = await policyRequest<PolicyPreviewResponse>("/preview", {
        method: "POST",
        body: JSON.stringify({ config: value }),
      });
      setYamlContent(preview.policy_yaml);
      setYamlEdited(false);
      setYamlValidation({ valid: true, error: null });
      setYamlConfig(preview.config);
      return preview;
    } catch (error) {
      toast.error(getErrorMessage(error));
      return null;
    } finally {
      setBusy(false);
    }
  };

  const validateYamlText = useCallback(async (value: string) => {
    if (!value.trim()) {
      setYamlValidation({ valid: false, error: "Policy YAML cannot be empty." });
      return;
    }
    try {
      const result = await policyRequest<PolicyYamlValidationResponse>("/validate", {
        method: "POST",
        body: JSON.stringify({ policy_yaml: value }),
      });
      setYamlValidation({ valid: result.valid, error: result.error });
      setYamlConfig(result.valid ? result.config : null);
    } catch (error) {
      setYamlValidation({ valid: false, error: getErrorMessage(error) });
      setYamlConfig(null);
    }
  }, []);

  const handleYamlChange = (value: string) => {
    setYamlContent(value);
    setYamlEdited(true);
    setYamlConfig(null);
    setReview(null);
    if (validationTimer.current) clearTimeout(validationTimer.current);
    validationTimer.current = setTimeout(() => {
      void validateYamlText(value);
    }, 350);
  };

  const handleTabChange = async (nextTab: "form" | "yaml") => {
    if (nextTab === tab) return;

    if (nextTab === "form") {
      if (yamlEdited) {
        if (!yamlValidation.valid || !yamlConfig) {
          toast.error("Fix the YAML validation errors, or reload, before returning to the form.");
          return;
        }
        setConfig(yamlConfig);
        setEligibleText(formatCategoryList(yamlConfig.returns.eligible_categories));
        setNonReturnableText(
          formatCategoryList(yamlConfig.returns.non_returnable_categories),
        );
        toast.info("Form updated from your YAML edits.");
      }
      setTab("form");
      return;
    }

    if (!config) return;
    const preview = await generatePreview(config);
    if (preview) setTab("yaml");
  };

  const openReview = async () => {
    if (!config) return;
    setBusy(true);
    try {
      if (tab === "yaml" && yamlEdited) {
        const result = await policyRequest<PolicyYamlValidationResponse>("/validate", {
          method: "POST",
          body: JSON.stringify({ policy_yaml: yamlContent }),
        });
        if (
          !result.valid ||
          !result.config ||
          !result.monetary_minor ||
          !result.policy_yaml
        ) {
          setYamlValidation({ valid: false, error: result.error });
          toast.error(result.error ?? "Policy YAML is invalid.");
          return;
        }
        setYamlValidation({ valid: true, error: null });
        setYamlConfig(result.config);
        setReview({
          config: result.config,
          monetary: result.monetary_minor,
          yaml: result.policy_yaml,
          warnings: [],
          source: "yaml",
        });
      } else {
        const preview = await policyRequest<PolicyPreviewResponse>("/preview", {
          method: "POST",
          body: JSON.stringify({ config }),
        });
        setYamlContent(preview.policy_yaml);
        setYamlValidation({ valid: true, error: null });
        setYamlConfig(preview.config);
        setReview({
          config: preview.config,
          monetary: preview.monetary_minor,
          yaml: preview.policy_yaml,
          warnings: preview.warnings,
          source: "structured",
        });
      }
      setConfirmed(false);
      setShowReview(true);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const publish = async () => {
    if (!review || !confirmed) return;
    setBusy(true);
    try {
      const body =
        review.source === "yaml"
          ? {
              policy_yaml: yamlContent,
              confirm: true,
              expected_active_version: expectedActiveVersion,
            }
          : {
              config: review.config,
              confirm: true,
              expected_active_version: expectedActiveVersion,
            };

      const result = await policyRequest<PolicyPublishResponse>("/publish", {
        method: "POST",
        body: JSON.stringify(body),
      });
      toast.success(`Policy v${result.version} published in ${result.currency}.`);
      setShowReview(false);
      setConfirmed(false);
      setReview(null);
      await loadAll();
    } catch (error) {
      toast.error(getErrorMessage(error));
      if (error instanceof PolicyApiError && error.status === 409) {
        setShowReview(false);
        await loadAll();
      }
    } finally {
      setBusy(false);
    }
  };

  const loadVersion = async (version: number) => {
    setBusy(true);
    try {
      const document = await policyRequest<PolicyDocumentResponse>(
        `/versions/${version}`,
      );
      if (!document.config) {
        toast.error("This stored version is not schema-valid and cannot be edited.");
        return;
      }
      const snapshot = cloneConfig(document.config);
      setConfig(snapshot);
      setYamlContent(document.policy_yaml);
      setYamlEdited(false);
      setYamlConfig(null);
      setYamlValidation({ valid: true, error: null });
      setEligibleText(formatCategoryList(snapshot.returns.eligible_categories));
      setNonReturnableText(
        formatCategoryList(snapshot.returns.non_returnable_categories),
      );
      setViewingVersion(version);
      setReview(null);
      setTab("form");
      toast.info(
        `Loaded v${version} as a draft. Publishing creates v${
          active?.next_version ?? version + 1
        }.`,
      );
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const resetDraft = () => {
    if (!baseline) return;
    const snapshot = cloneConfig(baseline);
    setConfig(snapshot);
    setYamlContent(active?.policy_yaml ?? "");
    setYamlEdited(false);
    setYamlConfig(null);
    setYamlValidation({ valid: true, error: null });
    setEligibleText(formatCategoryList(snapshot.returns.eligible_categories));
    setNonReturnableText(
      formatCategoryList(snapshot.returns.non_returnable_categories),
    );
    setViewingVersion(null);
    setReview(null);
    setTab("form");
  };

  const dirty =
    config !== null && baseline !== null && JSON.stringify(config) !== JSON.stringify(baseline);
  const hasActivePolicy = Boolean(active?.has_policy);
  const expectedActiveVersion = active?.has_policy ? active.version : 0;
  const nextVersion = active?.next_version ?? 1;
  const currency = config?.currency ?? active?.currency ?? "INR";
  const minorUnitLabel =
    currency === "INR" ? "paise" : currency === "USD" ? "cents" : "minor units";
  const canReview =
    config !== null &&
    (dirty ||
      !hasActivePolicy ||
      viewingVersion !== null ||
      (tab === "yaml" && yamlEdited));

  return (
    <div className="space-y-8">
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
          <p className="text-xs font-mono text-muted-foreground mt-2">
            Configure structured policies, preview canonical YAML, and publish an immutable
            version.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void loadAll()}
            disabled={loading || busy}
            className="h-10 px-4 rounded-full border border-border text-xs font-mono text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Reload</span>
          </button>

          {dirty || viewingVersion !== null ? (
            <button
              type="button"
              onClick={resetDraft}
              disabled={busy}
              className="h-10 px-4 rounded-full border border-border text-xs font-mono text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              <Undo2 className="w-3.5 h-3.5" />
              <span>Discard</span>
            </button>
          ) : null}

          <button
            type="button"
            onClick={() => void openReview()}
            disabled={!canReview || busy || (tab === "yaml" && !yamlValidation.valid)}
            className="h-10 px-6 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity flex items-center gap-2 disabled:opacity-40"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{busy ? "Checking…" : `Review & Publish v${nextVersion}`}</span>
          </button>
        </div>
      </div>

      <div className="p-4 rounded-md border border-border bg-card/40 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-sm border border-border bg-foreground/[0.02] flex items-center justify-center">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-medium text-foreground">
                {hasActivePolicy ? "Active enforcing policy" : "No published policy"}
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                {hasActivePolicy ? `v${active?.version}` : "baseline"}
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono border border-border text-muted-foreground">
                {currency}
              </span>
              {dirty ? (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-amber-500/10 border border-amber-500/30 text-amber-300">
                  Unsaved changes
                </span>
              ) : null}
            </div>
            <p className="text-xs font-mono text-muted-foreground">
              Activated: {formatDate(active?.activated_at ?? null)} · Next version: v
              {nextVersion}
            </p>
            <p className="text-[11px] font-mono text-muted-foreground mt-0.5">
              Source: {active?.source ?? "—"} · Checksum: {shortHash(active?.content_sha256 ?? null)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 border border-border rounded-full p-1 bg-background w-fit">
          <button
            type="button"
            onClick={() => void handleTabChange("form")}
            className={`px-3 py-1 rounded-full text-xs font-mono flex items-center gap-1.5 transition-colors ${
              tab === "form"
                ? "bg-foreground text-background font-medium"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Structured form</span>
          </button>
          <button
            type="button"
            onClick={() => void handleTabChange("yaml")}
            className={`px-3 py-1 rounded-full text-xs font-mono flex items-center gap-1.5 transition-colors ${
              tab === "yaml"
                ? "bg-foreground text-background font-medium"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Code2 className="w-3.5 h-3.5" />
            <span>YAML preview & edit</span>
          </button>
        </div>
      </div>

      {active && active.has_policy && !active.valid ? (
        <div className="p-3 rounded-md border border-destructive/30 bg-destructive/5 text-xs font-mono text-destructive flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>
            The active policy document is not schema-valid and is routed to manual review.
            Publishing a new version will replace it.
          </span>
        </div>
      ) : null}

      {viewingVersion !== null ? (
        <div className="p-3 rounded-md border border-amber-500/30 bg-amber-500/5 text-xs font-mono text-amber-200 flex items-center justify-between gap-3">
          <span className="flex items-center gap-2">
            <History className="w-4 h-4" />
            Editing v{viewingVersion} as a draft. Publishing creates v{nextVersion} and never
            modifies v{viewingVersion}.
          </span>
          <button
            type="button"
            onClick={resetDraft}
            className="underline underline-offset-2 hover:text-amber-100"
          >
            Back to active
          </button>
        </div>
      ) : null}

      {!config ? (
        <div className="p-8 rounded-md border border-border bg-card/20 text-center space-y-3">
          <p className="text-sm font-mono text-muted-foreground">
            {loading ? "Loading policy configuration…" : "Could not load the policy configuration."}
          </p>
          {!loading ? (
            <button
              type="button"
              onClick={() => void loadAll()}
              className="h-9 px-4 rounded-full border border-border text-xs font-mono hover:text-foreground text-muted-foreground"
            >
              Retry
            </button>
          ) : null}
        </div>
      ) : tab === "form" ? (
        <div className="space-y-6">
          <Section
            title="Return eligibility & shipping"
            description="Parameters applied autonomously to customer return and replacement requests."
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Field
                label="Return window (days)"
                hint="Eligible timeframe from the delivery date, inclusive."
              >
                <NumberInput
                  value={config.returns.window_days}
                  min={0}
                  max={90}
                  onChange={(value) => patchReturns({ window_days: value })}
                />
              </Field>

              <Field
                label="Return shipping fee"
                hint="Designates prepaid label billing liability."
              >
                <select
                  value={config.returns.return_shipping_paid_by}
                  onChange={(event) =>
                    patchReturns({
                      return_shipping_paid_by: event.target.value as "seller" | "buyer",
                    })
                  }
                  className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
                >
                  <option value="seller">Seller borne (free for customer)</option>
                  <option value="buyer">Deducted from customer refund</option>
                </select>
              </Field>

              <div className="flex flex-col justify-center gap-4">
                <Toggle
                  label="Auto-generate reverse pickup label"
                  description="Issues reverse AWB tracking when a return is approved."
                  checked={config.returns.auto_generate_shipping_label}
                  onChange={(checked) =>
                    patchReturns({ auto_generate_shipping_label: checked })
                  }
                />
                <Toggle
                  label="Require original packaging"
                  description="Returns must arrive in the original packaging."
                  checked={config.returns.require_original_packaging}
                  onChange={(checked) =>
                    patchReturns({ require_original_packaging: checked })
                  }
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
              <Field
                label="Eligible categories"
                hint="Comma-separated. Leave blank to accept every category."
              >
                <input
                  type="text"
                  value={eligibleText}
                  onChange={(event) => {
                    const value = event.target.value;
                    setEligibleText(value);
                    patchReturns({
                      eligible_categories:
                        value.trim() === "" ? null : parseCategoryList(value),
                    });
                  }}
                  placeholder="apparel, electronics, footwear"
                  className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
                />
              </Field>

              <Field
                label="Non-returnable categories"
                hint="Claims for these items are rejected by the deterministic engine."
              >
                <input
                  type="text"
                  value={nonReturnableText}
                  onChange={(event) => {
                    const value = event.target.value;
                    setNonReturnableText(value);
                    patchReturns({ non_returnable_categories: parseCategoryList(value) });
                  }}
                  placeholder="innerwear, perishables"
                  className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
                />
              </Field>
            </div>
          </Section>

          <Section
            title="Refund ceilings & escalation"
            description="Guardrails ensuring automated agents cannot settle payouts beyond your limits."
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Field
                label={`Autonomous refund ceiling (${currency})`}
                hint="Claims strictly above this amount pause for your approval. Sets both ceiling fields."
              >
                <NumberInput
                  value={config.refunds.auto_approve_up_to}
                  min={0}
                  max={100000}
                  step={100}
                  prefix={currency}
                  onChange={setRefundCeiling}
                />
              </Field>

              <Field
                label={`Instant refund without return (${currency})`}
                hint="Small claims settled without return transit."
              >
                <NumberInput
                  value={config.refunds.instant_refund_without_return_threshold}
                  min={0}
                  max={100000}
                  step={50}
                  prefix={currency}
                  onChange={(value) =>
                    patchRefunds({ instant_refund_without_return_threshold: value })
                  }
                />
              </Field>

              <Field label="COD refund method" hint="How cash-on-delivery claims are settled.">
                <select
                  value={config.refunds.cod_refund_method}
                  onChange={(event) =>
                    patchRefunds({
                      cod_refund_method: event.target.value as
                        | "store_credit"
                        | "bank_transfer",
                    })
                  }
                  className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
                >
                  <option value="store_credit">Store credit</option>
                  <option value="bank_transfer">Bank transfer</option>
                </select>
              </Field>

              <div className="grid grid-cols-2 gap-4">
                <Field label="Processing SLA (days)">
                  <NumberInput
                    value={config.refunds.processing_sla_days}
                    min={0}
                    max={30}
                    onChange={(value) => patchRefunds({ processing_sla_days: value })}
                  />
                </Field>
                <Field label="Restocking fee (%)">
                  <NumberInput
                    value={config.refunds.restocking_fee_percentage}
                    min={0}
                    max={100}
                    onChange={(value) =>
                      patchRefunds({ restocking_fee_percentage: value })
                    }
                  />
                </Field>
              </div>
            </div>
          </Section>

          <Section
            title="Shipping delays & proactive remedies"
            description="Rules executed by the background monitor when shipments exceed the promised delivery date."
          >
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <Field label="Delay trigger (days late)">
                <NumberInput
                  value={config.delays.notify_after_days_late}
                  min={1}
                  max={30}
                  onChange={(value) => patchDelays({ notify_after_days_late: value })}
                />
              </Field>

              <Field
                label={`Compensation per day (${currency})`}
                hint="0 disables automatic delay credit."
              >
                <NumberInput
                  value={config.delays.compensation_per_day_late}
                  min={0}
                  max={100000}
                  prefix={currency}
                  onChange={(value) =>
                    patchDelays({ compensation_per_day_late: value })
                  }
                />
              </Field>

              <Field label={`Maximum compensation (${currency})`}>
                <NumberInput
                  value={config.delays.max_delay_compensation}
                  min={0}
                  max={100000}
                  prefix={currency}
                  onChange={(value) => patchDelays({ max_delay_compensation: value })}
                />
              </Field>

              <Field
                label="Late return allowance (days)"
                hint="A shipment this late also permits a return."
              >
                <NumberInput
                  value={config.delays.allow_return_if_late_days_at_least}
                  min={1}
                  max={30}
                  onChange={(value) =>
                    patchDelays({ allow_return_if_late_days_at_least: value })
                  }
                />
              </Field>
            </div>
          </Section>

          <Section
            title="Damage claims & fraud checks"
            description="Verification requirements for transit defects and buyer refund velocity."
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="space-y-5">
                <Toggle
                  label="Require photo evidence for damage claims"
                  checked={config.damage_claims.require_photo}
                  onChange={(checked) => patchDamage({ require_photo: checked })}
                />

                <Field label="Damage report window (days)">
                  <NumberInput
                    value={config.damage_claims.report_within_days}
                    min={1}
                    max={30}
                    onChange={(value) => patchDamage({ report_within_days: value })}
                  />
                </Field>

                <Field label={`Auto-replacement max amount (${currency})`}>
                  <NumberInput
                    value={config.damage_claims.auto_replacement_under_amount}
                    min={0}
                    max={100000}
                    prefix={currency}
                    onChange={(value) =>
                      patchDamage({ auto_replacement_under_amount: value })
                    }
                  />
                </Field>

                <Field
                  label={`Warehouse inspection above (${currency})`}
                  hint="Higher-value replacements require inspection."
                >
                  <NumberInput
                    value={config.damage_claims.require_warehouse_inspection_above}
                    min={0}
                    max={100000}
                    prefix={currency}
                    onChange={(value) =>
                      patchDamage({ require_warehouse_inspection_above: value })
                    }
                  />
                </Field>
              </div>

              <div className="space-y-5">
                <Field
                  label="Max refunds per buyer (30 days)"
                  hint="Velocity check that escalates when the buyer exceeds this count."
                >
                  <NumberInput
                    value={config.fraud_checks.max_refunds_per_buyer_per_30_days}
                    min={1}
                    max={20}
                    onChange={(value) =>
                      patchFraud({ max_refunds_per_buyer_per_30_days: value })
                    }
                  />
                </Field>

                <Toggle
                  label="Require seller approval if the limit is exceeded"
                  checked={config.fraud_checks.require_seller_approval_if_exceeded}
                  onChange={(checked) =>
                    patchFraud({ require_seller_approval_if_exceeded: checked })
                  }
                />

                <Toggle
                  label="Manual review for high-value orders"
                  checked={config.fraud_checks.require_manual_review_for_high_value}
                  onChange={(checked) =>
                    patchFraud({ require_manual_review_for_high_value: checked })
                  }
                />

                <Field label={`High-value order threshold (${currency})`}>
                  <NumberInput
                    value={config.fraud_checks.high_value_order_threshold}
                    min={0}
                    max={1000000}
                    prefix={currency}
                    onChange={(value) =>
                      patchFraud({ high_value_order_threshold: value })
                    }
                  />
                </Field>

                <Toggle
                  label="Block high-risk PIN codes and unverified addresses"
                  checked={config.fraud_checks.block_suspicious_addresses}
                  onChange={(checked) =>
                    patchFraud({ block_suspicious_addresses: checked })
                  }
                />
              </div>
            </div>
          </Section>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-md border border-border bg-card/20">
            <p className="text-[11px] font-mono text-muted-foreground">
              Amounts are entered in {currency}. The server converts them to integer minor
              units (1 {currency} = 100 {minorUnitLabel}) for evaluation and records the
              minor-unit snapshot.
            </p>
            <button
              type="button"
              onClick={() => void handleTabChange("yaml")}
              disabled={busy}
              className="h-9 px-4 rounded-full border border-border text-xs font-mono text-foreground hover:bg-foreground/[0.03] flex items-center gap-2 disabled:opacity-50 w-fit"
            >
              <FileCode className="w-3.5 h-3.5" />
              Preview generated YAML
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div
            className={`p-3 rounded-md border flex items-center justify-between gap-3 text-xs font-mono ${
              yamlValidation.valid
                ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-300"
                : "border-destructive/30 bg-destructive/5 text-destructive"
            }`}
          >
            <div className="flex items-center gap-2">
              {yamlValidation.valid ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>YAML is valid against the canonical PolicySchema.</span>
                </>
              ) : (
                <>
                  <AlertTriangle className="w-4 h-4 text-destructive" />
                  <span>Validation error: {yamlValidation.error}</span>
                </>
              )}
            </div>
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground shrink-0">
              Server-validated
            </span>
          </div>

          <div className="rounded-md border border-border bg-background p-4">
            <textarea
              value={yamlContent}
              onChange={(event) => handleYamlChange(event.target.value)}
              rows={26}
              className="w-full bg-transparent font-mono text-xs text-foreground focus:outline-none resize-none leading-relaxed"
              spellCheck={false}
            />
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <p className="text-[11px] font-mono text-muted-foreground">
              Editing is optional. Unknown fields are rejected, and the server stores the
              canonical YAML checksum with every version.
            </p>
            <button
              type="button"
              onClick={() => void openReview()}
              disabled={!yamlValidation.valid || busy}
              className="h-9 px-4 rounded-full border border-border text-xs font-mono text-foreground hover:bg-foreground/[0.03] flex items-center gap-2 disabled:opacity-50 w-fit"
            >
              <Lock className="w-3.5 h-3.5" />
              Validate & review
            </button>
          </div>
        </div>
      )}

      <div className="space-y-4 pt-6 border-t border-border">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-muted-foreground" />
          <h2 className="font-display text-xl tracking-tight text-foreground">
            Policy version history
          </h2>
        </div>

        {history.length === 0 ? (
          <p className="text-xs font-mono text-muted-foreground">
            No published versions yet. Your first publication will be v1.
          </p>
        ) : (
          <div className="border border-border rounded-md overflow-x-auto bg-card/30">
            <table className="w-full text-left text-xs font-mono min-w-[860px]">
              <thead className="bg-foreground/[0.02] border-b border-border text-muted-foreground uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="p-3.5">Version</th>
                  <th className="p-3.5">Currency</th>
                  <th className="p-3.5">Created</th>
                  <th className="p-3.5">Activated</th>
                  <th className="p-3.5">Refund ceiling</th>
                  <th className="p-3.5">Window</th>
                  <th className="p-3.5">Checksum</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {history.map((item) => (
                  <tr key={item.id} className="hover:bg-foreground/[0.02] transition-colors">
                    <td className="p-3.5 font-medium text-foreground">v{item.version}</td>
                    <td className="p-3.5 text-muted-foreground">{item.currency}</td>
                    <td className="p-3.5 text-muted-foreground">
                      {formatDate(item.created_at)}
                    </td>
                    <td className="p-3.5 text-muted-foreground">
                      {formatDate(item.activated_at)}
                    </td>
                    <td className="p-3.5 text-muted-foreground">
                      {item.refund_ceiling === null
                        ? "—"
                        : formatMoney(item.refund_ceiling, item.currency)}
                    </td>
                    <td className="p-3.5 text-muted-foreground">
                      {item.returns_window === null ? "—" : `${item.returns_window}d`}
                    </td>
                    <td
                      className="p-3.5 text-muted-foreground"
                      title={item.content_sha256 ?? undefined}
                    >
                      {shortHash(item.content_sha256)}
                    </td>
                    <td className="p-3.5">
                      {item.is_active ? (
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
                    <td className="p-3.5 text-right">
                      <button
                        type="button"
                        onClick={() => void loadVersion(item.version)}
                        disabled={busy}
                        className="px-3 py-1 rounded-full border border-border text-[10px] uppercase tracking-wider text-muted-foreground hover:text-foreground disabled:opacity-50"
                      >
                        {item.is_active ? "View" : "Load draft"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showReview && review ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="policy-review-title"
        >
          <div
            className="absolute inset-0 bg-black/70"
            onClick={() => {
              if (!busy) setShowReview(false);
            }}
          />
          <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-lg border border-border bg-background shadow-2xl">
            <div className="flex items-start justify-between gap-4 border-b border-border p-5">
              <div>
                <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                  <Lock className="w-3.5 h-3.5" />
                  Explicit confirmation required
                </div>
                <h2
                  id="policy-review-title"
                  className="font-display text-2xl tracking-tight text-foreground mt-1"
                >
                  Publish policy v{nextVersion}
                </h2>
                <p className="text-xs font-mono text-muted-foreground mt-1">
                  {review.source === "yaml"
                    ? "Source: edited YAML"
                    : "Source: structured form"}{" "}
                  · Replaces {expectedActiveVersion ? `v${expectedActiveVersion}` : "no active policy"}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowReview(false)}
                disabled={busy}
                className="w-8 h-8 rounded-full border border-border flex items-center justify-center text-muted-foreground hover:text-foreground disabled:opacity-50"
                aria-label="Close review"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                <div className="p-3 rounded-md border border-border bg-card/30">
                  <span className="text-muted-foreground uppercase text-[10px] block">
                    Refund ceiling
                  </span>
                  <span className="text-foreground">
                    {formatMoney(
                      review.config.refunds.auto_approve_up_to,
                      review.monetary.currency,
                    )}
                  </span>
                  <span className="text-[10px] text-muted-foreground block mt-1">
                    {formatPaise(review.monetary.refund_auto_approve_ceiling_minor)}
                  </span>
                </div>
                <div className="p-3 rounded-md border border-border bg-card/30">
                  <span className="text-muted-foreground uppercase text-[10px] block">
                    Instant refund threshold
                  </span>
                  <span className="text-foreground">
                    {formatMoney(
                      review.config.refunds.instant_refund_without_return_threshold,
                      review.monetary.currency,
                    )}
                  </span>
                  <span className="text-[10px] text-muted-foreground block mt-1">
                    {formatPaise(
                      review.monetary.refund_instant_without_return_threshold_minor,
                    )}
                  </span>
                </div>
                <div className="p-3 rounded-md border border-border bg-card/30">
                  <span className="text-muted-foreground uppercase text-[10px] block">
                    Return window
                  </span>
                  <span className="text-foreground">
                    {review.config.returns.window_days} days
                  </span>
                </div>
                <div className="p-3 rounded-md border border-border bg-card/30">
                  <span className="text-muted-foreground uppercase text-[10px] block">
                    Delay compensation
                  </span>
                  <span className="text-foreground">
                    {formatMoney(
                      review.config.delays.compensation_per_day_late,
                      review.monetary.currency,
                    )}{" "}
                    / day
                  </span>
                  <span className="text-[10px] text-muted-foreground block mt-1">
                    Cap{" "}
                    {formatMinorUnits(
                      review.monetary.delay_compensation_max_minor,
                      review.monetary.currency,
                      review.monetary.minor_unit_exponent,
                    )}
                  </span>
                </div>
                <div className="p-3 rounded-md border border-border bg-card/30">
                  <span className="text-muted-foreground uppercase text-[10px] block">
                    Damage replacement max
                  </span>
                  <span className="text-foreground">
                    {formatMoney(
                      review.config.damage_claims.auto_replacement_under_amount,
                      review.monetary.currency,
                    )}
                  </span>
                  <span className="text-[10px] text-muted-foreground block mt-1">
                    {formatPaise(review.monetary.damage_auto_replacement_max_minor)}
                  </span>
                </div>
                <div className="p-3 rounded-md border border-border bg-card/30">
                  <span className="text-muted-foreground uppercase text-[10px] block">
                    Buyer refund limit
                  </span>
                  <span className="text-foreground">
                    {review.config.fraud_checks.max_refunds_per_buyer_per_30_days} / 30 days
                  </span>
                  <span className="text-[10px] text-muted-foreground block mt-1">
                    High value ≥{" "}
                    {formatMinorUnits(
                      review.monetary.fraud_high_value_order_threshold_minor,
                      review.monetary.currency,
                      review.monetary.minor_unit_exponent,
                    )}
                  </span>
                </div>
              </div>

              {review.warnings.length > 0 ? (
                <div className="p-3 rounded-md border border-amber-500/30 bg-amber-500/5 text-[11px] font-mono text-amber-200 space-y-1">
                  {review.warnings.map((warning) => (
                    <p key={warning}>• {warning}</p>
                  ))}
                </div>
              ) : null}

              <div className="rounded-md border border-border bg-background p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                    Canonical YAML that will be stored
                  </span>
                  <span className="text-[10px] font-mono text-muted-foreground">
                    immutable once published
                  </span>
                </div>
                <pre className="max-h-48 overflow-auto font-mono text-[11px] leading-relaxed text-foreground whitespace-pre-wrap">
                  {review.yaml}
                </pre>
              </div>

              <label className="flex items-start gap-3 cursor-pointer p-3 rounded-md border border-border bg-card/30">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(event) => setConfirmed(event.target.checked)}
                  className="mt-0.5 rounded border-border text-foreground focus:ring-0"
                />
                <span className="text-[11px] font-mono text-foreground">
                  I confirm publication of v{nextVersion}. This immutable version will govern
                  future automated decisions for {review.monetary.currency} orders, and this
                  action is recorded in the audit log.
                </span>
              </label>
            </div>

            <div className="flex items-center justify-end gap-3 border-t border-border p-5">
              <button
                type="button"
                onClick={() => setShowReview(false)}
                disabled={busy}
                className="h-10 px-4 rounded-full border border-border text-xs font-mono text-muted-foreground hover:text-foreground disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void publish()}
                disabled={!confirmed || busy}
                className="h-10 px-6 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 flex items-center gap-2 disabled:opacity-40"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                {busy ? "Publishing…" : `Publish v${nextVersion}`}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
