"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-6 text-center font-sans antialiased">
        <div className="w-16 h-16 rounded-full border border-red-500/30 bg-red-500/10 flex items-center justify-center mb-6 text-red-400">
          <AlertTriangle className="w-8 h-8" />
        </div>

        <span className="text-xs font-mono uppercase tracking-widest text-red-400 mb-3">
          Critical Failure
        </span>

        <h1 className="text-4xl md:text-5xl font-serif tracking-tight mb-4 max-w-lg">
          Application critical error.
        </h1>

        <p className="text-sm text-neutral-400 max-w-md mb-8 leading-relaxed">
          The system encountered an unrecoverable rendering boundary failure.
        </p>

        <button
          type="button"
          onClick={() => reset()}
          className="inline-flex items-center gap-2 h-12 px-6 rounded-full bg-white text-black text-sm font-medium hover:opacity-90 transition-opacity cursor-pointer"
        >
          <RefreshCw className="w-4 h-4" />
          Reload Application
        </button>
      </body>
    </html>
  );
}

