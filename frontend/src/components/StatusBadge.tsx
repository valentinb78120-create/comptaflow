import { cn, STATUS_COLORS, STATUS_LABELS } from "../lib/utils";
import type { InvoiceStatus } from "../types/invoice";

const DOT: Record<InvoiceStatus, string> = {
  pending: "bg-ink-400",
  processing: "bg-blue-500",
  needs_review: "bg-amber-500",
  validated: "bg-emerald-500",
  exported: "bg-accent-500",
};

export function StatusBadge({ status }: { status: InvoiceStatus }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium", STATUS_COLORS[status])}>
      <span className={cn("w-1.5 h-1.5 rounded-full", DOT[status], status === "processing" && "animate-pulse")} />
      {STATUS_LABELS[status]}
    </span>
  );
}
