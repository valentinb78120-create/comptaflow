import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Files, Loader2, AlertTriangle, CheckCircle2, Plus, Download } from "lucide-react";
import { InvoiceTable } from "../components/InvoiceTable";
import { api } from "../lib/api";
import { useCabinetId } from "../lib/CabinetContext";

export function Dashboard() {
  const cabinetId = useCabinetId();
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [exporting, setExporting] = useState(false);

  const { data: invoices = [], isLoading, isError } = useQuery({
    queryKey: ["invoices", cabinetId, statusFilter],
    queryFn: () => api.listInvoices(cabinetId, statusFilter || undefined),
    refetchInterval: 5000,
  });

  const handleExportAll = async (format: "ebp" | "sage50" | "fec") => {
    setExporting(true);
    const names = { ebp: "EBP", sage50: "Sage 50", fec: "FEC" };
    try {
      await api.exportBulk(cabinetId, format);
      toast.success(`Export ${names[format]} téléchargé`);
    } catch {
      toast.error("Aucune facture validée à exporter");
    } finally {
      setExporting(false);
    }
  };

  const counts = {
    total: invoices.length,
    processing: invoices.filter((i) => i.status === "pending" || i.status === "processing").length,
    review: invoices.filter((i) => i.status === "needs_review").length,
    validated: invoices.filter((i) => i.status === "validated" || i.status === "exported").length,
  };

  return (
    <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-ink-900">Tableau de bord</h1>
          <p className="text-sm text-ink-500 mt-0.5">Vos factures et leur traitement, en temps réel.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => handleExportAll("ebp")} disabled={exporting || counts.validated === 0} className="btn-secondary py-2">
            <Download className="w-4 h-4" /> EBP
          </button>
          <button onClick={() => handleExportAll("sage50")} disabled={exporting || counts.validated === 0} className="btn-secondary py-2">
            <Download className="w-4 h-4" /> Sage 50
          </button>
          <button onClick={() => handleExportAll("fec")} disabled={exporting || counts.validated === 0}
            title="Fichier des Écritures Comptables (DGFiP)" className="btn-secondary py-2">
            <Download className="w-4 h-4" /> FEC
          </button>
          <Link to="/upload" className="btn-primary py-2"><Plus className="w-4 h-4" /> Ajouter</Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Files} label="Total factures" value={counts.total} tone="ink" />
        <StatCard icon={Loader2} label="En traitement" value={counts.processing} tone="blue" />
        <StatCard icon={AlertTriangle} label="À vérifier" value={counts.review} tone="amber" highlight={counts.review > 0} />
        <StatCard icon={CheckCircle2} label="Validées" value={counts.validated} tone="emerald" />
      </div>

      {/* Liste */}
      <section className="card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-display font-bold text-ink-900">Factures</h2>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
            className="text-sm border border-ink-200 rounded-xl px-3 py-1.5 bg-white shadow-soft focus:outline-none focus:ring-4 focus:ring-brand-500/10 focus:border-brand-500">
            <option value="">Tous les statuts</option>
            <option value="pending">En attente</option>
            <option value="processing">Traitement OCR</option>
            <option value="needs_review">À vérifier</option>
            <option value="validated">Validées</option>
            <option value="exported">Exportées</option>
          </select>
        </div>
        {isLoading ? (
          <div className="py-12 text-center text-ink-400 text-sm flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
          </div>
        ) : isError ? (
          <div className="py-12 text-center text-red-500 text-sm">Erreur de chargement — le backend est-il démarré ?</div>
        ) : (
          <InvoiceTable invoices={invoices} onSelect={(inv) => navigate(`/invoices/${inv.id}`)} />
        )}
      </section>
    </main>
  );
}

const TONES = {
  ink: { bg: "bg-ink-100", fg: "text-ink-600", val: "text-ink-900" },
  blue: { bg: "bg-blue-50", fg: "text-blue-600", val: "text-blue-700" },
  amber: { bg: "bg-amber-50", fg: "text-amber-600", val: "text-amber-700" },
  emerald: { bg: "bg-emerald-50", fg: "text-emerald-600", val: "text-emerald-700" },
};

function StatCard({
  icon: Icon, label, value, tone, highlight = false,
}: {
  icon: typeof Files; label: string; value: number; tone: keyof typeof TONES; highlight?: boolean;
}) {
  const t = TONES[tone];
  return (
    <div className={`card p-5 transition-all duration-200 hover:shadow-elevated ${highlight ? "ring-2 ring-amber-200" : ""}`}>
      <div className="flex items-center justify-between">
        <p className="text-sm text-ink-500">{label}</p>
        <span className={`w-8 h-8 rounded-lg ${t.bg} flex items-center justify-center`}>
          <Icon className={`w-4 h-4 ${t.fg}`} />
        </span>
      </div>
      <p className={`text-3xl font-display font-extrabold mt-2 ${t.val}`}>{value}</p>
    </div>
  );
}
