import { useState } from "react";
import { isAxiosError } from "axios";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Sparkles, ShieldCheck, Zap, ArrowRight } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../lib/CabinetContext";
import { Logo } from "../components/Logo";

export function LoginPage() {
  const { loginWithToken, startDemo } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const auth = await api.login({ email, password });
      loginWithToken(auth);
      toast.success(`Bienvenue, ${auth.cabinet.name}`);
      navigate("/dashboard");
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 401) toast.error("Email ou mot de passe incorrect");
      else toast.error("Connexion impossible — le serveur est-il démarré ?");
    } finally {
      setBusy(false);
    }
  };

  const handleDemo = async () => {
    setBusy(true);
    try {
      await startDemo();
      toast.info("Mode démo — les données sont liées à ce navigateur");
      navigate("/dashboard");
    } catch {
      toast.error("Impossible de créer le cabinet démo");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Bon retour" subtitle="Accédez à votre espace cabinet">
      <form onSubmit={handleSubmit} className="space-y-4">
        <AuthField label="Email">
          <input type="email" required value={email} autoComplete="email"
            onChange={(e) => setEmail(e.target.value)} className="input-field" />
        </AuthField>
        <AuthField label="Mot de passe">
          <input type="password" required value={password} autoComplete="current-password"
            onChange={(e) => setPassword(e.target.value)} className="input-field" />
        </AuthField>
        <button type="submit" disabled={busy} className="btn-primary w-full py-3">
          {busy ? "Connexion…" : <>Se connecter <ArrowRight className="w-4 h-4" /></>}
        </button>
      </form>

      <p className="text-center text-sm text-ink-500">
        Pas encore de compte ?{" "}
        <Link to="/register" className="font-semibold text-brand-600 hover:text-brand-700">Créer un compte</Link>
      </p>

      <div className="relative py-1">
        <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-ink-200" /></div>
        <div className="relative flex justify-center"><span className="bg-white px-3 text-xs text-ink-400">ou</span></div>
      </div>

      <button onClick={handleDemo} disabled={busy} className="btn-secondary w-full py-3">
        Essayer sans compte (mode démo)
      </button>
    </AuthShell>
  );
}

/* Coquille auth premium — panneau marketing à gauche, formulaire à droite. */
export function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Panneau marque */}
      <div className="relative hidden lg:flex flex-col justify-between overflow-hidden bg-ink-900 p-12 text-white">
        <div className="absolute inset-0 bg-mesh opacity-80" />
        <div className="absolute inset-0 bg-grid bg-grid opacity-[0.07]" />
        <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-brand-600/30 rounded-full blur-3xl" />
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-accent-500/20 rounded-full blur-3xl" />

        <div className="relative">
          <Logo className="[&_span]:text-white" />
        </div>

        <div className="relative max-w-md">
          <h2 className="font-display text-3xl font-extrabold leading-tight">
            La saisie de factures, <span className="text-brand-300">automatisée</span>.
          </h2>
          <p className="mt-4 text-ink-300">
            Rejoignez les cabinets qui rendent 5 heures par semaine à leur équipe.
          </p>
          <ul className="mt-8 space-y-4">
            <PromoItem icon={Sparkles} text="OCR + catégorisation PCG automatique" />
            <PromoItem icon={ShieldCheck} text="Validation humaine, aucune erreur silencieuse" />
            <PromoItem icon={Zap} text="Exports EBP, Sage 50 et FEC en un clic" />
          </ul>
        </div>

        <div className="relative text-xs text-ink-400">14 jours d'essai · Sans carte bancaire · Données en Europe</div>
      </div>

      {/* Formulaire */}
      <div className="flex items-center justify-center px-6 py-12 bg-white">
        <div className="w-full max-w-sm animate-fade-up">
          <div className="lg:hidden mb-8 flex justify-center"><Logo /></div>
          <div className="text-center mb-8">
            <h1 className="font-display text-2xl font-bold text-ink-900">{title}</h1>
            <p className="mt-1.5 text-sm text-ink-500">{subtitle}</p>
          </div>
          <div className="space-y-5">{children}</div>
        </div>
      </div>
    </div>
  );
}

function PromoItem({ icon: Icon, text }: { icon: typeof Sparkles; text: string }) {
  return (
    <li className="flex items-center gap-3 text-sm text-ink-200">
      <span className="w-9 h-9 rounded-xl bg-white/10 flex items-center justify-center shrink-0">
        <Icon className="w-4 h-4 text-brand-300" />
      </span>
      {text}
    </li>
  );
}

export function AuthField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-ink-600 mb-1.5">{label}</label>
      {children}
    </div>
  );
}
