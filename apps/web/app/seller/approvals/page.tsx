"use client";

import React, { useEffect, useState } from "react";
import {
  CheckSquare,
  AlertTriangle,
  Clock,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Search,
  ArrowRight,
  ShieldCheck,
  Info,
} from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { toast } from "sonner";

interface ApprovalItem {
  id: string;
  case_id: string;
  order_number: string;
  buyer_name: string;
  issue_description: string;
  proposed_action: string;
  proposed_amount: number;
  reason: string;
  requested_at: string;
  status: string;
}

export default function SellerApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"pending" | "all">("pending");
  const [selectedApproval, setSelectedApproval] = useState<ApprovalItem | null>(null);
  const [sellerNotes, setSellerNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchApprovals = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/v1/seller/approvals");
      if (res.ok) {
        const data = await res.json();
        setApprovals(data);
      } else {
        toast.error("Failed to load approval requests");
      }
    } catch {
      toast.error("Network error while loading approvals");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  const handleDecision = async (decision: "approved" | "rejected") => {
    if (!selectedApproval) return;
    try {
      setSubmitting(true);
      const res = await fetch(`/api/v1/seller/approvals/${selectedApproval.id}/decide`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decision,
          seller_notes: sellerNotes.trim() || undefined,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        toast.success(data.message || `Case successfully ${decision}`);
        setSelectedApproval(null);
        setSellerNotes("");
        fetchApprovals();
      } else {
        const err = await res.json();
        toast.error(err.error?.message || `Failed to record ${decision} decision`);
      }
    } catch {
      toast.error("Network error executing decision");
    } finally {
      setSubmitting(false);
    }
  };

  const filteredApprovals = approvals.filter((a) => {
    if (filter === "pending") return a.status === "pending";
    return true;
  });

  const pendingCount = approvals.filter((a) => a.status === "pending").length;

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            <span className="text-[11px] font-mono uppercase text-muted-foreground tracking-wider">
              Human-in-the-Loop Supervision
            </span>
          </div>
          <h1 className="font-display text-3xl md:text-4xl tracking-tight text-foreground">
            Escalations & Approvals
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <div className="inline-flex rounded-full border border-border p-1 bg-card/40">
            <button
              type="button"
              onClick={() => setFilter("pending")}
              className={`px-3 py-1 rounded-full text-xs font-mono transition-colors ${
                filter === "pending"
                  ? "bg-foreground text-background font-medium"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Pending ({pendingCount})
            </button>
            <button
              type="button"
              onClick={() => setFilter("all")}
              className={`px-3 py-1 rounded-full text-xs font-mono transition-colors ${
                filter === "all"
                  ? "bg-foreground text-background font-medium"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              All ({approvals.length})
            </button>
          </div>

          <button
            type="button"
            onClick={fetchApprovals}
            disabled={loading}
            className="h-9 px-3.5 rounded-full border border-border text-xs font-mono text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Explanatory Context Box */}
      <div className="p-4 rounded-md border border-border bg-card/20 flex items-start gap-3">
        <Info className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
        <p className="text-xs text-muted-foreground leading-relaxed">
          The resolution agent operates within strict financial and operational boundaries defined in your{" "}
          <span className="font-mono text-foreground">Policy Configuration</span>. When customer claims exceed automated refund limits, involve suspected transit damage without pre-clearance, or request exceptions, they are queued here for explicit merchant verification.
        </p>
      </div>

      {/* Approvals Table / Empty State */}
      {filteredApprovals.length === 0 ? (
        <EmptyState
          title={filter === "pending" ? "No pending approvals" : "No approvals found"}
          description={
            filter === "pending"
              ? "All active complaints are either resolved autonomously within policy bounds or in active investigation."
              : "No historical human-in-the-loop decisions on record."
          }
          icon={CheckSquare}
        />
      ) : (
        <div className="border border-border rounded-md overflow-hidden bg-card/30">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-foreground/[0.02] border-b border-border text-muted-foreground uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="p-3.5">Order Ref</th>
                  <th className="p-3.5">Customer</th>
                  <th className="p-3.5">Proposed Action</th>
                  <th className="p-3.5">Amount</th>
                  <th className="p-3.5">Escalation Reason</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5 text-right">Review</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredApprovals.map((item) => (
                  <tr key={item.id} className="hover:bg-foreground/[0.02] transition-colors">
                    <td className="p-3.5 font-medium text-foreground">{item.order_number}</td>
                    <td className="p-3.5 text-muted-foreground">{item.buyer_name}</td>
                    <td className="p-3.5 font-medium text-foreground">
                      <span className="capitalize">{item.proposed_action.replace(/_/g, " ")}</span>
                    </td>
                    <td className="p-3.5 font-medium text-foreground">
                      INR {Number(item.proposed_amount ?? 0).toFixed(2)}
                    </td>
                    <td className="p-3.5 text-muted-foreground max-w-xs truncate" title={item.reason}>
                      {item.reason}
                    </td>
                    <td className="p-3.5">
                      {item.status === "pending" ? (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] border border-amber-500/30 bg-amber-500/10 text-amber-300">
                          <span className="w-1 h-1 rounded-full bg-amber-400" />
                          <span>Pending</span>
                        </span>
                      ) : item.status === "approved" ? (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] border border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                          <span className="w-1 h-1 rounded-full bg-emerald-400" />
                          <span>Approved</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] border border-destructive/30 bg-destructive/10 text-destructive">
                          <span className="w-1 h-1 rounded-full bg-destructive" />
                          <span>Rejected</span>
                        </span>
                      )}
                    </td>
                    <td className="p-3.5 text-right">
                      {item.status === "pending" ? (
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedApproval(item);
                            setSellerNotes("");
                          }}
                          className="h-7 px-3 rounded-full bg-foreground text-background text-[11px] font-mono font-medium hover:opacity-90 transition-opacity inline-flex items-center gap-1"
                        >
                          <span>Review</span>
                          <ArrowRight className="w-3 h-3" />
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setSelectedApproval(item)}
                          className="h-7 px-3 rounded-full border border-border text-muted-foreground text-[11px] font-mono hover:text-foreground transition-colors"
                        >
                          Details
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Decision Review Modal */}
      {selectedApproval && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-xl rounded-lg border border-border bg-card p-6 shadow-2xl space-y-6">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div>
                <span className="text-[10px] font-mono uppercase text-muted-foreground">
                  Escalation Review &bull; {selectedApproval.order_number}
                </span>
                <h3 className="font-display text-2xl tracking-tight text-foreground">
                  Resolve Escalated Claim
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedApproval(null)}
                className="text-muted-foreground hover:text-foreground text-sm font-mono"
              >
                Close
              </button>
            </div>

            <div className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-2 gap-3 p-4 rounded-md border border-border bg-background">
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase">Customer</span>
                  <span className="text-foreground font-medium">{selectedApproval.buyer_name}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase">Order Number</span>
                  <span className="text-foreground font-medium">{selectedApproval.order_number}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase">Proposed Action</span>
                  <span className="text-foreground font-medium capitalize">
                    {selectedApproval.proposed_action.replace(/_/g, " ")}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase">Proposed Amount</span>
                  <span className="text-foreground font-medium">
                    INR {Number(selectedApproval.proposed_amount ?? 0).toFixed(2)}
                  </span>
                </div>
              </div>

              <div>
                <span className="text-muted-foreground block text-[10px] uppercase mb-1">Issue Reported</span>
                <p className="p-3 rounded-md border border-border bg-background text-foreground leading-relaxed">
                  {selectedApproval.issue_description}
                </p>
              </div>

              <div>
                <span className="text-muted-foreground block text-[10px] uppercase mb-1">Escalation Trigger Reason</span>
                <div className="p-3 rounded-md border border-amber-500/20 bg-amber-500/5 text-amber-300 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                  <p className="leading-relaxed">{selectedApproval.reason}</p>
                </div>
              </div>

              {selectedApproval.status === "pending" && (
                <div>
                  <label htmlFor="seller-notes" className="text-muted-foreground block text-[10px] uppercase mb-1">
                    Merchant Decision Notes (Optional)
                  </label>
                  <textarea
                    id="seller-notes"
                    value={sellerNotes}
                    onChange={(e) => setSellerNotes(e.target.value)}
                    placeholder="Enter reason or instructions for customer notifications..."
                    rows={3}
                    className="w-full rounded-md border border-border bg-background p-3 text-xs font-mono text-foreground focus:outline-none focus:border-foreground/40"
                  />
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
              {selectedApproval.status === "pending" ? (
                <>
                  <button
                    type="button"
                    onClick={() => handleDecision("rejected")}
                    disabled={submitting}
                    className="h-10 px-5 rounded-full border border-destructive/40 text-destructive text-xs font-mono hover:bg-destructive/10 transition-colors flex items-center gap-2"
                  >
                    <XCircle className="w-4 h-4" />
                    <span>Reject Claim</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDecision("approved")}
                    disabled={submitting}
                    className="h-10 px-6 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Approve Resolution</span>
                  </button>
                </>
              ) : (
                <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>This case has been {selectedApproval.status}.</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
