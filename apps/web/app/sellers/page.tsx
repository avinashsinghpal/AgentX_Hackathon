"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Store,
  Search,
  ShieldCheck,
  RotateCcw,
  RefreshCw,
  ExternalLink,
  ArrowRight,
  PackageCheck,
  CheckCircle2,
} from "lucide-react";
import { Navigation } from "@/components/landing/navigation";
import { FooterSection } from "@/components/landing/footer-section";
import { EmptyState } from "@/components/ui/empty-state";
import { toast } from "sonner";

interface SellerDirectoryItem {
  id: string;
  store_name: string;
  description: string;
  categories: string[];
  return_window_days: number;
  auto_approve_max_amount: number;
  shipping_fee_bearer: string;
  orders_count: number;
}

export default function PublicSellersPage() {
  const [sellers, setSellers] = useState<SellerDirectoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchSellers = async (q = "") => {
    try {
      setLoading(true);
      const url = q.trim()
        ? `/api/v1/sellers/directory?q=${encodeURIComponent(q.trim())}`
        : "/api/v1/sellers/directory";
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setSellers(data);
      } else {
        toast.error("Failed to load merchants directory");
      }
    } catch {
      toast.error("Network error loading merchants");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSellers();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchSellers(searchQuery);
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Navigation />

      <main className="flex-1 pt-32 pb-24 px-6 lg:px-12 max-w-[1400px] mx-auto w-full space-y-12">
        {/* Header */}
        <div className="space-y-4 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-border bg-foreground/[0.02]">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-[11px] font-mono uppercase text-muted-foreground tracking-wider">
              Autonomous Merchant Network
            </span>
          </div>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl tracking-tight text-foreground">
            Verified Independent Sellers
          </h1>
          <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
            Every merchant listed here operates an autonomous resolution agent configured with transparent, deterministic customer refund and return policies.
          </p>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearch} className="flex gap-3 max-w-xl">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-muted-foreground absolute left-3.5 top-3" />
            <input
              type="text"
              placeholder="Search store name, category, or merchandise..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-10 pl-10 pr-4 bg-card/60 border border-border rounded-full text-xs font-mono text-foreground focus:outline-none focus:border-foreground/50"
            />
          </div>
          <button
            type="submit"
            className="h-10 px-6 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity"
          >
            Search
          </button>
        </form>

        {/* Grid of Sellers */}
        {sellers.length === 0 ? (
          <EmptyState
            title="No merchants found"
            description={
              searchQuery
                ? `No verified sellers matching '${searchQuery}'. Try another search query.`
                : "No verified sellers currently active in the directory."
            }
            icon={Store}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {sellers.map((s) => (
              <div
                key={s.id}
                className="p-6 rounded-lg border border-border bg-card/30 backdrop-blur hover:border-foreground/30 transition-all flex flex-col justify-between space-y-6"
              >
                <div className="space-y-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="w-10 h-10 rounded-md border border-border bg-foreground/[0.03] flex items-center justify-center shrink-0">
                      <Store className="w-5 h-5 text-foreground" />
                    </div>
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Verified Policy</span>
                    </span>
                  </div>

                  <div>
                    <h3 className="font-display text-2xl tracking-tight text-foreground">
                      {s.store_name}
                    </h3>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                      {s.description}
                    </p>
                  </div>

                  {/* Policy Attributes */}
                  <div className="space-y-2 pt-2 border-t border-border/60 text-xs font-mono">
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>Return Window:</span>
                      <span className="text-foreground font-medium">{s.return_window_days} Days</span>
                    </div>
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>Auto-Approve Refund:</span>
                      <span className="text-foreground font-medium">Up to &#8377;{Number(s.auto_approve_max_amount ?? 0).toFixed(0)}</span>
                    </div>
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>Reverse Freight:</span>
                      <span className="text-foreground capitalize">{s.shipping_fee_bearer || "Buyer"} Borne</span>
                    </div>
                  </div>

                  {/* Categories Tags */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {(s.categories || []).map((cat) => (
                      <span
                        key={cat}
                        className="px-2 py-0.5 rounded text-[10px] font-mono border border-border bg-foreground/[0.02] text-muted-foreground"
                      >
                        {cat}
                      </span>
                    ))}
                  </div>
                </div>

                <Link
                  href={`/buyer/orders`}
                  className="w-full h-10 rounded-full border border-border text-xs font-mono hover:bg-foreground hover:text-background transition-colors flex items-center justify-center gap-2 group"
                >
                  <span>View Orders & File Claim</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                </Link>
              </div>
            ))}
          </div>
        )}
      </main>

      <FooterSection />
    </div>
  );
}
