import React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "Failed to load information",
  description = "An error occurred while fetching data from the server. Please try again.",
  onRetry,
  className = "",
}: ErrorStateProps) {
  return (
    <div
      className={`p-8 border border-destructive/20 bg-destructive/5 rounded-sm flex flex-col items-center justify-center text-center ${className}`}
    >
      <div className="w-12 h-12 rounded-full border border-destructive/30 bg-destructive/10 flex items-center justify-center text-destructive mb-4">
        <AlertCircle className="w-6 h-6" />
      </div>
      <h4 className="text-lg font-display text-foreground mb-1">{title}</h4>
      <p className="text-xs text-muted-foreground max-w-sm mb-6 leading-relaxed">
        {description}
      </p>
      {onRetry && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onRetry}
          className="rounded-full font-mono text-xs gap-2"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Retry
        </Button>
      )}
    </div>
  );
}

