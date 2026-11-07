import Link from "next/link";
import { MailX, Home, LogIn } from "lucide-react";

export const metadata = {
  title: "Invalid Invite Link | SellerResolve",
};

export default function InvalidInvitePage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6 text-center">
      <div className="w-16 h-16 rounded-full border border-border bg-card/60 flex items-center justify-center mb-6 text-muted-foreground">
        <MailX className="w-8 h-8" />
      </div>

      <span className="text-xs font-mono uppercase tracking-widest text-muted-foreground mb-3">
        Invitation Error
      </span>

      <h1 className="text-4xl md:text-5xl font-display tracking-tight mb-4 max-w-md">
        This invite link is invalid or expired.
      </h1>

      <p className="text-sm text-muted-foreground max-w-sm mb-8 leading-relaxed">
        Invitation links expire after 7 days or after being accepted. Please ask your merchant to issue a fresh invitation link.
      </p>

      <div className="flex flex-wrap items-center justify-center gap-4">
        <Link
          href="/login/buyer"
          className="inline-flex items-center gap-2 h-12 px-6 rounded-full bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <LogIn className="w-4 h-4" />
          Buyer Sign In
        </Link>
        <Link
          href="/"
          className="inline-flex items-center gap-2 h-12 px-6 rounded-full border border-border hover:bg-foreground/5 text-sm font-medium transition-colors"
        >
          <Home className="w-4 h-4" />
          Return Home
        </Link>
      </div>
    </div>
  );
}

