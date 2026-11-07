import Link from "next/link";
import { FileQuestion, ArrowLeft, Home } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6 text-center">
      <div className="w-16 h-16 rounded-full border border-border bg-card/60 flex items-center justify-center mb-6 text-muted-foreground">
        <FileQuestion className="w-8 h-8" />
      </div>

      <span className="text-xs font-mono uppercase tracking-widest text-muted-foreground mb-3">
        Error 404 &bull; Page Not Found
      </span>

      <h1 className="text-5xl md:text-6xl font-display tracking-tight mb-4 max-w-md">
        This destination does not exist.
      </h1>

      <p className="text-sm text-muted-foreground max-w-sm mb-8 leading-relaxed">
        The page or resource you requested could not be located. It may have moved or the link may be outdated.
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
          Go to Sign In
        </Link>
      </div>
    </div>
  );
}

