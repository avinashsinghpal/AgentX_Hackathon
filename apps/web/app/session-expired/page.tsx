import Link from "next/link";
import { Clock, LogIn, Home } from "lucide-react";

export const metadata = {
  title: "Session Expired | SellerResolve",
};

export default function SessionExpiredPage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6 text-center">
      <div className="w-16 h-16 rounded-full border border-border bg-card/60 flex items-center justify-center mb-6 text-muted-foreground">
        <Clock className="w-8 h-8" />
      </div>

      <span className="text-xs font-mono uppercase tracking-widest text-muted-foreground mb-3">
        Authentication &bull; Code 401
      </span>

      <h1 className="text-4xl md:text-5xl font-display tracking-tight mb-4 max-w-md">
        Your session has expired.
      </h1>

      <p className="text-sm text-muted-foreground max-w-sm mb-8 leading-relaxed">
        For your security, active sessions expire automatically after a period of inactivity. Please sign in again to continue.
      </p>

      <div className="flex flex-wrap items-center justify-center gap-4">
        <Link
          href="/login"
          className="inline-flex items-center gap-2 h-12 px-6 rounded-full bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <LogIn className="w-4 h-4" />
          Sign In Again
        </Link>
        <Link
          href="/"
          className="inline-flex items-center gap-2 h-12 px-6 rounded-full border border-border hover:bg-foreground/5 text-sm font-medium transition-colors"
        >
          <Home className="w-4 h-4" />
          Home
        </Link>
      </div>
    </div>
  );
}

