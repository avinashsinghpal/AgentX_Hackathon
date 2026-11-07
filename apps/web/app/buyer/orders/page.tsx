"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Package,
  Plus,
  RefreshCw,
  Search,
  Truck,
  ExternalLink,
  ArrowRight,
  ShieldAlert,
  CheckCircle2,
  Clock,
  AlertCircle,
} from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { toast } from "sonner";

interface OrderSummary {
  id: string;
  order_number: string;
  seller_id: string;
  seller_name: string;
  order_date: string;
  total_amount: number;
  currency: string;
  payment_method: string;
  payment_status: string;
  order_status: string;
  items_count: number;
  items: Array<{ title: string; quantity: number; total_price: number }>;
  tracking_number?: string | null;
  carrier?: string | null;
  delivery_date?: string | null;
  eligible_for_complaint: boolean;
}

export default function BuyerOrdersPage() {
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [linkingOrder, setLinkingOrder] = useState(false);
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [orderNumberToLink, setOrderNumberToLink] = useState("");

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/v1/buyer/orders");
      if (res.ok) {
        const data = await res.json();
        setOrders(data);
      } else {
        toast.error("Failed to load customer orders");
      }
    } catch {
      toast.error("Network error while loading orders");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, []);

  const handleLinkOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orderNumberToLink.trim()) return;

    try {
      setLinkingOrder(true);
      const res = await fetch("/api/v1/buyer/orders/link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ order_number: orderNumberToLink.trim() }),
      });

      if (res.ok) {
        toast.success(`Order ${orderNumberToLink} linked to your account`);
        setShowLinkModal(false);
        setOrderNumberToLink("");
        fetchOrders();
      } else {
        const err = await res.json();
        toast.error(err.error?.message || "Failed to link order");
      }
    } catch {
      toast.error("Network error while linking order");
    } finally {
      setLinkingOrder(false);
    }
  };

  const filteredOrders = orders.filter((o) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      o.order_number.toLowerCase().includes(q) ||
      o.seller_name.toLowerCase().includes(q) ||
      o.items.some((it) => it.title.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-[11px] font-mono uppercase text-muted-foreground tracking-wider">
              Customer Order History
            </span>
          </div>
          <h1 className="font-display text-3xl md:text-4xl tracking-tight text-foreground">
            My Orders
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchOrders}
            disabled={loading}
            className="h-10 px-4 rounded-full border border-border text-xs font-mono text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Reload</span>
          </button>
          <button
            type="button"
            onClick={() => setShowLinkModal(true)}
            className="h-10 px-5 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Claim Order</span>
          </button>
        </div>
      </div>

      {/* Search Input */}
      <div className="max-w-md relative">
        <Search className="w-4 h-4 text-muted-foreground absolute left-3.5 top-3" />
        <input
          type="text"
          placeholder="Search by order number or merchant store..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full h-10 pl-10 pr-4 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
        />
      </div>

      {/* Orders List / Empty State */}
      {filteredOrders.length === 0 ? (
        <EmptyState
          title="No orders found"
          description={
            searchQuery
              ? `No orders matching '${searchQuery}'.`
              : "You do not have any orders linked to your customer profile yet."
          }
          actionLabel="Claim Order by Number"
          onAction={() => setShowLinkModal(true)}
          icon={Package}
        />
      ) : (
        <div className="space-y-4">
          {filteredOrders.map((o) => (
            <div
              key={o.id}
              className="p-6 rounded-lg border border-border bg-card/30 backdrop-blur hover:border-foreground/20 transition-all space-y-4"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/60 pb-3">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded border border-border bg-foreground/[0.02] flex items-center justify-center">
                    <Package className="w-4 h-4 text-foreground" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-foreground">
                        {o.order_number}
                      </span>
                      <span className="text-[11px] font-mono text-muted-foreground">
                        &bull; {o.seller_name}
                      </span>
                    </div>
                    <span className="text-[11px] font-mono text-muted-foreground">
                      Placed on {new Date(o.order_date).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono border border-border bg-foreground/[0.02]">
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        o.order_status === "delivered"
                          ? "bg-emerald-400"
                          : o.order_status === "shipped"
                          ? "bg-blue-400"
                          : "bg-amber-400"
                      }`}
                    />
                    <span className="capitalize">{o.order_status.replace(/_/g, " ")}</span>
                  </span>

                  <span className="font-mono text-xs font-bold text-foreground">
                    {o.currency} {Number(o.total_amount ?? 0).toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Order Items & Shipment Info */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
                <div className="md:col-span-2 space-y-1.5">
                  <span className="text-[10px] uppercase text-muted-foreground block">
                    Order Contents ({o.items_count} item{o.items_count > 1 ? "s" : ""})
                  </span>
                  <div className="space-y-1">
                    {(o.items || []).map((it: any, idx: number) => {
                      const itemTotal = it.total_price ?? (it.unit_price ? it.unit_price * (it.quantity || 1) : 0);
                      return (
                        <div key={idx} className="flex justify-between text-muted-foreground">
                          <span className="text-foreground">{it.title} &times; {it.quantity || 1}</span>
                          <span>{o.currency} {Number(itemTotal).toFixed(2)}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="p-3 rounded border border-border bg-background/50 space-y-1">
                  <span className="text-[10px] uppercase text-muted-foreground block">
                    Fulfillment Status
                  </span>
                  {o.carrier ? (
                    <div className="space-y-1">
                      <div className="flex items-center gap-1.5 text-foreground">
                        <Truck className="w-3.5 h-3.5 text-muted-foreground" />
                        <span>{o.carrier}</span>
                      </div>
                      <div className="text-muted-foreground truncate">
                        AWB: {o.tracking_number || "Not assigned"}
                      </div>
                      {o.delivery_date && (
                        <div className="text-emerald-400">
                          Delivered: {new Date(o.delivery_date).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="text-muted-foreground">Standard Courier Dispatch</span>
                  )}
                </div>
              </div>

              {/* Action Bar */}
              <div className="flex items-center justify-between pt-2 border-t border-border/40">
                <span className="text-[11px] font-mono text-muted-foreground">
                  Payment: <span className="uppercase text-foreground">{o.payment_method}</span> ({o.payment_status})
                </span>

                <Link
                  href={`/buyer/complaints/new?order_id=${o.id}`}
                  className="h-8 px-4 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity inline-flex items-center gap-1.5"
                >
                  <span>Resolve an Issue</span>
                  <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Claim Order Modal */}
      {showLinkModal && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-2xl space-y-6">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div>
                <span className="text-[10px] font-mono uppercase text-muted-foreground">
                  Order Ownership
                </span>
                <h3 className="font-display text-2xl tracking-tight text-foreground">
                  Claim Store Order
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowLinkModal(false)}
                className="text-muted-foreground hover:text-foreground text-sm font-mono"
              >
                Close
              </button>
            </div>

            <form onSubmit={handleLinkOrder} className="space-y-4">
              <div>
                <label className="text-xs font-mono uppercase text-muted-foreground block mb-1.5">
                  Order Number
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. ORD-1001"
                  value={orderNumberToLink}
                  onChange={(e) => setOrderNumberToLink(e.target.value)}
                  className="w-full h-10 px-3 bg-background border border-border rounded-md text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
                />
                <span className="text-[11px] text-muted-foreground mt-1.5 block">
                  Found on your store receipt, SMS notification, or dispatch email.
                </span>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowLinkModal(false)}
                  className="h-9 px-4 rounded-full border border-border text-xs font-mono text-muted-foreground hover:text-foreground"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={linkingOrder}
                  className="h-9 px-5 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity"
                >
                  {linkingOrder ? "Claiming..." : "Claim Order"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
