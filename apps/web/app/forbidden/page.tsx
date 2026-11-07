import Link from "next/link";
import { ShieldAlert, ArrowLeft, Home } from "lucide-react";

export const metadata = {
  title: "Access Restricted | SellerResolve",
};

export default function ForbiddenPage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6 text-center">
      <div className="w-16 h-16 rounded-full border border-destructive/30 bg-destructive/10 flex items-center justify-center mb-6 text-destructive">
        <ShieldAlert className="w-8 h-8" />
      </div>

      <span className="text-xs font-mono uppercase tracking-widest text-destructive mb-3">
        Authorization &bull; Code 403
      </span>

      <h1 className="text-4xl md:text-5xl font-display tracking-tight mb-4 max-w-md">
        Access restricted.
      </h1>

      <p className="text-sm text-muted-foreground max-w-sm mb-8 leading-relaxed">
        Your authenticated account does not have permission to view or manage this resource. If you believe this is in error, contact the store administrator.
      </p>

      <div className="flex flex-wrap items-center justify-center gap-4">
        <Link
          href="/"
          className="inline-flex items-center gap-2 h-12 px-6 rounded-full bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <Home className="w-4 h-4" />
          Return to Home
        </Link>
        <Link
          href="/login"
          className="inline-flex items-center gap-2 h-12 px-6 rounded-full border border-border hover:bg-foreground/5 text-sm font-medium transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Switch Account
        </Link>
      </div>
    </div>
  );
}

