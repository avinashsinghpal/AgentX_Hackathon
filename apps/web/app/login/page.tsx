import Link from "next/link";
import { Store, ShoppingBag, ArrowLeft, ArrowRight } from "lucide-react";

export const metadata = {
  title: "Sign In | SellerResolve",
};

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6">
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-xs font-mono text-muted-foreground hover:text-foreground mb-8 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to Home
      </Link>

      <div className="w-full max-w-md p-8 border border-border bg-card/40 rounded-sm">
        <span className="text-xs font-mono uppercase tracking-widest text-muted-foreground block mb-2">
          Authentication
        </span>
        <h1 className="text-3xl font-display tracking-tight mb-2">
          Select your portal
        </h1>
        <p className="text-xs text-muted-foreground mb-8">
          Choose whether you are signing in as an online seller or as a purchasing customer.
        </p>

        <div className="space-y-4">
          <Link
            href="/login/seller"
            className="flex items-center justify-between p-5 border border-border hover:border-foreground/40 bg-foreground/[0.02] hover:bg-foreground/[0.05] rounded-sm transition-all group"
          >
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-sm border border-border flex items-center justify-center text-foreground">
                <Store className="w-5 h-5" />
              </div>
              <div>
                <span className="font-display text-lg block">Seller Portal</span>
                <span className="text-xs text-muted-foreground font-sans">
                  Manage store, policies, approvals &amp; audit log
                </span>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground group-hover:translate-x-1 transition-all" />
          </Link>

          <Link
            href="/login/buyer"
            className="flex items-center justify-between p-5 border border-border hover:border-foreground/40 bg-foreground/[0.02] hover:bg-foreground/[0.05] rounded-sm transition-all group"
          >
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-sm border border-border flex items-center justify-center text-foreground">
                <ShoppingBag className="w-5 h-5" />
              </div>
              <div>
                <span className="font-display text-lg block">Buyer Portal</span>
                <span className="text-xs text-muted-foreground font-sans">
                  File complaints, track orders &amp; live resolution chat
                </span>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground group-hover:translate-x-1 transition-all" />
          </Link>
        </div>

        <div className="mt-8 pt-6 border-t border-border flex items-center justify-between text-xs font-mono text-muted-foreground">
          <span>Need an account?</span>
          <div className="space-x-3">
            <Link href="/register/seller" className="hover:text-foreground underline">
              Register as Seller
            </Link>
            <span>&bull;</span>
            <Link href="/register/buyer" className="hover:text-foreground underline">
              Register as Buyer
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

