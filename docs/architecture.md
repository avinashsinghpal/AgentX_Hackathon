# SellerResolve System Architecture

**Team:** Break The Bug  
**Hackathon:** AgentX Hackathon 2026 (PS-04)  
**Product:** SellerResolve — Autonomous, Policy-Aware Support Agent  
**Tagline:** *Investigate. Decide. Act. Verify.*

---

## 1. System Vision & Core Value Proposition

For small and medium online sellers, customer support is dominated by post-purchase queries: returns, refunds, order tracking, and transit delays. Standard chatbots fail because they merely answer questions with text, hallucinate policy exceptions, or cannot take action safely.

SellerResolve operates as an autonomous operational resolution engine:
1. **Investigates** authenticated order, shipment, and payment records.
2. **Decides** eligibility using the seller's deterministic policies (not LLM discretion).
3. **Acts** safely by creating return labels, triggering refunds, or escalating to the seller.
4. **Verifies** the operational outcome with external courier and payment connectors.
5. **Logs** every turn, tool invocation, and decision into a mathematically tamper-evident SHA-256 chained audit trail.

---

## 2. High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph Clients ["Client Layer"]
        Buyer["Buyer Browser (Portal / Resolution Room)"]
        Seller["Seller Browser (Operations Console / Approvals)"]
    end

    subgraph WebApp ["Next.js 16 Web Application (apps/web)"]
        Landing["Landing & Legal Pages"]
        BuyerRoutes["/buyer/* (Directory, Orders, Complaints, Chat)"]
        SellerRoutes["/seller/* (Onboarding, Policies, Approvals, Audit)"]
        Proxy["Next.js API Rewrite Proxy (/api/v1/*)"]
    end

    subgraph Backend ["FastAPI Core Services (apps/api)"]
        AuthMid["Security Middleware (Argon2id, Session HMAC, CSRF)"]
        RateLimiter["SlowAPI Rate Limiter"]
        
        subgraph AgentEngine ["Autonomous Resolution Engine"]
            Orchestrator["Resolution Orchestrator"]
            InvestigateTools["Investigation Tools (Order & Shipment Lookup)"]
            PolicyEngine["Deterministic Policy Engine (Pydantic V2 AST)"]
            ActionGuard["Action Guard & Execution Verification"]
            LLMClient["LLM Explanation Layer (Gemini / Anthropic / FakeClient)"]
        end

        subgraph BackgroundServices ["Background Support Services"]
            DelayMonitor["APScheduler Proactive Transit Delay Monitor"]
            FileValidator["Magic-Byte Evidence Validator"]
        end

        subgraph AuditEngine ["Cryptographic Audit Engine"]
            HashChain["SHA-256 Append-Only Chaining"]
            GenesisBlock["Deterministic Genesis Hash"]
            TamperDetector["Mathematical Chain Verifier"]
            CSVStream["Streaming CSV Exporter"]
        end
    end

    subgraph Storage ["Persistence Layer"]
        DB[(SQLite / PostgreSQL Engine via SQLAlchemy 2.0)]
        DiskStore[(Isolated File Storage for Photo Proof)]
    end

    Buyer --> BuyerRoutes
    Seller --> SellerRoutes
    BuyerRoutes --> Proxy
    SellerRoutes --> Proxy
    Proxy --> AuthMid
    AuthMid --> RateLimiter
    RateLimiter --> Orchestrator
    
    Orchestrator --> InvestigateTools
    InvestigateTools --> DB
    Orchestrator --> PolicyEngine
    PolicyEngine --> ActionGuard
    ActionGuard --> DB
    ActionGuard --> AuditEngine
    ActionGuard --> LLMClient
    
    DelayMonitor --> DB
    DelayMonitor --> AuditEngine
    AuditEngine --> DB
```

---

## 3. The 4-Phase Resolution Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Buyer
    participant Orch as Resolution Orchestrator
    participant Tools as Investigation Tools
    participant Policy as Deterministic Policy Engine
    participant Action as Action & Verification
    participant Audit as Cryptographic Audit Log
    participant LLM as LLM Explanation Generator

    Customer->>Orch: Submit Complaint Narrative + Photo Evidence
    Note over Orch: Phase 1: INVESTIGATE
    Orch->>Tools: lookup_order(order_id)
    Tools-->>Orch: Order Details (Status, Amount, Delivery Date)
    Orch->>Tools: lookup_shipment(order_id)
    Tools-->>Orch: Shipment Status, Carrier, AWB Tracking

    Note over Orch: Phase 2: DECIDE (Deterministic)
    Orch->>Policy: evaluate_policy_rules(order, category, evidence)
    Note over Policy: Return window check<br/>Photo requirement check<br/>Auto-approve financial ceiling check
    Policy-->>Orch: Decision (executed | needs_approval | not_eligible)

    Note over Orch: Phase 3: ACT
    alt Eligible <= Ceiling
        Orch->>Action: generate_return_label / issue_refund
        Action-->>Orch: Action Result (AWB generated, refund queued)
    else Exceeds Auto-Approve Ceiling
        Orch->>Action: escalate_for_approval
        Action-->>Orch: ApprovalRequest queued for seller
    else Ineligible
        Orch->>Action: record_ineligibility_rejection
    end

    Note over Orch: Phase 4: VERIFY
    Orch->>Tools: verify_action_outcome(action, case_id)
    Tools-->>Orch: Verified Status

    Orch->>Audit: Append Audit Record (SHA-256 Chained)
    Audit-->>Orch: Record Hash & Sequence

    Orch->>LLM: Generate Grounded Explanation (Zero Emoji System Prompt)
    LLM-->>Orch: Transparent Explanation + Tool Trace
    Orch-->>Customer: Decision Badge + Agent Explanation + Collapsible Tool Trace
```

---

## 4. Key Architectural Guarantees & Non-Negotiables

### 1. Deterministic Policy Boundary (No LLM Hallucinations)
- The LLM **never** decides refund eligibility, policy windows, or financial amounts.
- The policy AST is parsed from seller YAML and evaluated strictly in Python.
- If an order is delivered 22 days ago and the return policy is 14 days, the engine deterministically rejects the claim (`not_eligible`), irrespective of customer prompts.

### 2. Strict Server-Side Identity Scoping
- `buyer_id`, `seller_id`, and `order_id` are injected server-side from session tokens and database associations.
- A buyer cannot access or resolve claims for another buyer's orders.
- Multi-tenant seller separation is enforced across every query.

### 3. Cryptographic Audit Log (SHA-256 Hash Chaining)
- Every audit record contains:
  $$\text{Record Hash} = \text{SHA256}(\text{prev\_hash} \parallel \text{timestamp} \parallel \text{seller\_id} \parallel \text{case\_id} \parallel \text{action} \parallel \text{payload})$$
- The genesis record links to an initial genesis hash.
- Any manual modification, deletion, or reordering of records mathematically invalidates subsequent hashes and is instantly caught by `AuditLogService.verify_chain()`.

### 4. Proactive Background Monitor
- An automated scheduler checks active in-transit shipments without waiting for a customer complaint.
- Stalled packages exceeding seller SLA automatically receive wallet credits and proactive notification cases.

### 5. Zero Emoji & Zero Runtime Assets
- The entire codebase, agent replies, UI copy, and system logs enforce the strict zero-emoji mandate.
- All visual assets are 100% self-hosted SVGs and canvas animations; zero external blob dependencies.
