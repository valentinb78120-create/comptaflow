import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { z } from "zod";
import { api, invoiceFileUrl } from "../lib/api";
import type { Invoice, InvoicePatch } from "../types/invoice";
import { StatusBadge } from "../components/StatusBadge";

/** Validation des corrections : champs optionnels mais cohérents. */
const formSchema = z.object({
  vendor_name: z.string().max(512).optional(),
  invoice_number: z.string().max(128).optional(),
  invoice_date: z.string().optional(),
  due_date: z.string().optional(),
  amount_ht: z.coerce.number().nonnegative("Le montant HT doit être ≥ 0").optional(),
  amount_tva: z.coerce.number().nonnegative("La TVA doit être ≥ 0").optional(),
  amount_ttc: z.coerce.number().nonnegative("Le montant TTC doit être ≥ 0").optional(),
  tva_rate: z.coerce.number().min(0).max(100, "Taux entre 0 et 100").optional(),
  pcg_account: z
    .string()
    .regex(/^\d{6,8}$/, "Compte PCG : 6 à 8 chiffres (ex : 606100)")
    .optional()
    .or(z.literal("")),
  pcg_label: z.string().max(255).optional(),
});

type FormValues = {
  vendor_name: string;
  invoice_number: string;
  invoice_date: string;
  due_date: string;
  amount_ht: string;
  amount_tva: string;
  amount_ttc: string;
  tva_rate: string;
  pcg_account: string;
  pcg_label: string;
};

function toForm(inv: Invoice): FormValues {
  return {
    vendor_name: inv.vendor_name ?? "",
    invoice_number: inv.invoice_number ?? "",
    invoice_date: inv.invoice_date ?? "",
    due_date: inv.due_date ?? "",
    amount_ht: inv.amount_ht != null ? String(inv.amount_ht) : "",
    amount_tva: inv.amount_tva != null ? String(inv.amount_tva) : "",
    amount_ttc: inv.amount_ttc != null ? String(inv.amount_ttc) : "",
    tva_rate: inv.tva_rate != null ? String(inv.tva_rate) : "",
    pcg_account: inv.pcg_account ?? "",
    pcg_label: inv.pcg_label ?? "",
  };
}

