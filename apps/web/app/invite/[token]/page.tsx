"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Store,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  UserPlus,
  LogIn,
  PackageCheck,
} from "lucide-react";
import { toast } from "sonner";

interface InviteInfo {
  valid: boolean;
  invite_token: string;
  seller_name: string;
  seller_id: string;
  customer_email?: string | null;
  expires_at?: string | null;
  message?: string | null;
}

export default function InviteAcceptancePage() {
  const params = useParams();
  const router = useRouter();
  const token = params?.token as string;

  const [invite, setInvite] = useState<InviteInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    if (!token) return;

    const checkInviteAndAuth = async () => {
      try {
        setLoading(true);
        const [inviteRes, meRes] = await Promise.all([
          fetch(`/api/v1/invites/${token}`),
          fetch("/api/v1/auth/me"),
        ]);

        if (inviteRes.ok) {
          const invData = await inviteRes.json();
          setInvite(invData);
        } else {
          setInvite({
            valid: false,
            invite_token: token,
            seller_name: "Merchant",
            seller_id: "",
            message: "This invitation link is invalid or does not exist.",
          });
        }

        if (meRes.ok) {
          const meData = await meRes.json();
          setIsAuthenticated(meData.role === "buyer");
        } else {
          setIsAuthenticated(false);
        }
      } catch {
        toast.error("Failed to verify invitation link");
      } finally {
        setLoading(false);
      }
    };

    checkInviteAndAuth();
  }, [token]);

  const handleAcceptInvite = async () => {
    try {
      setAccepting(true);
      const res = await fetch(`/api/v1/invites/${token}/accept`, {
        method: "POST",
      });

      if (res.ok) {
        const data = await res.json();
        toast.success(data.message || "Connected to merchant successfully");
        router.push("/buyer/orders");
      } else {
        const err = await res.json();
        toast.error(err.error?.message || "Failed to accept invitation");
      }
    } catch {
      toast.error("Network error while connecting to merchant");
    } finally {
      setAccepting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6 text-foreground">
        <div className="text-center space-y-4">
          <div className="w-8 h-8 border-2 border-foreground border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
            Validating invitation token...
          </p>
        </div>
      </div>
    );
  }

  if (!invite || !invite.valid) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6 text-foreground">
        <div className="max-w-md w-full p-8 rounded-lg border border-destructive/30 bg-card/40 backdrop-blur space-y-6 text-center">
          <div className="w-12 h-12 rounded-full border border-destructive/40 bg-destructive/10 flex items-center justify-center mx-auto text-destructive">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-display text-2xl tracking-tight text-foreground">
              Invitation Invalid or Expired
            </h1>
            <p className="text-xs text-muted-foreground mt-2 font-mono">
              {invite?.message || "This invitation token is not valid or has exceeded its 7-day expiration window."}
            </p>
          </div>
          <Link
            href="/sellers"
            className="inline-flex h-10 px-6 rounded-full bg-foreground text-background text-xs font-mono font-medium items-center justify-center hover:opacity-90 transition-opacity"
          >
            Browse Verified Merchants
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6 text-foreground">
      <div className="max-w-md w-full p-8 rounded-lg border border-border bg-card/40 backdrop-blur space-y-6">
        <div className="flex items-center gap-3 border-b border-border pb-4">
          <div className="w-10 h-10 rounded-sm border border-border bg-foreground/[0.03] flex items-center justify-center shrink-0">
            <Store className="w-5 h-5 text-foreground" />
          </div>
          <div>
            <span className="text-[10px] font-mono uppercase text-muted-foreground tracking-wider block">
              Merchant Invitation
            </span>
            <h2 className="font-display text-2xl tracking-tight text-foreground">
              {invite.seller_name}
            </h2>
          </div>
        </div>

        <div className="space-y-3 text-xs text-muted-foreground leading-relaxed">
          <p>
            You have been invited by <span className="font-medium text-foreground">{invite.seller_name}</span> to access their autonomous customer resolution portal.
          </p>
          <div className="p-3 rounded border border-border bg-background/60 font-mono text-[11px] space-y-1">
            <div className="flex items-center justify-between">
              <span>Token Status:</span>
              <span className="text-emerald-400 font-medium">Valid & Active</span>
            </div>
            {invite.expires_at && (
              <div className="flex items-center justify-between">
                <span>Expires:</span>
                <span className="text-foreground">
                  {new Date(invite.expires_at).toLocaleDateString()}
                </span>
              </div>
            )}
          </div>
        </div>

        {isAuthenticated ? (
          <div className="space-y-3 pt-2">
            <button
              type="button"
              onClick={handleAcceptInvite}
              disabled={accepting}
              className="w-full h-11 rounded-full bg-foreground text-background text-xs font-mono font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
            >
              <PackageCheck className="w-4 h-4" />
              <span>{accepting ? "Connecting..." : "Accept Invitation & Link Orders"}</span>
            </button>
            <p className="text-[11px] font-mono text-center text-muted-foreground">
              Orders matching your account will be immediately available.
            </p>
          </div>
        ) : (
          <div className="space-y-3 pt-2">
            <p className="text-xs font-mono text-center text-muted-foreground">
              Please sign in or register as a buyer to accept this invitation:
            </p>
            <div className="grid grid-cols-2 gap-3">
              <Link
                href={`/login/buyer?redirect=/invite/${token}`}
                className="h-10 rounded-full border border-border text-xs font-mono flex items-center justify-center gap-1.5 hover:bg-foreground/[0.04] transition-colors"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Log In</span>
              </Link>
              <Link
                href={`/register/buyer?redirect=/invite/${token}`}
                className="h-10 rounded-full bg-foreground text-background text-xs font-mono font-medium flex items-center justify-center gap-1.5 hover:opacity-90 transition-opacity"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>Register</span>
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
