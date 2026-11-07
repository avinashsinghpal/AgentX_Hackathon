"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Package,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRight,
  Database,
  RefreshCw,
  ExternalLink,
  ShieldAlert,
} from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { toast } from "sonner";

interface SellerMetrics {
  total_orders: number;
  open_cases: number;
  pending_approvals: number;
  resolved_cases: number;
  rejected_cases: number;
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

export default function SellerDashboardPage() {
  const [metrics, setMetrics] = useState<SellerMetrics | null>(null);
  const [orders, setOrders] = useState<OrderItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [metricsRes, ordersRes] = await Promise.all([
        fetch("/api/v1/seller/metrics"),
        fetch("/api/v1/seller/orders"),
      ]);

      if (metricsRes.ok) {
        const data = await metricsRes.json();
        setMetrics(data);
      }
      if (ordersRes.ok) {
        const data = await ordersRes.json();
        setOrders(data);
      }
    } catch {
      toast.error("Failed to load dashboard metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleSeedDemoOrders = async () => {
    try {
      setSeeding(true);
      const res = await fetch("/api/v1/seller/orders/demo-seed", {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(data.message || "4 test scenario orders created");
        fetchDashboardData();
      } else {
        toast.error("Failed to seed demo orders");
      }
    } catch {
      toast.error("Network error while seeding orders");
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header with Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-[11px] font-mono uppercase text-muted-foreground tracking-wider">
              Autonomous Merchant Operations
            </span>
          </div>
          <h1 className="font-display text-3xl md:text-4xl tracking-tight text-foreground">
            Resolution Overview
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchDashboardData}
            disabled={loading}
            className="h-10 px-4 rounded-full border border-border text-xs font-mono text-muted-foreground hover:text-foreground hover:border-foreground/40 transition-colors flex items-center gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
          <button
            type="button"
            onClick={handleSeedDemoOrders}
            disabled={seeding}
            className="h-10 px-5 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
          >
            <Database className="w-3.5 h-3.5" />
            <span>{seeding ? "Seeding..." : "Seed Demo Orders"}</span>
          </button>
        </div>
      </div>

      {/* Pending Approvals Urgent Alert Banner */}
      {metrics && metrics.pending_approvals > 0 && (
        <div className="p-4 rounded-md border border-amber-500/30 bg-amber-500/10 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0" />
            <div>
              <p className="text-sm font-medium text-foreground">
                {metrics.pending_approvals} resolution{metrics.pending_approvals > 1 ? "s" : ""} require your human approval
              </p>
              <p className="text-xs text-muted-foreground font-mono">
                Claims exceed automated policy threshold or require manual review.
              </p>
            </div>
          </div>
          <Link
            href="/seller/approvals"
            className="h-8 px-4 rounded-full bg-amber-400 text-black text-xs font-mono font-medium hover:bg-amber-300 transition-colors flex items-center gap-1.5 shrink-0"
          >
            <span>Review Queue</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* Real Computed Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Orders */}
        <div className="p-5 rounded-md border border-border bg-card/40 backdrop-blur space-y-3">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-mono uppercase tracking-wider">Total Orders</span>
            <Package className="w-4 h-4" />
          </div>
          <div className="font-display text-3xl tracking-tight text-foreground">
            {loading ? "-" : metrics?.total_orders ?? 0}
          </div>
          <div className="text-[11px] font-mono text-muted-foreground">
            Synced from store connector
          </div>
        </div>

        {/* Active Cases */}
        <div className="p-5 rounded-md border border-border bg-card/40 backdrop-blur space-y-3">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-mono uppercase tracking-wider">Active Inquiries</span>
            <Clock className="w-4 h-4" />
          </div>
          <div className="font-display text-3xl tracking-tight text-foreground">
            {loading ? "-" : metrics?.open_cases ?? 0}
          </div>
          <div className="text-[11px] font-mono text-muted-foreground">
            Autonomous investigations in progress
          </div>
        </div>

        {/* Pending Approvals */}
        <div className="p-5 rounded-md border border-border bg-card/40 backdrop-blur space-y-3">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-mono uppercase tracking-wider">Pending Approvals</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="font-display text-3xl tracking-tight text-foreground">
            {loading ? "-" : metrics?.pending_approvals ?? 0}
          </div>
          <div className="text-[11px] font-mono text-muted-foreground">
            Escalated to human supervisor
          </div>
        </div>

        {/* Resolved Cases */}
        <div className="p-5 rounded-md border border-border bg-card/40 backdrop-blur space-y-3">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-mono uppercase tracking-wider">Autonomous Resolves</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="font-display text-3xl tracking-tight text-foreground">
            {loading ? "-" : metrics?.resolved_cases ?? 0}
          </div>
          <div className="text-[11px] font-mono text-muted-foreground">
            Verified without human escalation
          </div>
        </div>
      </div>

      {/* Quick Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          href="/seller/policies"
          className="p-5 rounded-md border border-border bg-card/20 hover:bg-card/60 transition-colors group space-y-2"
        >
          <div className="flex items-center justify-between text-foreground">
            <span className="font-display text-lg tracking-tight">Policy Manager</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </div>
          <p className="text-xs text-muted-foreground">
            Configure return windows, automated refund caps, and proof-of-damage thresholds.
          </p>
        </Link>

        <Link
          href="/seller/approvals"
          className="p-5 rounded-md border border-border bg-card/20 hover:bg-card/60 transition-colors group space-y-2"
        >
          <div className="flex items-center justify-between text-foreground">
            <span className="font-display text-lg tracking-tight">Approvals Queue</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </div>
          <p className="text-xs text-muted-foreground">
            Review high-risk claims, inspected evidence photos, and approve or reject payouts.
          </p>
        </Link>

        <Link
          href="/seller/audit"
          className="p-5 rounded-md border border-border bg-card/20 hover:bg-card/60 transition-colors group space-y-2"
        >
          <div className="flex items-center justify-between text-foreground">
            <span className="font-display text-lg tracking-tight">Audit Trail</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </div>
          <p className="text-xs text-muted-foreground">
            Mathematically verify SHA-256 hash chains of every agent investigation and action.
          </p>
        </Link>
      </div>

      {/* Orders List Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-display text-xl tracking-tight text-foreground">Store Orders</h2>
            <p className="text-xs font-mono text-muted-foreground">
              Mock or live synchronized orders available for customer complaints
            </p>
          </div>
          <Link
            href="/seller/customers"
            className="text-xs font-mono text-muted-foreground hover:text-foreground flex items-center gap-1.5 transition-colors"
          >
            <span>Manage Customers</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>

        {orders.length === 0 ? (
          <EmptyState
            title="No orders yet"
            description="Seed standard test scenario orders or connect your external commerce catalog to start testing resolution flows."
            actionLabel="Seed 4 Test Scenario Orders"
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
                    <th className="p-3.5">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {orders.map((o) => (
                    <tr key={o.id} className="hover:bg-foreground/[0.02] transition-colors">
                      <td className="p-3.5 font-medium text-foreground">{o.order_number}</td>
                      <td className="p-3.5 text-muted-foreground">{o.buyer_name}</td>
                      <td className="p-3.5 text-muted-foreground">{o.items_count} item{o.items_count > 1 ? "s" : ""}</td>
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