export function InvoiceDetail() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FormValues | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);

  const { data: invoice, isLoading, isError } = useQuery({
    queryKey: ["invoice", id],
    queryFn: () => api.getInvoice(id!),
    enabled: !!id,
    // Tant que l'OCR tourne, on rafraîchit pour voir le résultat arriver
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "pending" || s === "processing" ? 3000 : false;
    },
  });

  // Initialise le formulaire à l'arrivée des données OCR (sans écraser les saisies)
  useEffect(() => {
    if (invoice && form === null && invoice.status !== "pending" && invoice.status !== "processing") {
      setForm(toForm(invoice));
    }
  }, [invoice, form]);

  if (isLoading) {
    return <Centered>Chargement…</Centered>;
  }
  if (isError || !invoice) {
    return (
      <Centered>
        <span className="text-red-500">Facture introuvable.</span>{" "}
        <Link to="/dashboard" className="text-brand-600 underline">Retour</Link>
      </Centered>
    );
  }

  const ocrRunning = invoice.status === "pending" || invoice.status === "processing";

  const set = (key: keyof FormValues) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((f) => (f ? { ...f, [key]: e.target.value } : f));
    setErrors((prev) => ({ ...prev, [key]: "" }));
  };

  const handleSave = async () => {
    if (!form) return;

    // Champs vides → omis du PATCH (le backend ignore les None)
    const candidate: Record<string, string> = {};
    for (const [k, v] of Object.entries(form)) {
      if (v !== "") candidate[k] = v;
    }

    const parsed = formSchema.safeParse(candidate);
    if (!parsed.success) {
      const fieldErrors: Record<string, string> = {};
      for (const issue of parsed.error.issues) {
        fieldErrors[String(issue.path[0])] = issue.message;
      }
      setErrors(fieldErrors);
      toast.error("Corrigez les champs en rouge");
      return;
    }

    setSaving(true);
    try {
      const patch = parsed.data as InvoicePatch;
      const updated = await api.patchInvoice(invoice.id, patch);
      queryClient.setQueryData(["invoice", id], updated);
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      toast.success("Facture validée ✓");
    } catch {
      toast.error("Erreur lors de la sauvegarde");
    } finally {
      setSaving(false);
    }
  };

  const handleExport = async (format: "ebp" | "sage50") => {
    setExporting(true);
    try {
      await api.exportInvoice(invoice.id, format);
      queryClient.invalidateQueries({ queryKey: ["invoice", id] });
      toast.success(`CSV ${format === "ebp" ? "EBP" : "Sage 50"} téléchargé`);
    } catch {
      toast.error("La facture doit être validée avant export");
    } finally {
      setExporting(false);
    }
  };

  const handleReprocess = async () => {
    try {
      await api.reprocessInvoice(invoice.id);
      setForm(null); // le formulaire se re-remplira avec le nouveau résultat OCR
      queryClient.invalidateQueries({ queryKey: ["invoice", id] });
      toast.info("OCR relancé — analyse en cours…");
    } catch {
      toast.error("Impossible de relancer l'OCR");
    }
  };

  const isPdf = invoice.original_filename.toLowerCase().endsWith(".pdf");

  return (
    <main className="max-w-7xl mx-auto px-6 py-6">
      {/* Fil d'ariane + statut */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Link to="/dashboard" className="text-sm text-gray-500 hover:text-gray-700">
            ← Tableau de bord
          </Link>
          <span className="text-gray-300">/</span>
          <span className="text-sm font-medium text-gray-900 truncate max-w-sm">
            {invoice.original_filename}
          </span>
        </div>
        <StatusBadge status={invoice.status} />
      </div>

      <div className="grid grid-cols-2 gap-6 items-start">
        {/* Aperçu du document */}
        <section className="bg-white rounded-2xl border border-gray-200 overflow-hidden sticky top-20">
          <div className="px-4 py-2.5 border-b border-gray-100 text-sm font-medium text-gray-700">
            Document original
          </div>
          {isPdf ? (
            <iframe
              src={invoiceFileUrl(invoice.id)}
              title="Aperçu de la facture"
              className="w-full h-[75vh]"
            />
          ) : (
            <div className="h-[75vh] overflow-auto flex items-start justify-center bg-gray-50 p-4">
              <img
                src={invoiceFileUrl(invoice.id)}
                alt="Aperçu de la facture"
                className="max-w-full rounded shadow"
              />
            </div>
          )}
        </section>

        {/* Formulaire de validation */}
        <section className="bg-white rounded-2xl border border-gray-200 p-6 space-y-5">
          <h2 className="font-semibold text-gray-900">Données extraites</h2>

          {ocrRunning && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-700 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              OCR en cours d'analyse… la page se mettra à jour automatiquement.
            </div>
          )}

          {invoice.ocr_error && (
            <div className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 flex items-center justify-between gap-3">
              <span className="truncate" title={invoice.ocr_error}>OCR : {invoice.ocr_error}</span>
              <button
                onClick={handleReprocess}
                disabled={ocrRunning}
                className="shrink-0 text-xs border border-amber-300 rounded px-2 py-1 hover:bg-amber-100 disabled:opacity-40"
              >
                Relancer l'OCR
              </button>
            </div>
          )}

          {invoice.ocr_confidence != null && !ocrRunning && (
            <div className="bg-gray-50 rounded-lg px-4 py-3 text-sm flex items-center gap-3">
              <span className="text-gray-500">Confiance OCR :</span>
              <span className={`font-semibold ${invoice.ocr_confidence >= 0.8 ? "text-green-600" : invoice.ocr_confidence >= 0.5 ? "text-amber-600" : "text-red-600"}`}>
                {Math.round(invoice.ocr_confidence * 100)}%
              </span>
              {invoice.pcg_source === "auto" && invoice.pcg_account && (
                <span className="text-xs bg-blue-100 text-blue-700 rounded px-2 py-0.5">
                  PCG auto : {invoice.pcg_account}
                </span>
              )}
            </div>
          )}

          {form && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Fournisseur" error={errors.vendor_name} full>
                  <input value={form.vendor_name} onChange={set("vendor_name")} />
                </Field>
                <Field label="N° facture" error={errors.invoice_number}>
                  <input value={form.invoice_number} onChange={set("invoice_number")} />
                </Field>
                <Field label="Date facture" error={errors.invoice_date}>
                  <input type="date" value={form.invoice_date} onChange={set("invoice_date")} />
                </Field>
                <Field label="Montant HT (€)" error={errors.amount_ht}>
                  <input type="number" step="0.01" min="0" value={form.amount_ht} onChange={set("amount_ht")} />
                </Field>
                <Field label="TVA (€)" error={errors.amount_tva}>
                  <input type="number" step="0.01" min="0" value={form.amount_tva} onChange={set("amount_tva")} />
                </Field>
                <Field label="Montant TTC (€)" error={errors.amount_ttc}>
                  <input type="number" step="0.01" min="0" value={form.amount_ttc} onChange={set("amount_ttc")} />
                </Field>
                <Field label="Taux TVA (%)" error={errors.tva_rate}>
                  <input type="number" step="0.1" min="0" max="100" value={form.tva_rate} onChange={set("tva_rate")} />
                </Field>
                <Field label="Compte PCG" error={errors.pcg_account}>
                  <input value={form.pcg_account} onChange={set("pcg_account")} placeholder="ex : 606100" />
                </Field>
                <Field label="Libellé PCG" error={errors.pcg_label}>
                  <input value={form.pcg_label} onChange={set("pcg_label")} placeholder="ex : Énergie électrique" />
                </Field>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                <div className="flex gap-2">
                  <button
                    onClick={() => handleExport("ebp")}
                    disabled={exporting || ocrRunning}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40"
                  >
                    Export EBP
                  </button>
                  <button
                    onClick={() => handleExport("sage50")}
                    disabled={exporting || ocrRunning}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40"
                  >
                    Export Sage 50
                  </button>
                </div>
                <button
                  onClick={handleSave}
                  disabled={saving || ocrRunning}
                  className="px-5 py-2 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50"
                >
                  {saving ? "Sauvegarde…" : "Valider la facture"}
                </button>
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}

function Field({
  label,
  error,
  full = false,
  children,
}: {
  label: string;
  error?: string;
  full?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={full ? "col-span-2" : ""}>
      <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
      <div
        className={`[&_input]:w-full [&_input]:border [&_input]:rounded-lg [&_input]:px-3 [&_input]:py-2 [&_input]:text-sm [&_input]:focus:outline-none [&_input]:focus:ring-2 [&_input]:focus:ring-brand-500 ${
          error ? "[&_input]:border-red-400" : "[&_input]:border-gray-300"
        }`}
      >
        {children}
      </div>
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="py-24 text-center text-sm text-gray-400">{children}</div>;
}
