"use client";

import React, { useEffect, useState } from "react";
import {
  ScrollText,
  ShieldCheck,
  ShieldAlert,
  Download,
  RefreshCw,
  Search,
  Filter,
  Copy,
  Check,
  ExternalLink,
  Code,
  CheckCircle2,
} from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { toast } from "sonner";

interface AuditEntry {
  id: string;
  sequence: number;
  timestamp: string;
  action_type: string;
  actor_type: string;
  actor_id: string | null;
  case_id: string | null;
  previous_hash: string;
  entry_hash: string;
  payload: Record<string, unknown>;
}

interface VerificationResult {
  is_valid: boolean;
  total_entries: number;
  broken_sequence: number | null;
  genesis_hash: string;
  latest_hash: string;
}

export default function SellerAuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [verification, setVerification] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [actionFilter, setActionFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const fetchAuditData = async () => {
    try {
      setLoading(true);
      const [entriesRes, verifyRes] = await Promise.all([
        fetch("/api/v1/seller/audit"),
        fetch("/api/v1/seller/audit/verify"),
      ]);

      if (entriesRes.ok) {
        const data = await entriesRes.json();
        setEntries(data);
      }
      if (verifyRes.ok) {
        const vData = await verifyRes.json();
        setVerification(vData);
      }
    } catch {
      toast.error("Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditData();
  }, []);

  const handleVerifyChain = async () => {
    try {
      setVerifying(true);
      const res = await fetch("/api/v1/seller/audit/verify");
      if (res.ok) {
        const data = await res.json();
        setVerification(data);
        if (data.is_valid) {
          toast.success(
            `Cryptographic audit chain verified. ${data.total_entries} blocks checked with zero tamper flags.`
          );
        } else {
          toast.error(`Chain broken at sequence ${data.broken_sequence}`);
        }
      } else {
        toast.error("Failed to verify chain");
      }
    } catch {
      toast.error("Network error verifying chain");
    } finally {
      setVerifying(false);
    }
  };

  const handleExportCsv = () => {
    window.open("/api/v1/seller/audit/export", "_blank");
    toast.success("Audit trail export initiated");
  };

  const copyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    toast.success("Hash copied to clipboard");
    setTimeout(() => setCopiedHash(null), 2000);
  };

  // Filter entries
  const filteredEntries = entries.filter((e) => {
    if (actionFilter !== "all" && !e.action_type.toLowerCase().includes(actionFilter.toLowerCase())) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchAction = e.action_type.toLowerCase().includes(q);
      const matchCase = e.case_id?.toLowerCase().includes(q);
      const matchHash = e.entry_hash.toLowerCase().includes(q);
      return matchAction || matchCase || matchHash;
    }
    return true;
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-[11px] font-mono uppercase text-muted-foreground tracking-wider">
              Cryptographic Immutability
            </span>
          </div>
          <h1 className="font-display text-3xl md:text-4xl tracking-tight text-foreground">
            Audit Trail & Chain Verification
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleVerifyChain}
            disabled={verifying}
            className="h-10 px-4 rounded-full border border-border text-xs font-mono text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2"
          >
            <ShieldCheck className={`w-3.5 h-3.5 text-emerald-400 ${verifying ? "animate-spin" : ""}`} />
            <span>{verifying ? "Verifying..." : "Verify Chain"}</span>
          </button>
          <button
            type="button"
            onClick={handleExportCsv}
            className="h-10 px-5 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Cryptographic Chain Integrity Status Card */}
      {verification && (
        <div
          className={`p-5 rounded-md border flex flex-col md:flex-row md:items-center justify-between gap-4 ${
            verification.is_valid
              ? "border-emerald-500/30 bg-emerald-500/5 text-foreground"
              : "border-destructive/30 bg-destructive/10 text-foreground"
          }`}
        >
          <div className="flex items-start md:items-center gap-3.5">
            {verification.is_valid ? (
              <div className="w-9 h-9 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center shrink-0">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
              </div>
            ) : (
              <div className="w-9 h-9 rounded-full bg-destructive/20 border border-destructive/40 flex items-center justify-center shrink-0">
                <ShieldAlert className="w-5 h-5 text-destructive" />
              </div>
            )}
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-medium uppercase tracking-wider">
                  {verification.is_valid
                    ? "Cryptographic Hash Chain Verified"
                    : "Integrity Compromised"}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full border border-border bg-foreground/[0.04]">
                  {verification.total_entries} Blocks
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {verification.is_valid
                  ? "Every autonomous tool invocation, policy change, and payout is linked via SHA-256 prev_hash signatures."
                  : `Discrepancy detected at entry #${verification.broken_sequence}. Check logs immediately.`}
              </p>
            </div>
          </div>

          <div className="text-xs font-mono bg-background/60 p-2.5 rounded border border-border flex items-center gap-2 shrink-0">
            <span className="text-muted-foreground text-[10px] uppercase">Tip Hash:</span>
            <span className="text-foreground max-w-[140px] truncate">
              {verification.latest_hash}
            </span>
            <button
              type="button"
              onClick={() => copyHash(verification.latest_hash)}
              className="text-muted-foreground hover:text-foreground"
              aria-label="Copy latest block hash"
            >
              {copiedHash === verification.latest_hash ? (
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-muted-foreground absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Search action type, case ID, or SHA-256 hash..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-10 pl-10 pr-4 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
          />
        </div>

        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
        >
          <option value="all">All Action Types</option>
          <option value="policy">Policy Events</option>
          <option value="operations">Operations Events</option>
          <option value="case">Case Inquiries</option>
          <option value="agent">Agent Tool Invocations</option>
          <option value="approval">Human Approvals</option>
          <option value="order">Order Seeding</option>
        </select>
      </div>

      {/* Audit Entries Table */}
      {filteredEntries.length === 0 ? (
        <EmptyState
          title="No audit entries found"
          description="Actions performed by merchant administrators or the resolution agent will automatically generate immutable hash-chained records here."
          icon={ScrollText}
        />
      ) : (
        <div className="border border-border rounded-md overflow-hidden bg-card/30">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-foreground/[0.02] border-b border-border text-muted-foreground uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="p-3.5">Seq #</th>
                  <th className="p-3.5">Timestamp (UTC)</th>
                  <th className="p-3.5">Action</th>
                  <th className="p-3.5">Actor</th>
                  <th className="p-3.5">Case ID</th>
                  <th className="p-3.5">Entry Hash</th>
                  <th className="p-3.5 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredEntries.map((e) => (
                  <tr key={e.id} className="hover:bg-foreground/[0.02] transition-colors">
                    <td className="p-3.5 font-bold text-foreground">#{e.sequence}</td>
                    <td className="p-3.5 text-muted-foreground whitespace-nowrap">
                      {e.timestamp ? new Date(e.timestamp).toLocaleString() : "-"}
                    </td>
                    <td className="p-3.5 font-medium text-foreground">
                      <span className="px-2 py-0.5 rounded border border-border bg-foreground/[0.03]">
                        {e.action_type}
                      </span>
                    </td>
                    <td className="p-3.5">
                      <span className="capitalize text-muted-foreground">{e.actor_type}</span>
                    </td>
                    <td className="p-3.5 text-muted-foreground">
                      {e.case_id ? e.case_id.slice(0, 8) + "..." : "-"}
                    </td>
                    <td className="p-3.5 text-muted-foreground font-mono">
                      {e.entry_hash ? e.entry_hash.slice(0, 12) + "..." : "-"}
                    </td>
                    <td className="p-3.5 text-right">
                      <button
                        type="button"
                        onClick={() => setSelectedEntry(e)}
                        className="h-7 px-3 rounded-full border border-border text-muted-foreground text-[11px] font-mono hover:text-foreground hover:border-foreground/40 transition-colors"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Inspect Entry Modal */}
      {selectedEntry && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl rounded-lg border border-border bg-card p-6 shadow-2xl space-y-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div>
                <span className="text-[10px] font-mono uppercase text-muted-foreground">
                  Block #{selectedEntry.sequence} &bull; Cryptographic Record
                </span>
                <h3 className="font-display text-2xl tracking-tight text-foreground">
                  {selectedEntry.action_type}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedEntry(null)}
                className="text-muted-foreground hover:text-foreground text-sm font-mono"
              >
                Close
              </button>
            </div>

            <div className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-2 gap-3 p-4 rounded-md border border-border bg-background">
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase">Actor</span>
                  <span className="text-foreground capitalize">{selectedEntry.actor_type}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase">Timestamp</span>
                  <span className="text-foreground">{selectedEntry.timestamp}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase">Case ID</span>
                  <span className="text-foreground">{selectedEntry.case_id || "None (Store Level)"}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase">Sequence</span>
                  <span className="text-foreground font-bold">#{selectedEntry.sequence}</span>
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-muted-foreground block text-[10px] uppercase">Previous Block Hash</span>
                <div className="p-2.5 rounded bg-background border border-border text-[11px] font-mono break-all text-muted-foreground">
                  {selectedEntry.previous_hash}
                </div>

                <span className="text-muted-foreground block text-[10px] uppercase pt-1">Current Entry SHA-256</span>
                <div className="p-2.5 rounded bg-background border border-border text-[11px] font-mono break-all text-foreground flex items-center justify-between gap-2">
                  <span>{selectedEntry.entry_hash}</span>
                  <button
                    type="button"
                    onClick={() => copyHash(selectedEntry.entry_hash)}
                    className="text-muted-foreground hover:text-foreground shrink-0"
                  >
                    {copiedHash === selectedEntry.entry_hash ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>

              <div>
                <span className="text-muted-foreground block text-[10px] uppercase mb-1">
                  Event Payload (JSON)
                </span>
                <pre className="p-4 rounded-md border border-border bg-background text-[11px] font-mono text-foreground overflow-x-auto leading-relaxed">
                  {JSON.stringify(selectedEntry.payload, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
