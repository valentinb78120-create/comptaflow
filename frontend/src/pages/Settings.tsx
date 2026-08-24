import { useState } from "react";
import { isAxiosError } from "axios";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "../lib/api";
import { useAuth, useCabinetId } from "../lib/CabinetContext";
import { formatDate } from "../lib/utils";

export function SettingsPage() {
  const cabinetId = useCabinetId();
  const { cabinet, demoMode } = useAuth();

  const { data: billing } = useQuery({
    queryKey: ["billing", cabinetId],
    queryFn: () => api.billingStatus(cabinetId),
  });

  const queryClient = useQueryClient();

  const { data: rules = [], isLoading: rulesLoading } = useQuery({
    queryKey: ["pcg-rules"],
    queryFn: api.pcgRules,
    staleTime: Infinity, // catalogue statique
  });

  // Règles standard désactivées par CE cabinet (comptes connectés uniquement)
  const { data: disabledKeys = [] } = useQuery({
    queryKey: ["pcg-disabled", cabinetId],
    queryFn: api.disabledRules,
    enabled: !demoMode,
  });
  const disabledSet = new Set(disabledKeys);

  const handleToggleRule = async (key: string, label: string) => {
    try {
      const res = await api.toggleStandardRule(key);
      queryClient.invalidateQueries({ queryKey: ["pcg-disabled"] });
      toast.success(res.disabled ? `Règle « ${label} » désactivée pour votre cabinet` : `Règle « ${label} » réactivée`);
    } catch {
      toast.error("Impossible de modifier cette règle");
    }
  };

  const trialDaysLeft = billing?.trial_ends_at
    ? Math.max(0, Math.ceil((new Date(billing.trial_ends_at).getTime() - Date.now()) / 86_400_000))
    : null;

  return (
    <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-ink-900">Réglages</h1>
        <p className="text-sm text-ink-500 mt-0.5">Votre cabinet, votre abonnement et vos règles.</p>
      </div>

      {/* Cabinet */}
      <section className="card p-6 space-y-4">
        <h2 className="font-display font-bold text-ink-900">Mon cabinet</h2>
        <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
          <InfoRow label="Nom" value={cabinet?.name} />
          <InfoRow label="Email" value={cabinet?.email} />
          <InfoRow label="SIRET" value={cabinet?.siret ?? "—"} />
          <InfoRow label="Compte créé le" value={formatDate(cabinet?.created_at)} />
        </dl>
        {demoMode && (
          <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
            Mode démo : les données sont liées à ce navigateur. Créez un compte pour les sécuriser.
          </p>
        )}
      </section>

      {/* Abonnement & consommation */}
      <section className="card p-6 space-y-4">
        <h2 className="font-display font-bold text-ink-900">Abonnement</h2>
        {billing ? (
          <div className="space-y-4 text-sm">
            <div className="flex items-center gap-3">
              <StatusDot ok={billing.has_access} />
              {billing.subscription_active ? (
                <span className="text-gray-700">
                  Plan <strong>{billing.plan_label}</strong> actif
                  {billing.plan_price_eur != null && <> — {billing.plan_price_eur} €/mois</>}
                </span>
              ) : billing.trial_active ? (
                <span className="text-gray-700">
                  Période d'essai (plan {billing.plan_label}) —{" "}
                  <strong>{trialDaysLeft} jour{(trialDaysLeft ?? 0) > 1 ? "s" : ""} restant{(trialDaysLeft ?? 0) > 1 ? "s" : ""}</strong>
                  {billing.trial_ends_at && <span className="text-gray-400"> (jusqu'au {formatDate(billing.trial_ends_at)})</span>}
                </span>
              ) : (
                <span className="text-red-600">Essai terminé — abonnement requis pour continuer</span>
              )}
            </div>

            {/* Jauge de consommation mensuelle */}
            {billing.monthly_limit != null && (
              <div className="max-w-md space-y-1.5">
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Factures ce mois-ci</span>
                  <span className={billing.monthly_used >= billing.monthly_limit ? "text-red-600 font-semibold" : ""}>
                    {billing.monthly_used} / {billing.monthly_limit}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      billing.monthly_used >= billing.monthly_limit
                        ? "bg-red-500"
                        : billing.monthly_used / billing.monthly_limit > 0.8
                        ? "bg-amber-500"
                        : "bg-brand-600"
                    }`}
                    style={{ width: `${Math.min(100, (billing.monthly_used / billing.monthly_limit) * 100)}%` }}
                  />
                </div>
                {billing.monthly_used / billing.monthly_limit > 0.8 && (
                  <p className="text-xs text-amber-700">
                    Vous approchez de votre quota — pensez au plan supérieur.
                  </p>
                )}
              </div>
            )}

            {!billing.stripe_configured && (
              <p className="text-xs text-gray-400">
                Paiement non configuré sur ce serveur (mode développement) — l'essai reste utilisable.
              </p>
            )}
          </div>
        ) : (
          <p className="text-sm text-gray-400">Chargement…</p>
        )}
      </section>

      {/* Sécurité */}
      {!demoMode && <SecuritySection />}

      {/* Règles personnalisées */}
      {!demoMode && <CustomRulesSection />}

      {/* Règles PCG standard */}
      <section className="card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-display font-bold text-ink-900">Catégorisation standard (PCG)</h2>
          <span className="text-xs text-gray-400">
            {rules.length - disabledSet.size}/{rules.length} règles actives
          </span>
        </div>
        <p className="text-sm text-gray-500">
          Quand un mot-clé est détecté dans le nom du fournisseur ou la facture, le compte est proposé
          automatiquement. Vos règles personnalisées (ci-dessus) sont prioritaires.
          {!demoMode && " Vous pouvez désactiver une règle qui ne convient pas à votre cabinet."}
        </p>
        {rulesLoading ? (
          <p className="text-sm text-gray-400">Chargement…</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-gray-200 max-h-96 overflow-y-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 border-b border-gray-200 sticky top-0">
                <tr>
                  <th className="px-4 py-2.5 font-medium text-gray-600">Compte</th>
                  <th className="px-4 py-2.5 font-medium text-gray-600">Libellé</th>
                  <th className="px-4 py-2.5 font-medium text-gray-600">Mots-clés détectés</th>
                  <th className="px-4 py-2.5 font-medium text-gray-600">Origine</th>
                  {!demoMode && <th className="px-4 py-2.5 font-medium text-gray-600">Action</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {rules.map((r) => {
                  const isDisabled = disabledSet.has(r.key);
                  return (
                    <tr key={r.key} className={isDisabled ? "opacity-45 bg-gray-50" : ""}>
                      <td className="px-4 py-2.5 font-mono text-gray-900">{r.account}</td>
                      <td className="px-4 py-2.5 text-gray-700">
                        {r.label}
                        {isDisabled && (
                          <span className="ml-2 text-xs bg-gray-200 text-gray-500 rounded px-1.5 py-0.5">désactivée</span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-gray-500">
                        <span className="line-clamp-1">{r.keywords.join(", ")}</span>
                      </td>
                      <td className="px-4 py-2.5">
                        <span className="text-xs bg-blue-50 text-blue-600 rounded px-1.5 py-0.5">par défaut</span>
                      </td>
                      {!demoMode && (
                        <td className="px-4 py-2.5">
                          <button
                            onClick={() => handleToggleRule(r.key, r.label)}
                            className={`text-xs border rounded px-2 py-1 ${
                              isDisabled
                                ? "border-green-200 text-green-700 hover:bg-green-50"
                                : "border-gray-300 text-gray-500 hover:bg-gray-100"
                            }`}
                          >
                            {isDisabled ? "Réactiver" : "Désactiver"}
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

/** Changement de mot de passe (comptes inscrits uniquement). */
function SecuritySection() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (next !== confirm) {
      toast.error("Les nouveaux mots de passe ne correspondent pas");
      return;
    }
    if (next.length < 8) {
      toast.error("8 caractères minimum");
      return;
    }
    setBusy(true);
    try {
      await api.changePassword(current, next);
      toast.success("Mot de passe modifié ✓");
      setCurrent(""); setNext(""); setConfirm("");
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 401) {
        toast.error("Mot de passe actuel incorrect");
      } else {
        toast.error("Échec du changement de mot de passe");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card p-6 space-y-4">
      <h2 className="font-display font-bold text-ink-900">Sécurité</h2>
      <form onSubmit={handleSubmit} className="grid grid-cols-3 gap-4 items-end max-w-2xl">
        <PwdField label="Mot de passe actuel" value={current} onChange={setCurrent} autoComplete="current-password" />
        <PwdField label="Nouveau (8 car. min.)" value={next} onChange={setNext} autoComplete="new-password" />
        <PwdField label="Confirmer" value={confirm} onChange={setConfirm} autoComplete="new-password" />
        <div className="col-span-3">
          <button
            type="submit" disabled={busy || !current || !next}
            className="px-4 py-2 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-40"
          >
            {busy ? "Modification…" : "Changer le mot de passe"}
          </button>
        </div>
      </form>
    </section>
  );
}

function PwdField({ label, value, onChange, autoComplete }: {
  label: string; value: string; onChange: (v: string) => void; autoComplete: string;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
      <input
        type="password" value={value} autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
    </div>
  );
}

/** Règles PCG personnalisées du cabinet (prioritaires sur le standard). */
function CustomRulesSection() {
  const queryClient = useQueryClient();
  const [keywords, setKeywords] = useState("");
  const [account, setAccount] = useState("");
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);

  const { data: customRules = [] } = useQuery({
    queryKey: ["custom-rules"],
    queryFn: api.customRules,
  });

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const kw = keywords.split(",").map((k) => k.trim()).filter(Boolean);
    if (!kw.length) { toast.error("Au moins un mot-clé"); return; }
    if (!/^\d{6,8}$/.test(account)) { toast.error("Compte PCG : 6 à 8 chiffres"); return; }
    if (label.trim().length < 2) { toast.error("Libellé requis"); return; }

    setBusy(true);
    try {
      await api.createCustomRule({ keywords: kw, account, label: label.trim() });
      queryClient.invalidateQueries({ queryKey: ["custom-rules"] });
      setKeywords(""); setAccount(""); setLabel("");
      toast.success("Règle ajoutée — elle s'appliquera aux prochaines factures");
    } catch {
      toast.error("Impossible d'ajouter la règle");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteCustomRule(id);
      queryClient.invalidateQueries({ queryKey: ["custom-rules"] });
      toast.success("Règle supprimée");
    } catch {
      toast.error("Suppression impossible");
    }
  };

  return (
    <section className="card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-display font-bold text-ink-900">Mes règles de catégorisation</h2>
        <span className="text-xs text-gray-400">{customRules.length} règle{customRules.length > 1 ? "s" : ""}</span>
      </div>
      <p className="text-sm text-gray-500">
        Vos règles sont évaluées <strong>avant</strong> les règles standard — idéal pour vos fournisseurs récurrents.
      </p>

      {/* Formulaire d'ajout */}
      <form onSubmit={handleAdd} className="grid grid-cols-[2fr_1fr_2fr_auto] gap-3 items-end">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Mots-clés (séparés par des virgules)</label>
          <input
            value={keywords} onChange={(e) => setKeywords(e.target.value)}
            placeholder="ex : boulangerie dupont, traiteur martin"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Compte PCG</label>
          <input
            value={account} onChange={(e) => setAccount(e.target.value)}
            placeholder="606300"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Libellé</label>
          <input
            value={label} onChange={(e) => setLabel(e.target.value)}
            placeholder="ex : Frais de réception"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <button
          type="submit" disabled={busy}
          className="px-4 py-2 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-40"
        >
          Ajouter
        </button>
      </form>

      {/* Liste */}
      {customRules.length > 0 && (
        <div className="rounded-xl border border-gray-200 divide-y divide-gray-100">
          {customRules.map((r) => (
            <div key={r.id} className="flex items-center gap-4 px-4 py-2.5 text-sm">
              <span className="font-mono text-gray-900 w-20">{r.account}</span>
              <span className="text-gray-700 flex-1">{r.label}</span>
              <span className="text-gray-400 truncate max-w-[280px]">{r.keywords.join(", ")}</span>
              <button
                onClick={() => handleDelete(r.id)}
                className="text-xs text-red-500 hover:text-red-700 border border-red-200 rounded px-2 py-1 hover:bg-red-50"
              >
                Supprimer
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function InfoRow({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-gray-400 text-xs">{label}</dt>
      <dd className="text-gray-900 mt-0.5">{value ?? "—"}</dd>
    </div>
  );
}

function StatusDot({ ok }: { ok: boolean }) {
  return <span className={`w-2.5 h-2.5 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`} />;
}
