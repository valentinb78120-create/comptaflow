import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { InvoiceStatus } from "../types/invoice";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatAmount(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("fr-FR").format(new Date(iso));
}

export const STATUS_LABELS: Record<InvoiceStatus, string> = {
  pending: "En attente",
  processing: "Traitement OCR",
  needs_review: "À vérifier",
  validated: "Validée",
  exported: "Exportée",
};

export const STATUS_COLORS: Record<InvoiceStatus, string> = {
  pending: "bg-ink-100 text-ink-600",
  processing: "bg-blue-50 text-blue-700",
  needs_review: "bg-amber-50 text-amber-700",
  validated: "bg-emerald-50 text-emerald-700",
  exported: "bg-accent-500/10 text-accent-600",
};
