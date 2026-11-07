# SellerResolve Policy Engine Schema (Version 1)

## 1. Overview
Seller policies are declared in YAML, validated strictly against a Pydantic V2 schema, and evaluated deterministically.
No LLM is permitted to alter or interpret policy rules during decision evaluation.

---

## 2. Policy Schema Specification

```yaml
version: 1
currency: INR

returns:
  window_days: 7                           # Days after delivery within which return is permitted
  non_returnable_categories:               # SKUs matching these categories cannot be returned
    - innerwear
    - perishables

refunds:
  auto_approve_up_to: 500                  # Max amount in Rupees eligible for auto-approval
  require_seller_approval_above: 500       # Amounts above this threshold require seller sign-off
  cod_refund_method: store_credit          # 'store_credit' or 'bank_transfer'

delays:
  notify_after_days_late: 2                # Days past promised delivery date to trigger alert
  allow_return_if_late_days_at_least: 3    # Allow return/cancellation if late by this many days

damage_claims:
  require_photo: true                      # Whether photo evidence is mandatory
  report_within_days: 2                    # Window to report damage from delivery

fraud_checks:
  max_refunds_per_buyer_per_30_days: 3     # Frequency limit for buyers
  require_seller_approval_if_exceeded: true
```

---

## 3. Evaluation Pipeline Order
1. **Ownership & Scope:** Verify buyer owns order and order belongs to case seller.
2. **Seller Status:** Ensure seller has active onboarding status and active policy.
3. **Delivery Coverage:** Check PIN code and serviceable warehouse delivery timelines.
4. **Duplicate Protection:** Prevent duplicate returns or refunds for the same order and reason.
5. **Return Window & Category:** Validate delivery date + `window_days`, non-returnable categories.
6. **Evidence Requirements:** Verify required photo attachments for damaged items.
7. **Monetary Thresholds:** Compare minor unit amount against `auto_approve_up_to`.
8. **Risk Assessment:** Check buyer refund history within last 30 days.
9. **COD Specifics:** Apply configured COD refund method.

