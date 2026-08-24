import { useState } from "react";
import { isAxiosError } from "axios";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api } from "../lib/api";
import { useAuth } from "../lib/CabinetContext";
import { AuthShell, AuthField } from "./Login";

export function RegisterPage() {
  const { loginWithToken } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [busy, setBusy] = useState(false);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password !== form.confirm) {
      toast.error("Les mots de passe ne correspondent pas");
      return;
    }
    if (form.password.length < 8) {
      toast.error("Le mot de passe doit faire au moins 8 caractères");
      return;
    }
    setBusy(true);
    try {
      const auth = await api.register({ name: form.name, email: form.email, password: form.password });
      loginWithToken(auth);
      toast.success("Compte créé — 14 jours d'essai gratuit !");
      navigate("/dashboard");
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 409) {
        toast.error("Cet email a déjà un compte — connectez-vous");
      } else {
        toast.error("Inscription impossible");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Créer un compte" subtitle="14 jours d'essai gratuit, sans carte bancaire">
      <form onSubmit={handleSubmit} className="space-y-4">
        <AuthField label="Nom du cabinet">
          <input required minLength={2} value={form.name} onChange={set("name")} placeholder="Cabinet Dupont & Associés" className="input-field" />
        </AuthField>
        <AuthField label="Email">
          <input type="email" required value={form.email} autoComplete="email" onChange={set("email")} className="input-field" />
        </AuthField>
        <AuthField label="Mot de passe (8 caractères min.)">
          <input type="password" required minLength={8} value={form.password} autoComplete="new-password" onChange={set("password")} className="input-field" />
        </AuthField>
        <AuthField label="Confirmer le mot de passe">
          <input type="password" required value={form.confirm} autoComplete="new-password" onChange={set("confirm")} className="input-field" />
        </AuthField>
        <button type="submit" disabled={busy} className="btn-primary w-full py-3">
          {busy ? "Création…" : "Créer mon compte"}
        </button>
      </form>
      <p className="text-center text-sm text-ink-500">
        Déjà un compte ?{" "}
        <Link to="/login" className="font-semibold text-brand-600 hover:text-brand-700">Se connecter</Link>
      </p>
    </AuthShell>
  );
}
