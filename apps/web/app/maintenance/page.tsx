import { Wrench, RefreshCw } from "lucide-react";

export const metadata = {
  title: "Scheduled Maintenance | SellerResolve",
};

export default function MaintenancePage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6 text-center">
      <div className="w-16 h-16 rounded-full border border-amber-500/30 bg-amber-500/10 flex items-center justify-center mb-6 text-amber-400">
        <Wrench className="w-8 h-8" />
      </div>

      <span className="text-xs font-mono uppercase tracking-widest text-amber-400 mb-3">
        System Maintenance
      </span>

      <h1 className="text-4xl md:text-5xl font-display tracking-tight mb-4 max-w-md">
        Scheduled engine update in progress.
      </h1>

      <p className="text-sm text-muted-foreground max-w-sm mb-8 leading-relaxed">
        We are applying database optimizations and upgrading policy worker queues. All active disputes are paused safely and will resume automatically.
      </p>

      <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-border bg-card font-mono text-xs text-muted-foreground">
        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
        Estimated completion: 15 minutes
      </div>
    </div>
  );
}

