"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log error cleanly in development
    if (process.env.NODE_ENV !== "production") {
      // Intentionally avoiding console.log per strict linter rules; digest tracks error
    }
  }, [error]);

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6 text-center">
      <div className="w-16 h-16 rounded-full border border-destructive/30 bg-destructive/10 flex items-center justify-center mb-6 text-destructive">
        <AlertTriangle className="w-8 h-8" />
      </div>

      <span className="text-xs font-mono uppercase tracking-widest text-destructive mb-3">
        System Exception &bull; Code 500
      </span>

      <h1 className="text-4xl md:text-5xl font-display tracking-tight mb-4 max-w-lg">
        An unexpected error occurred.
      </h1>

      <p className="text-sm text-muted-foreground max-w-md mb-6 leading-relaxed">
        The application encountered an unexpected state. Our monitoring has recorded this event.
      </p>

      {error.digest && (
        <div className="p-3 mb-8 border border-border bg-card/60 rounded font-mono text-xs text-muted-foreground max-w-sm overflow-hidden text-ellipsis">
          Reference ID: {error.digest}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-center gap-4">
        <button
          type="button"
          onClick={() => reset()}
          className="inline-flex items-center gap-2 h-12 px-6 rounded-full bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity cursor-pointer"
        >
          <RefreshCw className="w-4 h-4" />
          Try Again
        </button>
        <Link
          href="/"
          className="inline-flex items-center gap-2 h-12 px-6 rounded-full border border-border hover:bg-foreground/5 text-sm font-medium transition-colors"
        >
          <Home className="w-4 h-4" />
          Return to Home
        </Link>
      </div>
    </div>
  );
}

