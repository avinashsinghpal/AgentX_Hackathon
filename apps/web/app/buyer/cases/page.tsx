"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  MessageSquare,
  Clock,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Search,
  ExternalLink,
  Bot,
  User,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Package,
} from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { toast } from "sonner";

interface CaseSummary {
  id: string;
  case_number: string;
  order_number: string;
  seller_id: string;
  seller_name: string;
  issue_category: string;
  status: string;
  decision?: string | null;
  created_at: string;
  resolved_at?: string | null;
}

interface CaseDetail {
  case: CaseSummary;
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
  }>;
}

export default function BuyerCasesPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [expandedInvestigations, setExpandedInvestigations] = useState<Record<string, boolean>>({});

  const fetchCases = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/v1/buyer/cases");
      if (res.ok) {
        const data = await res.json();
        setCases(data);
      } else {
        toast.error("Failed to load resolution cases");
      }
    } catch {
      toast.error("Network error loading cases");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);

  const openCaseDetail = async (caseId: string) => {
    try {
      setSelectedCaseId(caseId);
      setLoadingDetail(true);
      const res = await fetch(`/api/v1/buyer/cases/${caseId}`);
      if (res.ok) {
        const data = await res.json();
        setCaseDetail(data);
      } else {
        toast.error("Failed to load case detail");
      }
    } catch {
      toast.error("Network error loading case detail");
    } finally {
      setLoadingDetail(false);
    }
  };

  const toggleInvestigation = (msgId: string) => {
    setExpandedInvestigations((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-[11px] font-mono uppercase text-muted-foreground tracking-wider">
              Autonomous Support Cases
            </span>
          </div>
          <h1 className="font-display text-3xl md:text-4xl tracking-tight text-foreground">
            Resolution Cases
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchCases}
            disabled={loading}
            className="h-10 px-4 rounded-full border border-border text-xs font-mono text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Reload</span>
          </button>
          <Link
            href="/buyer/complaints/new"
            className="h-10 px-5 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
          >
            <span>File New Claim</span>
          </Link>
        </div>
      </div>

      {/* Cases List */}
      {cases.length === 0 ? (
        <EmptyState
          title="No resolution cases on record"
          description="If you experience delivery delays, transit damage, or wish to request a return, you can raise a complaint directly with the seller resolution agent."
          actionLabel="File a Complaint"
          onAction={() => window.location.assign("/buyer/complaints/new")}
          icon={MessageSquare}
        />
      ) : (
        <div className="border border-border rounded-md overflow-hidden bg-card/30">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-foreground/[0.02] border-b border-border text-muted-foreground uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="p-3.5">Case Ref</th>
                  <th className="p-3.5">Order Ref</th>
                  <th className="p-3.5">Merchant</th>
                  <th className="p-3.5">Issue Type</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5">Opened</th>
                  <th className="p-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {cases.map((c) => (
                  <tr key={c.id} className="hover:bg-foreground/[0.02] transition-colors">
                    <td className="p-3.5 font-bold text-foreground">{c.case_number}</td>
                    <td className="p-3.5 text-muted-foreground">{c.order_number}</td>
                    <td className="p-3.5 text-muted-foreground">{c.seller_name}</td>
                    <td className="p-3.5 font-medium text-foreground capitalize">
                      {c.issue_category.replace(/_/g, " ")}
                    </td>
                    <td className="p-3.5">
                      {c.status === "resolved" ? (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Resolved</span>
                        </span>
                      ) : c.status === "rejected" ? (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] border border-destructive/30 bg-destructive/10 text-destructive">
                          <XCircle className="w-3 h-3" />
                          <span>Not Eligible</span>
                        </span>
                      ) : c.status === "pending_approval" ? (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] border border-amber-500/30 bg-amber-500/10 text-amber-400">
                          <Clock className="w-3 h-3" />
                          <span>Needs Approval</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] border border-blue-500/30 bg-blue-500/10 text-blue-400">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                          <span>Investigating</span>
                        </span>
                      )}
                    </td>
                    <td className="p-3.5 text-muted-foreground">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-3.5 text-right">
                      <button
                        type="button"
                        onClick={() => openCaseDetail(c.id)}
                        className="h-7 px-3 rounded-full border border-border text-muted-foreground text-[11px] font-mono hover:text-foreground hover:border-foreground/40 transition-colors"
                      >
                        Open Room
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Case Investigation & Chat Room Modal */}
      {selectedCaseId && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-3xl rounded-lg border border-border bg-card p-6 shadow-2xl space-y-6 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-border pb-4 shrink-0">
              <div>
                <span className="text-[10px] font-mono uppercase text-muted-foreground">
                  Resolution Room &bull; {caseDetail?.case.case_number || "Loading"}
                </span>
                <h3 className="font-display text-2xl tracking-tight text-foreground">
                  {caseDetail?.case.seller_name} Support Agent
                </h3>
              </div>
              <button
                type="button"
                onClick={() => {
                  setSelectedCaseId(null);
                  setCaseDetail(null);
                }}
                className="text-muted-foreground hover:text-foreground text-sm font-mono"
              >
                Close
              </button>
            </div>

            {loadingDetail || !caseDetail ? (
              <div className="py-16 text-center text-xs font-mono text-muted-foreground">
                Retrieving case investigation records...
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto space-y-6 pr-2">
                {/* Order Summary Strip */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 rounded border border-border bg-background text-xs font-mono">
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">Order</span>
                    <span className="text-foreground font-medium">{caseDetail.order.order_number}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">Amount</span>
                    <span className="text-foreground">
                      {caseDetail.order.currency} {Number(caseDetail.order.total_amount ?? 0).toFixed(2)}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">Issue</span>
                    <span className="text-foreground capitalize">
                      {caseDetail.case.issue_category.replace(/_/g, " ")}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">Case Status</span>
                    <span className="text-foreground font-medium capitalize">
                      {caseDetail.case.status.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>

                {/* Evidence Attachments */}
                {caseDetail.evidence_urls.length > 0 && (
                  <div className="p-3 rounded border border-border bg-background/50 text-xs font-mono">
                    <span className="text-[10px] uppercase text-muted-foreground block mb-1">
                      Submitted Photo Evidence
                    </span>
                    <div className="flex gap-2">
                      {caseDetail.evidence_urls.map((id, idx) => (
                        <span
                          key={id}
                          className="px-2.5 py-1 rounded border border-border bg-foreground/[0.02] text-[11px]"
                        >
                          Evidence File #{idx + 1}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Live Message & Investigation Stream */}
                <div className="space-y-4 pt-2">
                  <span className="text-[10px] font-mono uppercase text-muted-foreground block">
                    Interaction History
                  </span>

                  {caseDetail.messages.map((msg) => {
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
                          className={`max-w-lg rounded-lg p-4 space-y-3 ${
                            isBuyer
                              ? "bg-secondary text-secondary-foreground"
                              : "bg-card border border-border text-foreground"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-3 text-[10px] text-muted-foreground border-b border-border/40 pb-2">
                            <span className="font-bold uppercase">
                              {isBuyer ? "You (Buyer)" : "SellerResolve Autonomous Agent"}
                            </span>
                            <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                          </div>

                          <p className="leading-relaxed whitespace-pre-wrap">{msg.message}</p>

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

                          {/* Investigation Drawer for Agent turns */}
                          {msg.tool_calls && msg.tool_calls.length > 0 && (
                            <div className="pt-2 border-t border-border/50">
                              <button
                                type="button"
                                onClick={() => toggleInvestigation(msg.id)}
                                className="w-full flex items-center justify-between text-[11px] text-muted-foreground hover:text-foreground transition-colors"
                              >
                                <span>Investigation ({msg.tool_calls.length} tool call{msg.tool_calls.length > 1 ? "s" : ""})</span>
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
                                        <span className="text-muted-foreground">{tc.timestamp?.slice(11, 19)}</span>
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
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
