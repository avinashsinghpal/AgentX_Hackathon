"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ShoppingBag, ArrowLeft, ArrowRight, Loader2, Sparkles, AlertCircle } from "lucide-react";
import { toast } from "sonner";

export default function BuyerLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("buyer@example.com");
  const [password, setPassword] = useState("Password123!");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fillDemo = () => {
    setEmail("buyer@example.com");
    setPassword("Password123!");
    setError(null);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please enter both email and password");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        const errorMsg = data.error?.message || data.detail || "Invalid email or password";
        setError(errorMsg);
        toast.error(errorMsg);
      } else {
        toast.success("Welcome back to your customer portal");
        const destination = data.redirect_uri === "/buyer" ? "/buyer/orders" : (data.redirect_uri || "/buyer/orders");
        router.push(destination);
        router.refresh();
      }
    } catch {
      setError("Network error communicating with authentication service");
      toast.error("Network connection error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6">
      <Link
        href="/login"
        className="inline-flex items-center gap-2 text-xs font-mono text-muted-foreground hover:text-foreground mb-8 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Choose Portal
      </Link>

      <div className="w-full max-w-md p-8 border border-border bg-card/40 rounded-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-sm border border-border flex items-center justify-center text-foreground bg-foreground/[0.02]">
              <ShoppingBag className="w-4 h-4" />
            </div>
            <div>
              <span className="text-xs font-mono uppercase tracking-widest text-muted-foreground block">
                Customer Portal
              </span>
              <h1 className="text-2xl font-display tracking-tight">Buyer Sign In</h1>
            </div>
          </div>
          <button
            type="button"
            onClick={fillDemo}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-mono text-[#a78bfa] border border-[#a78bfa]/30 rounded hover:bg-[#a78bfa]/10 transition-colors"
            title="Auto-fill verified demo buyer credentials"
          >
            <Sparkles className="w-3 h-3" />
            Demo
          </button>
        </div>

        <p className="text-xs text-muted-foreground mb-6">
          Sign in to view your orders, file complaints, and chat with the autonomous agent.
        </p>

        {error && (
          <div className="mb-5 p-3 rounded-sm border border-destructive/30 bg-destructive/10 text-destructive text-xs font-mono flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-muted-foreground mb-1.5 uppercase">
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="buyer@example.com"
              className="w-full h-11 px-3.5 rounded-sm bg-background border border-border text-sm font-sans focus:outline-none focus:border-foreground transition-colors"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-mono text-muted-foreground uppercase">
                Password
              </label>
              <button
                type="button"
                onClick={fillDemo}
                className="text-[11px] font-mono text-muted-foreground hover:text-foreground"
              >
                Use Password123!
              </button>
            </div>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              className="w-full h-11 px-3.5 rounded-sm bg-background border border-border text-sm font-sans focus:outline-none focus:border-foreground transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full h-12 mt-2 rounded-full bg-foreground text-background font-medium text-sm hover:opacity-90 transition-opacity cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Authenticating...</span>
              </>
            ) : (
              <>
                <span>Sign In to Customer Orders</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-border flex items-center justify-between text-xs font-mono text-muted-foreground">
          <span>First time here?</span>
          <Link href="/register/buyer" className="hover:text-foreground underline">
            Create buyer account
          </Link>
        </div>
      </div>
    </div>
  );
}
