import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import { toast } from "sonner";
import { api, PLAN_LABELS } from "../lib/api";
import { useAuth } from "../lib/CabinetContext";
import { formatDate, STATUS_LABELS } from "../lib/utils";
import type { InvoiceStatus } from "../types/invoice";

/** Back-office plateforme — visible uniquement pour les comptes admin. */
export function AdminPage() {
  const { cabinet } = useAuth();
  const queryClient = useQueryClient();

  const { data: stats } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: api.adminStats,
    refetchInterval: 15_000,
    enabled: !!cabinet?.is_admin,
  });

  const { data: cabinets = [], isLoading } = useQuery({
    queryKey: ["admin-cabinets"],
    queryFn: api.adminCabinets,
    enabled: !!cabinet?.is_admin,
  });

  // Garde côté client (le backend renvoie de toute façon 403)
  if (cabinet && !cabinet.is_admin) {
    return <Navigate to="/dashboard" replace />;
  }

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["admin-cabinets"] });
    queryClient.invalidateQueries({ queryKey: ["admin-stats"] });
  };

  const handleExtendTrial = async (id: string, name: string) => {
    try {
      await api.adminExtendTrial(id, 14);
      toast.success(`Essai prolongé de 14 jours pour ${name}`);
      refresh();
    } catch {
      toast.error("Échec de la prolongation");
    }
  };

  const handleToggleSub = async (id: string, name: string) => {
    try {
      const updated = await api.adminToggleSubscription(id);
      toast.success(`Abonnement ${updated.subscription_active ? "activé" : "coupé"} pour ${name}`);
      refresh();
    } catch {
      toast.error("Échec du changement d'abonnement");
    }
  };

  const handleSetPlan = async (id: string, name: string, plan: string) => {
    try {
      await api.adminSetPlan(id, plan);
      toast.success(`${name} → plan ${PLAN_LABELS[plan] ?? plan}`);
      refresh();
    } catch {
      toast.error("Échec du changement de plan");
    }
  };

  return (
    <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="font-display text-2xl font-bold text-ink-900">Administration</h1>
        <span className="text-xs bg-accent-500/10 text-accent-600 rounded-full px-2.5 py-0.5 font-medium">back-office</span>
      </div>

      {/* KPIs plateforme */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <Kpi label="Cabinets" value={stats?.cabinets_total} />
        <Kpi label="Abonnés payants" value={stats?.cabinets_subscribed} highlight />
        <Kpi label="En essai" value={stats?.cabinets_in_trial} />
        <Kpi label="Factures totales" value={stats?.invoices_total} />
        <Kpi label="Factures (7 jours)" value={stats?.invoices_last_7d} />
      </div>

      {/* Répartition par statut */}
      {stats && (
        <section className="card p-6">
          <h2 className="font-display font-bold text-ink-900 mb-4">Factures par statut</h2>
          <div className="flex gap-6 flex-wrap text-sm">
            {Object.entries(stats.invoices_by_status).map(([s, count]) => (
              <div key={s} className="flex items-center gap-2">
                <span className="text-gray-500">{STATUS_LABELS[s as InvoiceStatus] ?? s} :</span>
                <span className="font-semibold text-gray-900">{count}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Cabinets */}
      <section className="card p-6 space-y-4">
        <h2 className="font-display font-bold text-ink-900">Cabinets ({cabinets.length})</h2>
        {isLoading ? (
          <p className="text-sm text-gray-400 py-6 text-center">Chargement…</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-gray-200">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 font-medium text-gray-600">Cabinet</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Email</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Factures</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Plan</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Statut</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Créé le</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {cabinets.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {c.name}
                      {c.is_admin && <span className="ml-2 text-xs bg-purple-100 text-purple-700 rounded px-1.5 py-0.5">admin</span>}
                    </td>
                    <td className="px-4 py-3 text-gray-500 truncate max-w-[220px]">{c.email}</td>
                    <td className="px-4 py-3 text-gray-700">{c.invoice_count}</td>
                    <td className="px-4 py-3">
                      <select
                        value={c.plan}
                        onChange={(e) => handleSetPlan(c.id, c.name, e.target.value)}
                        className="text-xs border border-gray-200 rounded px-1.5 py-1 bg-white"
                      >
                        {Object.entries(PLAN_LABELS).map(([k, v]) => (
                          <option key={k} value={k}>{v}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3"><AccessBadge cabinet={c} /></td>
                    <td className="px-4 py-3 text-gray-500">{formatDate(c.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleExtendTrial(c.id, c.name)}
                          className="text-xs border border-gray-300 rounded px-2 py-1 hover:bg-gray-100"
                          title="Prolonger l'essai de 14 jours"
                        >
                          +14j essai
                        </button>
                        <button
                          onClick={() => handleToggleSub(c.id, c.name)}
                          className={`text-xs border rounded px-2 py-1 ${
                            c.subscription_active
                              ? "border-red-200 text-red-600 hover:bg-red-50"
                              : "border-green-200 text-green-700 hover:bg-green-50"
                          }`}
                        >
                          {c.subscription_active ? "Couper abo" : "Activer abo"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

function Kpi({ label, value, highlight = false }: { label: string; value: number | undefined; highlight?: boolean }) {
  return (
    <div className={`card p-4 ${highlight ? "ring-2 ring-emerald-200 bg-emerald-50/40" : ""}`}>
      <p className="text-xs text-ink-500">{label}</p>
      <p className={`text-2xl font-display font-extrabold mt-1 ${highlight ? "text-emerald-700" : "text-ink-900"}`}>{value ?? "…"}</p>
    </div>
  );
}

function AccessBadge({ cabinet }: { cabinet: { subscription_active: boolean; trial_ends_at: string | null } }) {
  if (cabinet.subscription_active) {
    return <span className="text-xs bg-green-100 text-green-700 rounded-full px-2.5 py-0.5">Abonné</span>;
  }
  const trialActive = cabinet.trial_ends_at && new Date(cabinet.trial_ends_at) > new Date();
  if (trialActive) {
    return <span className="text-xs bg-blue-100 text-blue-700 rounded-full px-2.5 py-0.5">Essai</span>;
  }
  return <span className="text-xs bg-gray-100 text-gray-500 rounded-full px-2.5 py-0.5">Expiré</span>;
}
