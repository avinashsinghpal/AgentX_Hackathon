"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function BuyerRootPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/buyer/orders");
  }, [router]);

  return (
    <div className="py-24 text-center space-y-4">
      <div className="w-8 h-8 border-2 border-foreground border-t-transparent rounded-full animate-spin mx-auto" />
      <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
        Redirecting to Customer Orders...
      </p>
    </div>
  );
}

