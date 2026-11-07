"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  CheckSquare,
  FileCode,
  SlidersHorizontal,
  Users,
  ScrollText,
  LogOut,
  Store,
  Menu,
  X,
} from "lucide-react";

const navigationItems = [
  { name: "Dashboard", href: "/seller/dashboard", icon: LayoutDashboard },
  { name: "Onboarding", href: "/seller/onboarding", icon: SlidersHorizontal },
  { name: "Approvals", href: "/seller/approvals", icon: CheckSquare },
  { name: "Policy Manager", href: "/seller/policies", icon: FileCode },
  { name: "Operations", href: "/seller/operations", icon: SlidersHorizontal },
  { name: "Customers & Orders", href: "/seller/customers", icon: Users },
  { name: "Audit Trail", href: "/seller/audit", icon: ScrollText },
];

export default function SellerLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  const handleLogout = async () => {
    setSigningOut(true);
    try {
      await fetch("/api/v1/auth/logout", { method: "POST" });
    } catch {
      // Continue redirect even on network error
    }
    router.push("/login");
    router.refresh();
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col md:flex-row">
      {/* Mobile Top Header */}
      <header className="md:hidden border-b border-border bg-card/60 backdrop-blur px-6 h-16 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-sm border border-border flex items-center justify-center text-foreground">
            <Store className="w-4 h-4" />
          </div>
          <div>
            <span className="font-display text-lg tracking-tight block">SellerResolve</span>
            <span className="text-[10px] font-mono text-muted-foreground uppercase">Merchant Console</span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 border border-border rounded-sm text-foreground"
          aria-label="Toggle menu"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </header>

      {/* Sidebar for Desktop & Mobile Overlay */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 border-r border-border bg-card/40 backdrop-blur flex flex-col justify-between p-6 transition-transform md:translate-x-0 md:static ${
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div>
          {/* Brand header */}
          <div className="hidden md:flex items-center gap-3 mb-8">
            <div className="w-9 h-9 rounded-sm border border-border flex items-center justify-center text-foreground bg-foreground/[0.02]">
              <Store className="w-4 h-4" />
            </div>
            <div>
              <Link href="/" className="font-display text-xl tracking-tight block hover:opacity-80 transition-opacity">
                SellerResolve
              </Link>
              <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest block">
                Merchant Console
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1">
            {navigationItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || (item.href !== "/seller/dashboard" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-3.5 py-2.5 rounded-sm text-xs font-mono transition-all ${
                    isActive
                      ? "bg-foreground text-background font-medium shadow-sm"
                      : "text-muted-foreground hover:text-foreground hover:bg-foreground/[0.03]"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User profile & Sign out */}
        <div className="pt-6 border-t border-border space-y-3">
          <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
            <span className="truncate">Merchant Account</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
          </div>
          <button
            type="button"
            onClick={handleLogout}
            disabled={signingOut}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-sm text-xs font-mono text-muted-foreground hover:text-foreground transition-colors hover:bg-foreground/[0.03] disabled:opacity-50 text-left"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>{signingOut ? "Signing Out..." : "Sign Out"}</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 overflow-y-auto">
        <div className="max-w-[1280px] mx-auto p-6 lg:p-10">{children}</div>
      </main>
    </div>
  );
}

