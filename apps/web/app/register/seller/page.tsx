"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Store, ArrowLeft, ArrowRight, Loader2, AlertCircle } from "lucide-react";
import { toast } from "sonner";

export default function RegisterSellerPage() {
  const router = useRouter();
  const [storeName, setStoreName] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [storeUrl, setStoreUrl] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!storeName || !fullName || !email || !password) {
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
      const res = await fetch("/api/v1/auth/register/seller", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          store_name: storeName.trim(),
          full_name: fullName.trim(),
          email: email.trim().toLowerCase(),
          password,
          store_url: storeUrl.trim() || null,
          phone: phone.trim() || null,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        const errorMsg = data.error?.message || data.detail || "Registration failed";
        setError(errorMsg);
        toast.error(errorMsg);
      } else {
        toast.success("Seller account created successfully");
        router.push(data.redirect_uri || "/seller/onboarding");
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
            <Store className="w-4 h-4" />
          </div>
          <div>
            <span className="text-xs font-mono uppercase tracking-widest text-muted-foreground block">
              Merchant Onboarding
            </span>
            <h1 className="text-2xl font-display tracking-tight">Create Seller Account</h1>
          </div>
        </div>

        <p className="text-xs text-muted-foreground mb-6">
          Set up your store rules, automated thresholds, and connect your fulfillment channels.
        </p>

        {error && (
          <div className="mb-5 p-3 rounded-sm border border-destructive/30 bg-destructive/10 text-destructive text-xs font-mono flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-muted-foreground mb-1.5 uppercase">
              Store / Brand Name *
            </label>
            <input
              type="text"
              required
              value={storeName}
              onChange={(e) => setStoreName(e.target.value)}
              placeholder="Apex Electronics"
              className="w-full h-11 px-3.5 rounded-sm bg-background border border-border text-sm font-sans focus:outline-none focus:border-foreground transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-muted-foreground mb-1.5 uppercase">
              Administrator Full Name *
            </label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Alex Chen"
              className="w-full h-11 px-3.5 rounded-sm bg-background border border-border text-sm font-sans focus:outline-none focus:border-foreground transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-muted-foreground mb-1.5 uppercase">
              Work Email Address *
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="alex@apexstore.example"
              className="w-full h-11 px-3.5 rounded-sm bg-background border border-border text-sm font-sans focus:outline-none focus:border-foreground transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-muted-foreground mb-1.5 uppercase">
              Password (min 8 chars) *
            </label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Choose a strong password"
              className="w-full h-11 px-3.5 rounded-sm bg-background border border-border text-sm font-sans focus:outline-none focus:border-foreground transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-muted-foreground mb-1.5 uppercase">
              Store URL (Optional)
            </label>
            <input
              type="url"
              value={storeUrl}
              onChange={(e) => setStoreUrl(e.target.value)}
              placeholder="store.example.com"
              className="w-full h-11 px-3.5 rounded-sm bg-background border border-border text-sm font-sans focus:outline-none focus:border-foreground transition-colors"
            />
          </div>

          <div className="text-xs text-muted-foreground leading-relaxed pt-2">
            By creating an account, you agree to our{" "}
            <Link href="/terms" className="text-foreground underline">
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link href="/privacy" className="text-foreground underline">
              Privacy Policy
            </Link>.
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full h-12 mt-2 rounded-full bg-foreground text-background font-medium text-sm hover:opacity-90 transition-opacity cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Creating Seller Account...</span>
              </>
            ) : (
              <>
                <span>Complete Registration &amp; Setup</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-border flex items-center justify-between text-xs font-mono text-muted-foreground">
          <span>Already registered?</span>
          <Link href="/login/seller" className="hover:text-foreground underline">
            Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}
