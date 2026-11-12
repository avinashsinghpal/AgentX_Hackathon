"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  MessageSquare,
  Clock,
  CheckCircle2,
  XCircle,
  RefreshCw,
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

export default function BuyerCasesPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);

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
                      <Link
                        href={`/buyer/cases/${c.id}`}
                        className="h-7 px-3 rounded-full border border-border text-muted-foreground text-[11px] font-mono hover:text-foreground hover:border-foreground/40 transition-colors"
                      >
                        Open Room
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
}
