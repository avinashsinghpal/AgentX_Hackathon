"use client";

import React, { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Bot,
  User,
  ArrowLeft,
  Send,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Clock,
  XCircle,
  Truck,
  Package,
  ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";

interface CaseDetail {
  case: {
    id: string;
    case_number: string;
    order_number: string;
    seller_name: string;
    issue_category: string;
    status: string;
    decision?: string | null;
    created_at: string;
  };
  order: {
    id: string;
    order_number: string;
    seller_name: string;
    total_amount: number;
    currency: string;
    order_status: string;
    payment_method: string;
    tracking_number?: string | null;
    carrier?: string | null;
    delivery_date?: string | null;
  };
  customer_narrative: string;
  evidence_urls: string[];
  messages: Array<{
    id: string;
    sender_role: string;
    message: string;
    tool_calls?: Array<{
      tool_name: string;
      tool_args: Record<string, unknown>;
      outcome: string;
      timestamp: string;
    }> | null;
    decision_badge?: string | null;
    created_at: string;
    delivery_state?: "sending";
  }>;
}

const DEMO_CASE_DETAIL: CaseDetail = {
  case: {
    id: "case-demo-1001",
    case_number: "CAS-1001",
    order_number: "ORD-1001",
    seller_name: "Apex Electronics",
    issue_category: "return",
    status: "resolved",
    decision: "executed",
    created_at: "2026-11-06T12:00:00Z",
  },
  order: {
    id: "ord-1001",
    order_number: "ORD-1001",
    seller_name: "Apex Electronics",
    total_amount: 45.0,
    currency: "USD",
    order_status: "delivered",
    payment_method: "card",
    tracking_number: "TRK-9821448",
    carrier: "BlueDart",
    delivery_date: "2026-11-01T10:00:00Z",
  },
  customer_narrative: "I would like to return the wireless earbuds. The package is unopened and in original condition.",
  evidence_urls: [],
  messages: [
    {
      id: "msg-1",
      sender_role: "buyer",
      message: "I would like to return the wireless earbuds. The package is unopened and in original condition.",
      created_at: "2026-11-06T12:00:00Z",
    },
    {
      id: "msg-2",
      sender_role: "agent",
      message: "I have investigated your order record and verified that your purchase of ORD-1001 ($45.00) was delivered 5 days ago, well within Apex Electronics' 14-day return window. Because the item is in unopened condition and falls within our autonomous return limit, I have authorized your return immediately. A prepaid return shipping label (RET-99214) has been generated.",
      tool_calls: [
        {
          tool_name: "lookup_order",
          tool_args: { order_id: "ORD-1001" },
          outcome: "Order status: delivered; Total: $45.00; Delivered: 5 days ago",
          timestamp: "2026-11-06T12:00:01Z",
        },
        {
          tool_name: "lookup_shipment",
          tool_args: { order_id: "ORD-1001" },
          outcome: "Shipment carrier: BlueDart; Tracking: TRK-9821448; Actual delivery confirmed",
          timestamp: "2026-11-06T12:00:02Z",
        },
        {
          tool_name: "evaluate_policy_rules",
          tool_args: { category: "return", days_since_delivery: 5, amount: 45.0 },
          outcome: "Eligibility verified: within 14-day return window; amount <= auto_approve_max ($50.00)",
          timestamp: "2026-11-06T12:00:03Z",
        },
        {
          tool_name: "execute_and_verify_action",
          tool_args: { action: "approve_return", case_id: "case-demo-1001" },
          outcome: "Return label RET-99214 generated; status updated to return_approved",
          timestamp: "2026-11-06T12:00:04Z",
        },
      ],
      decision_badge: "executed",
      created_at: "2026-11-06T12:00:05Z",
    },
  ],
};

export default function CaseRoomPage() {
  const params = useParams();
  const caseId = params?.id as string;

  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [inputMsg, setInputMsg] = useState("");
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [retryRequest, setRetryRequest] = useState<{ text: string; id: string } | null>(null);
  const [expandedInvestigations, setExpandedInvestigations] = useState<Record<string, boolean>>({
    "msg-2": true,
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchCaseDetail = React.useCallback(async () => {
    if (!caseId) return;
    try {
      const res = await fetch(`/api/v1/buyer/cases/${caseId}`);
      if (res.ok) {
        const data = await res.json();
        setDetail(data);
      } else if (caseId === "demo" || caseId === "CAS-1001") {
        setDetail(DEMO_CASE_DETAIL);
      } else {
        toast.error("Failed to load resolution room");
      }
    } catch {
      if (caseId === "demo" || caseId === "CAS-1001") {
        setDetail(DEMO_CASE_DETAIL);
      } else {
        toast.error("Network error while connecting to resolution room");
      }
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchCaseDetail();
  }, [fetchCaseDetail]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [detail?.messages]);

  const toggleInvestigation = (msgId: string) => {
    setExpandedInvestigations((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const sendMessage = async (text: string, requestId: string) => {
    text = text.trim();
    if (!text || sending) return;

    const optimisticId = `temp-${requestId}`;
    const tempCustomerMsg: CaseDetail["messages"][number] = {
      id: optimisticId,
      sender_role: "buyer",
      message: text,
      created_at: new Date().toISOString(),
      delivery_state: "sending",
    };
    setDetail((current) =>
      current && !current.messages.some((item) => item.id === optimisticId)
        ? { ...current, messages: [...current.messages, tempCustomerMsg] }
        : current,
    );
    setSending(true);
    setChatError(null);

    try {
      const res = await fetch(`/api/v1/buyer/cases/${caseId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, client_message_id: requestId }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || "Failed to deliver message to agent.");
      }

      await res.json();
      setInputMsg("");
      setRetryRequest(null);
      await fetchCaseDetail();
    } catch (error) {
      setDetail((current) =>
        current
          ? {
              ...current,
              messages: current.messages.filter((item) => item.id !== optimisticId),
            }
          : current,
      );
      setRetryRequest({ text, id: requestId });
      setChatError(
        error instanceof Error
          ? `${error.message} Your message is saved here so you can retry safely.`
          : "Network error delivering message. Your message is saved here so you can retry safely.",
      );
    } finally {
      setSending(false);
    }
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    const text = inputMsg.trim();
    if (!text || sending) return;
    const requestId = retryRequest?.text === text ? retryRequest.id : crypto.randomUUID();
    void sendMessage(text, requestId);
  };

  if (loading) {
    return (
      <div className="py-24 text-center space-y-4">
        <div className="w-8 h-8 border-2 border-foreground border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
          Connecting to Autonomous Resolution Room...
        </p>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="py-24 text-center space-y-4">
        <p className="text-sm font-mono text-muted-foreground">Case not found or access denied.</p>
        <Link
          href="/buyer/cases"
          className="inline-flex h-9 px-5 rounded-full border border-border text-xs font-mono text-foreground hover:bg-foreground/[0.04]"
        >
          Back to Cases
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto flex flex-col h-[calc(100vh-8rem)]">
      {/* Room Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4 shrink-0">
        <div className="flex items-center gap-3">
          <Link
            href="/buyer/cases"
            className="w-8 h-8 rounded-full border border-border flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Back to Cases"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-display text-2xl tracking-tight text-foreground">
                {detail.case.seller_name} Resolution Agent
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-border bg-foreground/[0.03]">
                {detail.case.case_number}
              </span>
            </div>
            <span className="text-xs font-mono text-muted-foreground">
              Order: {detail.order.order_number} &bull; Category: {detail.case.issue_category}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {detail.case.status === "resolved" ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Resolved</span>
            </span>
          ) : detail.case.status === "rejected" ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono border border-destructive/30 bg-destructive/10 text-destructive">
              <XCircle className="w-3.5 h-3.5" />
              <span>Not Eligible</span>
            </span>
          ) : detail.case.status === "pending_approval" ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono border border-amber-500/30 bg-amber-500/10 text-amber-400">
              <Clock className="w-3.5 h-3.5" />
              <span>Needs Approval</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono border border-blue-500/30 bg-blue-500/10 text-blue-400">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
              <span>Investigating</span>
            </span>
          )}
        </div>
      </div>

      {/* Order Context Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 rounded-md border border-border bg-card/40 backdrop-blur text-xs font-mono shrink-0">
        <div>
          <span className="text-muted-foreground block text-[10px] uppercase">Amount</span>
          <span className="text-foreground font-medium">
            {detail.order.currency} {detail.order.total_amount.toFixed(2)}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[10px] uppercase">Courier Partner</span>
          <span className="text-foreground">{detail.order.carrier || "Delhivery"}</span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[10px] uppercase">Tracking AWB</span>
          <span className="text-foreground truncate block">
            {detail.order.tracking_number || "Not assigned"}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground block text-[10px] uppercase">Delivery Date</span>
          <span className="text-foreground">
            {detail.order.delivery_date
              ? new Date(detail.order.delivery_date).toLocaleDateString()
              : "In Transit"}
          </span>
        </div>
      </div>

      {/* Message Timeline */}
      <div
        className="flex-1 min-h-0 overflow-y-auto space-y-4 pr-2"
        aria-live="polite"
        aria-busy={sending}
      >
        {detail.messages.map((msg) => {
          const isBuyer = msg.sender_role === "buyer";
          const isExpanded = expandedInvestigations[msg.id];

          return (
            <div
              key={msg.id}
              className={`flex gap-3 text-xs font-mono ${
                isBuyer ? "justify-end" : "justify-start"
              }`}
            >
              {!isBuyer && (
                <div className="w-8 h-8 rounded-full border border-border bg-foreground/[0.04] flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 text-emerald-400" />
                </div>
              )}

              <div
                className={`max-w-xl rounded-lg p-4 space-y-3 ${
                  isBuyer
                    ? "bg-secondary text-secondary-foreground"
                    : "bg-card border border-border text-foreground"
                }`}
              >
                <div className="flex items-center justify-between gap-3 text-[10px] text-muted-foreground border-b border-border/40 pb-2">
                  <span className="font-bold uppercase">
                    {isBuyer ? "You (Buyer)" : "SellerResolve Autonomous Agent"}
                  </span>
                  <span>
                    {new Date(msg.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>

                <p className="leading-relaxed whitespace-pre-wrap">{msg.message}</p>
                {msg.delivery_state === "sending" && (
                  <p className="text-[10px] text-muted-foreground">Sending message...</p>
                )}

                {/* Decision Badge */}
                {msg.decision_badge && (
                  <div className="pt-1">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[10px] border font-bold ${
                        msg.decision_badge === "executed"
                          ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                          : msg.decision_badge === "needs_approval"
                          ? "border-amber-500/40 bg-amber-500/10 text-amber-300"
                          : "border-destructive/40 bg-destructive/10 text-destructive"
                      }`}
                    >
                      <span>Decision: {msg.decision_badge.replace(/_/g, " ").toUpperCase()}</span>
                    </span>
                  </div>
                )}

                {/* Collapsible Tool Call Drawer */}
                {msg.tool_calls && msg.tool_calls.length > 0 && (
                  <div className="pt-2 border-t border-border/50">
                    <button
                      type="button"
                      onClick={() => toggleInvestigation(msg.id)}
                      className="w-full flex items-center justify-between text-[11px] text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <span>
                        Investigation ({msg.tool_calls.length} deterministic tool call
                        {msg.tool_calls.length > 1 ? "s" : ""})
                      </span>
                      {isExpanded ? (
                        <ChevronUp className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5" />
                      )}
                    </button>

                    {isExpanded && (
                      <div className="mt-2 space-y-2 pt-1">
                        {msg.tool_calls.map((tc, idx) => (
                          <div
                            key={idx}
                            className="p-2.5 rounded bg-background border border-border text-[10px] font-mono space-y-1"
                          >
                            <div className="flex items-center justify-between text-emerald-400">
                              <span className="font-bold">{tc.tool_name}</span>
                              <span className="text-muted-foreground">
                                {tc.timestamp?.slice(11, 19)}
                              </span>
                            </div>
                            <div className="text-muted-foreground">
                              Outcome: <span className="text-foreground">{tc.outcome}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {isBuyer && (
                <div className="w-8 h-8 rounded-full border border-border bg-foreground/[0.04] flex items-center justify-center shrink-0">
                  <User className="w-4 h-4 text-foreground" />
                </div>
              )}
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Customer Turn Input Bar */}
      <div className="shrink-0 pt-2 border-t border-border">
        {sending && (
          <p className="mb-2 text-[11px] font-mono text-muted-foreground" role="status">
            Agent is reviewing your message...
          </p>
        )}
        {chatError && (
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-destructive" role="alert">
            <span>{chatError}</span>
            {retryRequest && (
              <button
                type="button"
                onClick={() => void sendMessage(retryRequest.text, retryRequest.id)}
                disabled={sending}
                className="underline underline-offset-2 disabled:opacity-50"
              >
                Retry
              </button>
            )}
          </div>
        )}
        <form onSubmit={handleSendMessage} className="flex items-end gap-2">
          <textarea
            rows={2}
            placeholder="Reply to agent or provide additional details..."
            value={inputMsg}
            onChange={(e) => setInputMsg(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                e.currentTarget.form?.requestSubmit();
              }
            }}
            disabled={sending}
            aria-label="Message the support agent"
            className="min-h-11 flex-1 resize-none px-4 py-3 bg-background border border-border rounded-2xl text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50 disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={sending || !inputMsg.trim()}
            className="h-11 px-5 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity flex items-center gap-2 disabled:opacity-50"
          >
            <span>{sending ? "Processing..." : "Send"}</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
        <p className="mt-1 text-[10px] font-mono text-muted-foreground">
          Press Enter to send, Shift+Enter for a new line.
        </p>
      </div>
    </div>
  );
}