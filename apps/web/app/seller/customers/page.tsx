"use client";

import React, { useEffect, useState } from "react";
import {
  Users,
  UserPlus,
  Copy,
  Check,
  RefreshCw,
  Package,
  Database,
  Calendar,
  Clock,
  ArrowRight,
  ShieldCheck,
  ExternalLink,
} from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { toast } from "sonner";

interface InviteItem {
  id: string;
  customer_email: string;
  invite_token: string;
  status: "pending" | "accepted" | "expired";
  expires_at: string;
  created_at: string;
  accepted_at: string | null;
}

interface OrderItem {
  id: string;
  order_number: string;
  buyer_name: string;
  total_amount: number;
  currency: string;
  status: string;
  items_count: number;
  created_at: string;
}

export default function SellerCustomersPage() {
  const [invites, setInvites] = useState<InviteItem[]>([]);
  const [orders, setOrders] = useState<OrderItem[]>([]);
  const [customerEmail, setCustomerEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [generatingInvite, setGeneratingInvite] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [invRes, ordRes] = await Promise.all([
        fetch("/api/v1/seller/customers/invites"),
        fetch("/api/v1/seller/orders"),
      ]);

      if (invRes.ok) {
        const data = await invRes.json();
        setInvites(data);
      }
      if (ordRes.ok) {
        const data = await ordRes.json();
        setOrders(data);
      }
    } catch {
      toast.error("Failed to load customer invites and orders");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    const email = customerEmail.trim();
    if (!email) {
      toast.error("Please enter a customer email address");
      return;
    }

    try {
      setGeneratingInvite(true);
      const res = await fetch("/api/v1/seller/customers/invites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_email: email }),
      });

      if (res.ok) {
        const data = await res.json();
        toast.success(`Invite generated for ${email}`);
        setCustomerEmail("");
        fetchData();
        // Copy to clipboard
        const fullLink = `${window.location.origin}/invite/${data.invite_token}`;
        navigator.clipboard.writeText(fullLink);
        setCopiedToken(data.invite_token);
        setTimeout(() => setCopiedToken(null), 3000);
      } else {
        const err = await res.json();
        toast.error(err.error?.message || "Failed to create invite");
      }
    } catch {
      toast.error("Network error creating invite");
    } finally {
      setGeneratingInvite(false);
    }
  };

  const copyInviteLink = (token: string) => {
    const fullLink = `${window.location.origin}/invite/${token}`;
    navigator.clipboard.writeText(fullLink);
    setCopiedToken(token);
    toast.success("Invite link copied to clipboard");
    setTimeout(() => setCopiedToken(null), 2500);
  };

  const handleSeedDemoOrders = async () => {
    try {
      setSeeding(true);
      const res = await fetch("/api/v1/seller/orders/demo-seed", {
        method: "POST",
      });

      if (res.ok) {
        const data = await res.json();
        toast.success(data.message || "4 test scenario orders created");
        fetchData();
      } else {
        toast.error("Failed to seed orders");
      }
    } catch {
      toast.error("Network error while seeding orders");
    } finally {
      setSeeding(false);
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
              Customer Onboarding & Order Scenarios
            </span>
          </div>
          <h1 className="font-display text-3xl md:text-4xl tracking-tight text-foreground">
            Customers & Demo Orders
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchData}
            disabled={loading}
            className="h-10 px-4 rounded-full border border-border text-xs font-mono text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Reload</span>
          </button>
          <button
            type="button"
            onClick={handleSeedDemoOrders}
            disabled={seeding}
            className="h-10 px-5 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
          >
            <Database className="w-3.5 h-3.5" />
            <span>{seeding ? "Generating..." : "Seed 4 Demo Orders"}</span>
          </button>
        </div>
      </div>

      {/* Customer Invite Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Create Invite Form */}
        <div className="p-6 rounded-md border border-border bg-card/20 space-y-4">
          <div className="border-b border-border pb-3">
            <h2 className="font-display text-xl tracking-tight text-foreground">
              Invite Customer
            </h2>
            <p className="text-xs font-mono text-muted-foreground">
              Generate a secure 7-day single-use invitation link for a buyer.
            </p>
          </div>

          <form onSubmit={handleCreateInvite} className="space-y-4">
            <div>
              <label className="text-xs font-mono uppercase text-muted-foreground block mb-1.5">
                Customer Email Address
              </label>
              <input
                type="email"
                required
                placeholder="customer@example.com"
                value={customerEmail}
                onChange={(e) => setCustomerEmail(e.target.value)}
                className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
              />
            </div>

            <button
              type="submit"
              disabled={generatingInvite}
              className="w-full h-10 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
            >
              <UserPlus className="w-3.5 h-3.5" />
              <span>{generatingInvite ? "Generating..." : "Generate Invite Link"}</span>
            </button>
          </form>

          <div className="pt-2 text-[11px] font-mono text-muted-foreground space-y-1">
            <p>Links grant access to view orders and file claims with the resolution agent.</p>
          </div>
        </div>

        {/* Invites List */}
        <div className="lg:col-span-2 space-y-3">
          <h2 className="font-display text-xl tracking-tight text-foreground">
            Customer Invitations ({invites.length})
          </h2>

          {invites.length === 0 ? (
            <EmptyState
              title="No customer invitations yet"
              description="Generate an invitation link to onboard buyers into your autonomous resolution portal."
              icon={Users}
            />
          ) : (
            <div className="border border-border rounded-md overflow-hidden bg-card/30">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-foreground/[0.02] border-b border-border text-muted-foreground uppercase text-[10px] tracking-wider">
                    <tr>
                      <th className="p-3.5">Customer Email</th>
                      <th className="p-3.5">Token</th>
                      <th className="p-3.5">Status</th>
                      <th className="p-3.5">Expires</th>
                      <th className="p-3.5 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {invites.map((inv) => (
                      <tr key={inv.id} className="hover:bg-foreground/[0.02] transition-colors">
                        <td className="p-3.5 font-medium text-foreground">{inv.customer_email}</td>
                        <td className="p-3.5 text-muted-foreground font-mono">
                          {inv.invite_token ? inv.invite_token.slice(0, 8) + "..." : "-"}
                        </td>
                        <td className="p-3.5">
                          {inv.status === "accepted" ? (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] border border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                              <span className="w-1 h-1 rounded-full bg-emerald-400" />
                              <span>Accepted</span>
                            </span>
                          ) : inv.status === "expired" ? (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] border border-border text-muted-foreground">
                              <span>Expired</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] border border-blue-500/30 bg-blue-500/10 text-blue-300">
                              <span className="w-1 h-1 rounded-full bg-blue-400" />
                              <span>Pending</span>
                            </span>
                          )}
                        </td>
                        <td className="p-3.5 text-muted-foreground">
                          {new Date(inv.expires_at).toLocaleDateString()}
                        </td>
                        <td className="p-3.5 text-right">
                          <button
                            type="button"
                            onClick={() => copyInviteLink(inv.invite_token)}
                            className="h-7 px-3 rounded-full border border-border text-muted-foreground text-[11px] font-mono hover:text-foreground transition-colors inline-flex items-center gap-1.5"
                          >
                            {copiedToken === inv.invite_token ? (
                              <>
                                <Check className="w-3 h-3 text-emerald-400" />
                                <span className="text-emerald-400">Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3 h-3" />
                                <span>Copy Link</span>
                              </>
                            )}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Demo Test Scenarios Information Box */}
      <div className="p-6 rounded-md border border-border bg-card/20 space-y-4">
        <div>
          <h2 className="font-display text-xl tracking-tight text-foreground">
            Standard Deterministic Test Scenarios
          </h2>
          <p className="text-xs font-mono text-muted-foreground">
            These four orders are pre-configured to rigorously test every deterministic rule in the AgentX specification:
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
          <div className="p-4 rounded border border-border bg-background space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="font-bold text-foreground">ORD-1001</span>
              <span className="text-emerald-400">Eligible</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Delivered 2 days ago. Value INR 1,299. Standard return within 7-day policy. Agent issues reverse shipping label autonomously.
            </p>
          </div>

          <div className="p-4 rounded border border-border bg-background space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="font-bold text-foreground">ORD-1002</span>
              <span className="text-destructive">Expired</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Delivered 28 days ago. Value INR 2,499. Exceeds 7-day return window. Agent politely refuses and cites seller return policy rule.
            </p>
          </div>

          <div className="p-4 rounded border border-border bg-background space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="font-bold text-foreground">ORD-1003</span>
              <span className="text-amber-400">High Value</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Delivered 1 day ago. Value INR 8,999. Exceeds INR 2,000 auto-refund threshold. Agent queues case for human merchant 1-click approval.
            </p>
          </div>

          <div className="p-4 rounded border border-border bg-background space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="font-bold text-foreground">ORD-1004</span>
              <span className="text-blue-400">Delayed</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              In transit with Delhivery for 5 days. 3 days past EDD. Proactive monitor triggers and grants automatic INR 150 wallet credit.
            </p>
          </div>
        </div>
      </div>

      {/* Orders Table */}
      <div className="space-y-4">
        <h2 className="font-display text-xl tracking-tight text-foreground">
          Store Orders ({orders.length})
        </h2>

        {orders.length === 0 ? (
          <EmptyState
            title="No orders yet"
            description="Generate the 4 standard test scenario orders to test buyer claims and escalation flows."
            actionLabel="Generate 4 Test Scenario Orders"
            onAction={handleSeedDemoOrders}
            icon={Package}
          />
        ) : (
          <div className="border border-border rounded-md overflow-hidden bg-card/30">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-foreground/[0.02] border-b border-border text-muted-foreground uppercase text-[10px] tracking-wider">
                  <tr>
                    <th className="p-3.5">Order Number</th>
                    <th className="p-3.5">Customer</th>
                    <th className="p-3.5">Items</th>
                    <th className="p-3.5">Total Amount</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {orders.map((o) => (
                    <tr key={o.id} className="hover:bg-foreground/[0.02] transition-colors">
                      <td className="p-3.5 font-medium text-foreground">{o.order_number}</td>
                      <td className="p-3.5 text-muted-foreground">{o.buyer_name}</td>
                      <td className="p-3.5 text-muted-foreground">
                        {o.items_count} item{o.items_count > 1 ? "s" : ""}
                      </td>
                      <td className="p-3.5 text-foreground font-medium">
                        {o.currency} {Number(o.total_amount ?? 0).toFixed(2)}
                      </td>
                      <td className="p-3.5">
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] border border-border bg-foreground/[0.03]">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                          <span className="capitalize">{o.status}</span>
                        </span>
                      </td>
                      <td className="p-3.5 text-muted-foreground">
                        {new Date(o.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
