import React from "react";
import { FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({
  title = "No records found",
  description = "No items have been created or recorded yet.",
  icon: Icon = FolderOpen,
  actionLabel,
  onAction,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`p-10 border border-border bg-card/30 rounded-sm flex flex-col items-center justify-center text-center ${className}`}
    >
      <div className="w-12 h-12 rounded-full border border-border bg-foreground/[0.03] flex items-center justify-center text-muted-foreground mb-4">
        <Icon className="w-6 h-6" />
      </div>
      <h4 className="text-lg font-display text-foreground mb-1">{title}</h4>
      <p className="text-xs text-muted-foreground max-w-sm mb-6 leading-relaxed font-sans">
        {description}
      </p>
      {actionLabel && onAction && (
        <Button
          type="button"
          size="sm"
          onClick={onAction}
          className="rounded-full font-mono text-xs px-5 bg-foreground text-background hover:opacity-90"
        >
          {actionLabel}
        </Button>
      )}
    </div>
  );
}

