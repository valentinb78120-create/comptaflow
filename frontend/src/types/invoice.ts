export type InvoiceStatus =
  | "pending"
  | "processing"
  | "needs_review"
  | "validated"
  | "exported";

export interface LineItem {
  id: string;
  description: string | null;
  quantity: number | null;
  unit_price_ht: number | null;
  total_ht: number | null;
  tva_rate: number | null;
  pcg_account: string | null;
}

export interface Invoice {
  id: string;
  cabinet_id: string;
  original_filename: string;
  status: InvoiceStatus;

  vendor_name: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  due_date: string | null;

  amount_ht: number | null;
  amount_tva: number | null;
  amount_ttc: number | null;
  tva_rate: number | null;

  pcg_account: string | null;
  pcg_label: string | null;
  pcg_source: "auto" | "manual" | null;

  ocr_confidence: number | null;
  ocr_error: string | null;

  line_items: LineItem[];
  created_at: string;
  updated_at: string;
}

export interface InvoicePatch {
  vendor_name?: string;
  invoice_number?: string;
  invoice_date?: string;
  due_date?: string;
  amount_ht?: number;
  amount_tva?: number;
  amount_ttc?: number;
  tva_rate?: number;
  pcg_account?: string;
  pcg_label?: string;
}
