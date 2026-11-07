"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ShoppingBag, ArrowLeft, ArrowRight, Loader2, AlertCircle } from "lucide-react";
import { toast } from "sonner";

export default function RegisterBuyerPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName || !email || !password) {
      setError("Please fill in all required fields");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/v1/auth/register/buyer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: fullName.trim(),
          email: email.trim().toLowerCase(),
          password,
          phone: phone.trim() || null,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        const errorMsg = data.error?.message || data.detail || "Registration failed";
        setError(errorMsg);
        toast.error(errorMsg);
      } else {
        toast.success("Buyer account created successfully");
        const destination = data.redirect_uri === "/buyer" ? "/buyer/orders" : (data.redirect_uri || "/buyer/orders");
        router.push(destination);
        router.refresh();
      }
    } catch {
      setError("Network error communicating with registration service");
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
        Back to Sign In
      </Link>

      <div className="w-full max-w-md p-8 border border-border bg-card/40 rounded-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-sm border border-border flex items-center justify-center text-foreground bg-foreground/[0.02]">
            <ShoppingBag className="w-4 h-4" />
          </div>
          <div>
            <span className="text-xs font-mono uppercase tracking-widest text-muted-foreground block">
              Customer Registration
            </span>
            <h1 className="text-2xl font-display tracking-tight">Create Buyer Account</h1>
          </div>
        </div>

        <p className="text-xs text-muted-foreground mb-6">
          Register to view participating sellers, track orders, and submit complaint claims.
        </p>

        {error && (
          <div className="mb-6 p-3 rounded-sm border border-destructive/30 bg-destructive/10 text-destructive flex items-center gap-2 text-xs font-mono">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-muted-foreground mb-1.5 uppercase">
              Full Name *
            </label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Maya Lin"
              className="w-full h-11 px-3.5 rounded-sm bg-background border border-border text-sm font-sans focus:outline-none focus:border-foreground transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-muted-foreground mb-1.5 uppercase">
              Email Address *
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="maya@example.com"
              className="w-full h-11 px-3.5 rounded-sm bg-background border border-border text-sm font-sans focus:outline-none focus:border-foreground transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-muted-foreground mb-1.5 uppercase">
              Phone (Optional)
            </label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+1 555-0199"
              className="w-full h-11 px-3.5 rounded-sm bg-background border border-border text-sm font-sans focus:outline-none focus:border-foreground transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-muted-foreground mb-1.5 uppercase">
              Password *
            </label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 characters"
              className="w-full h-11 px-3.5 rounded-sm bg-background border border-border text-sm font-sans focus:outline-none focus:border-foreground transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full h-11 mt-2 inline-flex items-center justify-center gap-2 rounded-sm bg-foreground text-background font-mono text-xs font-semibold uppercase tracking-wider hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Creating Account...
              </>
            ) : (
              <>
                Create Buyer Account
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-6 pt-6 border-t border-border flex items-center justify-between text-xs font-mono text-muted-foreground">
          <span>Already have an account?</span>
          <Link href="/login/buyer" className="text-foreground hover:underline">
            Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}
