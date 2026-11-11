/**
 * Typed contract for the seller policy configuration workflow.
 *
 * The shapes mirror `apps/api/app/schemas/policy.py` and
 * `apps/api/app/schemas/policy_config.py` exactly. Monetary inputs are integer
 * major units (rupees); the API is the only place that converts them to integer
 * minor units (`minor`, for example paise for INR or cents for USD) for
 * evaluation and storage.
 */

export interface ReturnsPolicy {
  window_days: number;
  non_returnable_categories: string[];
  eligible_categories: string[] | null;
  return_shipping_paid_by: "seller" | "buyer";
  auto_generate_shipping_label: boolean;
  require_original_packaging: boolean;
}

export interface RefundsPolicy {
  auto_approve_up_to: number;
  require_seller_approval_above: number;
  cod_refund_method: "store_credit" | "bank_transfer";
  instant_refund_without_return_threshold: number;
  restocking_fee_percentage: number;
  processing_sla_days: number;
}

export interface DelaysPolicy {
  notify_after_days_late: number;
  allow_return_if_late_days_at_least: number;
  compensation_per_day_late: number;
  max_delay_compensation: number;
}

export interface DamageClaimsPolicy {
  require_photo: boolean;
  report_within_days: number;
  auto_replacement_under_amount: number;
  require_warehouse_inspection_above: number;
}

export interface FraudChecksPolicy {
  max_refunds_per_buyer_per_30_days: number;
  require_seller_approval_if_exceeded: boolean;
  require_manual_review_for_high_value: boolean;
  high_value_order_threshold: number;
  block_suspicious_addresses: boolean;
}

export interface PolicyConfig {
  version: number;
  currency: string;
  returns: ReturnsPolicy;
  refunds: RefundsPolicy;
  delays: DelaysPolicy;
  damage_claims: DamageClaimsPolicy;
  fraud_checks: FraudChecksPolicy;
}

export interface PolicyMonetaryMinor {
  currency: string;
  minor_unit_exponent: number;
  refund_auto_approve_ceiling_minor: number;
  refund_instant_without_return_threshold_minor: number;
  delay_compensation_per_day_minor: number;
  delay_compensation_max_minor: number;
  damage_auto_replacement_max_minor: number;
  damage_warehouse_inspection_threshold_minor: number;
  fraud_high_value_order_threshold_minor: number;
}

export interface PolicyDocumentResponse {
  has_policy: boolean;
  valid: boolean;
  id: string | null;
  version: number;
  next_version: number;
  currency: string;
  policy_yaml: string;
  config: PolicyConfig | null;
  parsed_rules: Record<string, unknown>;
  monetary_minor: PolicyMonetaryMinor | null;
  activated_at: string | null;
  created_at: string | null;
  source: string | null;
  content_sha256: string | null;
}

export interface PolicyHistoryItem {
  id: string;
  version: number;
  is_active: boolean;
  currency: string;
  created_at: string;
  activated_at: string | null;
  source: string | null;
  content_sha256: string | null;
  returns_window: number | null;
  refund_ceiling: number | null;
  refund_ceiling_minor: number | null;
}

export interface PolicyPreviewResponse {
  valid: boolean;
  currency: string;
  config: PolicyConfig;
  monetary_minor: PolicyMonetaryMinor;
  policy_yaml: string;
  warnings: string[];
}

export interface PolicyYamlValidationResponse {
  valid: boolean;
  error: string | null;
  config: PolicyConfig | null;
  policy_yaml: string | null;
  parsed: Record<string, unknown> | null;
  monetary_minor: PolicyMonetaryMinor | null;
}

export interface PolicyPublishResponse {
  success: boolean;
  id: string;
  version: number;
  previous_version: number;
  currency: string;
  policy_yaml: string;
  config: PolicyConfig;
  parsed_rules: Record<string, unknown>;
  monetary_minor: PolicyMonetaryMinor;
  activated_at: string | null;
  created_at: string | null;
  source: string;
  content_sha256: string;
}

export interface PolicyValidationDetail {
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
}

interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
    details?: PolicyValidationDetail[];
  };
}

export class PolicyApiError extends Error {
  status: number;
  details: PolicyValidationDetail[];

  constructor(
    message: string,
    status: number,
    details: PolicyValidationDetail[] = [],
  ) {
    super(message);
    this.name = "PolicyApiError";
    this.status = status;
    this.details = details;
  }
}

const POLICY_BASE = "/api/v1/seller/policies";

export async function policyRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${POLICY_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  const body = (await response.json().catch(() => null)) as
    | T
    | ApiErrorEnvelope
    | null;

  if (!response.ok) {
    const envelope = (body ?? {}) as ApiErrorEnvelope;
    const detailText = envelope.error?.details
      ?.slice(0, 3)
      .map((detail) => {
        const location = (detail.loc ?? []).join(".");
        return location ? `${location}: ${detail.msg ?? "invalid"}` : detail.msg;
      })
      .filter(Boolean)
      .join("; ");

    throw new PolicyApiError(
      envelope.error?.message ??
        detailText ??
        `Policy request failed (HTTP ${response.status})`,
      response.status,
      envelope.error?.details ?? [],
    );
  }

  return body as T;
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof PolicyApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Unexpected policy error";
}

export function createDefaultPolicyConfig(currency = "INR"): PolicyConfig {
  return {
    version: 1,
    currency,
    returns: {
      window_days: 7,
      non_returnable_categories: ["innerwear", "perishables"],
      eligible_categories: null,
      return_shipping_paid_by: "seller",
      auto_generate_shipping_label: true,
      require_original_packaging: false,
    },
    refunds: {
      auto_approve_up_to: 500,
      require_seller_approval_above: 500,
      cod_refund_method: "store_credit",
      instant_refund_without_return_threshold: 500,
      restocking_fee_percentage: 0,
      processing_sla_days: 2,
    },
    delays: {
      notify_after_days_late: 2,
      allow_return_if_late_days_at_least: 3,
      compensation_per_day_late: 0,
      max_delay_compensation: 0,
    },
    damage_claims: {
      require_photo: true,
      report_within_days: 2,
      auto_replacement_under_amount: 1500,
      require_warehouse_inspection_above: 5000,
    },
    fraud_checks: {
      max_refunds_per_buyer_per_30_days: 3,
      require_seller_approval_if_exceeded: true,
      require_manual_review_for_high_value: false,
      high_value_order_threshold: 5000,
      block_suspicious_addresses: false,
    },
  };
}

export function formatMoney(majorUnits: number, currency: string): string {
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(majorUnits);
  } catch {
    return `${currency} ${majorUnits.toLocaleString("en-IN")}`;
  }
}

export function formatMinorUnits(
  minorUnits: number,
  currency: string,
  exponent = 2,
): string {
  const major = minorUnits / 10 ** exponent;
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: exponent,
    }).format(major);
  } catch {
    return `${currency} ${major}`;
  }
}

export function formatPaise(minorUnits: number): string {
  return `${minorUnits.toLocaleString("en-IN")} paise`;
}

export function parseCategoryList(value: string): string[] {
  return value
    .split(",")
    .map((category) => category.trim().toLowerCase())
    .filter(Boolean);
}

export function formatCategoryList(categories: string[] | null): string {
  return (categories ?? []).join(", ");
}

export function shortHash(hash: string | null): string {
  return hash ? `${hash.slice(0, 12)}…` : "—";
}

export function toInteger(value: string, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.trunc(parsed) : fallback;
}
