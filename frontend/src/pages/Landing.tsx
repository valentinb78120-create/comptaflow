import { Link } from "react-router-dom";
import {
  ScanLine, Sparkles, CheckCircle2, FileSpreadsheet, ShieldCheck,
  Layers, Zap, ArrowRight, Upload, BrainCircuit, FileCheck2, Download,
} from "lucide-react";
import { useAuth } from "../lib/CabinetContext";
import { Logo } from "../components/Logo";

/** Page vitrine publique — design premium. */
export function LandingPage() {
  const { cabinetId } = useAuth();

  return (
    <div className="min-h-screen bg-white text-ink-800 overflow-x-hidden">
      {/* ---------- Header ---------- */}
      <header className="sticky top-0 z-40">
        <div className="glass border-b border-ink-200/50">
          <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
            <Logo />
            <nav className="flex items-center gap-2 sm:gap-3">
              {cabinetId ? (
                <Link to="/dashboard" className="btn-primary">
                  Tableau de bord <ArrowRight className="w-4 h-4" />
                </Link>
              ) : (
                <>
                  <Link to="/login" className="hidden sm:inline-flex px-4 py-2 text-sm font-medium text-ink-600 hover:text-ink-900 transition-colors">
                    Connexion
                  </Link>
                  <Link to="/register" className="btn-primary">
                    Essai gratuit <ArrowRight className="w-4 h-4" />
                  </Link>
                </>
              )}
            </nav>
          </div>
        </div>
      </header>

      {/* ---------- Hero ---------- */}
      <section className="relative">
        {/* Décor de fond */}
        <div className="absolute inset-0 bg-mesh" />
        <div className="absolute inset-0 bg-grid bg-grid [mask-image:radial-gradient(ellipse_at_center,black,transparent_70%)]" />
        <div className="absolute top-20 -left-20 w-72 h-72 bg-brand-400/20 rounded-full blur-3xl animate-float" />
        <div className="absolute top-40 -right-10 w-72 h-72 bg-accent-400/20 rounded-full blur-3xl animate-float" style={{ animationDelay: "2s" }} />

        <div className="relative max-w-4xl mx-auto px-6 pt-20 pb-24 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50/80 px-4 py-1.5 text-sm font-medium text-brand-700 animate-fade-up">
            <Sparkles className="w-4 h-4" />
            Pour les cabinets d'expertise comptable
          </div>

          <h1 className="mt-6 font-display text-display-sm sm:text-display-md font-extrabold text-ink-900 animate-fade-up delay-1">
            La saisie de factures,
            <br />
            <span className="text-gradient">en 10 secondes</span> au lieu de 10 minutes
          </h1>

          <p className="mt-6 text-lg text-ink-500 max-w-2xl mx-auto leading-relaxed animate-fade-up delay-2">
            Glissez une facture, ComptaFlow lit le fournisseur, les montants et la TVA,
            propose le compte PCG, et exporte des écritures prêtes pour EBP, Sage 50 ou le FEC.
          </p>

          <div className="mt-9 flex flex-col sm:flex-row items-center justify-center gap-3 animate-fade-up delay-3">
            <Link to="/register" className="btn-primary text-base px-7 py-3.5">
              Commencer gratuitement <ArrowRight className="w-5 h-5" />
            </Link>
            <Link to="/login" className="btn-secondary text-base px-7 py-3.5">
              Voir une démo
            </Link>
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-ink-400 animate-fade-up delay-4">
            <span className="inline-flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-brand-500" /> 14 jours d'essai</span>
            <span className="inline-flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-brand-500" /> Sans carte bancaire</span>
            <span className="inline-flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-brand-500" /> Données en Europe</span>
          </div>

          {/* Aperçu produit factice */}
          <div className="mt-16 animate-scale-in delay-4">
            <MockupCard />
          </div>
        </div>
      </section>

      {/* ---------- Comment ça marche ---------- */}
      <section className="py-24 bg-ink-50/60 border-y border-ink-200/60">
        <div className="max-w-5xl mx-auto px-6">
          <SectionTitle eyebrow="Workflow" title="Quatre étapes, zéro friction" />
          <div className="mt-14 grid sm:grid-cols-4 gap-8">
            <Step icon={Upload} n="1" title="Déposez" text="Glissez vos factures PDF ou photos, par lot." />
            <Step icon={BrainCircuit} n="2" title="L'IA extrait" text="Fournisseur, dates, HT, TVA, TTC lus automatiquement." />
            <Step icon={FileCheck2} n="3" title="Vous validez" text="Le compte PCG est proposé. Un clic pour corriger." />
            <Step icon={Download} n="4" title="Vous exportez" text="Écritures prêtes pour EBP, Sage 50 ou FEC." />
          </div>
        </div>
      </section>

      {/* ---------- Features ---------- */}
      <section className="py-24">
        <div className="max-w-5xl mx-auto px-6">
          <SectionTitle eyebrow="Fonctionnalités" title="Tout ce qu'un cabinet attend" />
          <div className="mt-14 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            <Feature icon={Sparkles} title="Catégorisation PCG auto" text="36 règles standard + vos propres règles par cabinet, prioritaires." />
            <Feature icon={ShieldCheck} title="Validation humaine" text="Aucune écriture douteuse ne passe : tout l'incertain est marqué à vérifier." />
            <Feature icon={Layers} title="Anti-doublon" text="Une facture déjà saisie est détectée et refusée. Fini la double saisie." />
            <Feature icon={FileSpreadsheet} title="Exports natifs" text="CSV EBP, Sage 50, et FEC conforme à l'article A47 A-1 du LPF." />
            <Feature icon={Zap} title="OCR à deux étages" text="Mistral AI pour la précision, repli local : le service ne s'arrête jamais." />
            <Feature icon={ScanLine} title="Multi-dossiers" text="Chaque cabinet voit uniquement ses données. Accès sécurisé par compte." />
          </div>
        </div>
      </section>

      {/* ---------- Pricing ---------- */}
      <section className="py-24 bg-ink-50/60 border-t border-ink-200/60">
        <div className="max-w-6xl mx-auto px-6">
          <SectionTitle eyebrow="Tarifs" title="Un prix simple, par volume" subtitle="14 jours d'essai gratuit sur tous les plans, sans carte bancaire." />
          <div className="mt-14 grid sm:grid-cols-2 lg:grid-cols-4 gap-5 items-stretch">
            <PriceCard name="Découverte" price="29 €" priceSuffix="/ mois" quota="100 factures / mois"
              features={["OCR + catégorisation PCG", "Exports EBP, Sage 50, FEC", "Règles personnalisées"]} />
            <PriceCard name="Cabinet" price="79 €" priceSuffix="/ mois" quota="1 000 factures / mois"
              features={["Tout Découverte", "Volume adapté aux cabinets", "Support par email"]} highlight />
            <PriceCard name="Cabinet+" price="199 €" priceSuffix="/ mois" quota="5 000 factures / mois"
              features={["Tout Cabinet", "Gros volumes", "Support prioritaire"]} />
            <PriceCard name="Illimité" price="Sur devis" quota="Factures illimitées"
              features={["Tout Cabinet+", "Multi-sites & gros groupes", "Accompagnement dédié"]}
              cta="Nous contacter" href="mailto:contact@comptaflow.fr?subject=Plan%20Illimit%C3%A9%20ComptaFlow" dark />
          </div>
        </div>
      </section>

      {/* ---------- CTA final ---------- */}
      <section className="py-24">
        <div className="max-w-4xl mx-auto px-6">
          <div className="relative overflow-hidden rounded-4xl bg-brand-gradient px-8 py-16 text-center shadow-float">
            <div className="absolute inset-0 bg-grid bg-grid opacity-20" />
            <div className="relative">
              <h2 className="font-display text-3xl sm:text-4xl font-extrabold text-white">
                Rendez 5 heures par semaine à votre équipe
              </h2>
              <p className="mt-4 text-brand-100 max-w-xl mx-auto">
                Testez ComptaFlow gratuitement pendant 14 jours. Une démo se fait en direct avec une de vos vraies factures.
              </p>
              <Link to="/register" className="mt-8 inline-flex items-center gap-2 rounded-xl bg-white px-7 py-3.5 text-base font-semibold text-brand-700 shadow-elevated transition-all hover:-translate-y-0.5 hover:shadow-float">
                Démarrer l'essai gratuit <ArrowRight className="w-5 h-5" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ---------- Footer ---------- */}
      <footer className="border-t border-ink-200/60 py-10">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <Logo />
          <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs text-ink-400">
            <span>© {new Date().getFullYear()} ComptaFlow</span>
            <span>Mentions légales</span>
            <span>CGV</span>
            <span>contact@comptaflow.fr</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

/* ----------------------------- Sous-composants ----------------------------- */

function SectionTitle({ eyebrow, title, subtitle }: { eyebrow: string; title: string; subtitle?: string }) {
  return (
    <div className="text-center max-w-2xl mx-auto">
      <p className="text-sm font-semibold text-brand-600 uppercase tracking-wider">{eyebrow}</p>
      <h2 className="mt-2 font-display text-3xl sm:text-4xl font-extrabold text-ink-900">{title}</h2>
      {subtitle && <p className="mt-3 text-ink-500">{subtitle}</p>}
    </div>
  );
}

function MockupCard() {
  return (
    <div className="relative max-w-3xl mx-auto">
      <div className="card shadow-float overflow-hidden text-left">
        {/* Barre fenêtre */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-ink-100 bg-ink-50/50">
          <span className="w-3 h-3 rounded-full bg-red-300" />
          <span className="w-3 h-3 rounded-full bg-amber-300" />
          <span className="w-3 h-3 rounded-full bg-green-300" />
          <span className="ml-3 text-xs text-ink-400">comptaflow.fr/dashboard</span>
        </div>
        <div className="p-6 grid sm:grid-cols-3 gap-4">
          {[
            { l: "À vérifier", v: "3", c: "amber" },
            { l: "Validées", v: "128", c: "emerald" },
            { l: "Ce mois", v: "412", c: "brand" },
          ].map((s) => (
            <div key={s.l} className="rounded-2xl border border-ink-100 p-4">
              <p className="text-xs text-ink-400">{s.l}</p>
              <p className={`mt-1 text-2xl font-bold ${s.c === "amber" ? "text-amber-600" : s.c === "emerald" ? "text-emerald-600" : "text-brand-600"}`}>{s.v}</p>
            </div>
          ))}
        </div>
        <div className="px-6 pb-6 space-y-2">
          {[
            { f: "EDF — facture avril", a: "120,00 €", p: "606100", ok: true },
            { f: "Orange Business", a: "59,90 €", p: "626000", ok: true },
            { f: "SNCF — déplacement", a: "84,00 €", p: "625100", ok: false },
          ].map((r) => (
            <div key={r.f} className="flex items-center gap-3 rounded-xl border border-ink-100 px-4 py-3 text-sm">
              <FileCheck2 className="w-4 h-4 text-ink-300 shrink-0" />
              <span className="flex-1 text-ink-700 truncate">{r.f}</span>
              <span className="font-mono text-ink-500">{r.a}</span>
              <span className="font-mono text-xs text-brand-600 bg-brand-50 rounded px-1.5 py-0.5">{r.p}</span>
              <span className={`text-xs rounded-full px-2 py-0.5 ${r.ok ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"}`}>
                {r.ok ? "Validée" : "À vérifier"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Step({ icon: Icon, n, title, text }: { icon: typeof Upload; n: string; title: string; text: string }) {
  return (
    <div className="relative text-center">
      <div className="relative mx-auto w-14 h-14 rounded-2xl bg-white border border-ink-200 shadow-card flex items-center justify-center">
        <Icon className="w-6 h-6 text-brand-600" />
        <span className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-brand-gradient text-white text-xs font-bold flex items-center justify-center shadow-glow">{n}</span>
      </div>
      <h3 className="mt-4 font-semibold text-ink-900">{title}</h3>
      <p className="mt-1 text-sm text-ink-500">{text}</p>
    </div>
  );
}

function Feature({ icon: Icon, title, text }: { icon: typeof Upload; title: string; text: string }) {
  return (
    <div className="group card p-6 transition-all duration-200 hover:shadow-elevated hover:-translate-y-1">
      <div className="w-11 h-11 rounded-xl bg-brand-50 flex items-center justify-center transition-colors group-hover:bg-brand-gradient">
        <Icon className="w-5 h-5 text-brand-600 transition-colors group-hover:text-white" />
      </div>
      <h3 className="mt-4 font-semibold text-ink-900">{title}</h3>
      <p className="mt-2 text-sm text-ink-500 leading-relaxed">{text}</p>
    </div>
  );
}

function PriceCard({
  name, price, priceSuffix, quota, features, highlight = false, dark = false,
  cta = "Essayer 14 jours", href,
}: {
  name: string; price: string; priceSuffix?: string; quota: string; features: string[];
  highlight?: boolean; dark?: boolean; cta?: string; href?: string;
}) {
  const ctaClass = highlight ? "btn-primary w-full" : dark
    ? "w-full inline-flex items-center justify-center rounded-xl bg-white px-5 py-2.5 text-sm font-semibold text-ink-900 transition-all hover:-translate-y-0.5"
    : "btn-secondary w-full";

  return (
    <div className={`relative rounded-3xl p-7 flex flex-col transition-all duration-200 hover:-translate-y-1 ${
      dark ? "bg-ink-900 text-white shadow-float"
        : highlight ? "bg-white border-2 border-brand-500 shadow-glow hover:shadow-glow-lg"
        : "bg-white border border-ink-200 shadow-card hover:shadow-elevated"
    }`}>
      {highlight && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-brand-gradient px-3 py-1 text-xs font-semibold text-white shadow-glow">
          Le plus choisi
        </span>
      )}
      <p className={`text-sm font-semibold ${dark ? "text-brand-300" : "text-brand-600"}`}>{name}</p>
      <p className="mt-2">
        <span className={`font-display font-extrabold ${price.length > 6 ? "text-3xl" : "text-4xl"} ${dark ? "text-white" : "text-ink-900"}`}>{price}</span>
        {priceSuffix && <span className={`text-sm ${dark ? "text-ink-400" : "text-ink-400"}`}> {priceSuffix}</span>}
      </p>
      <p className={`mt-1 text-sm font-medium ${dark ? "text-ink-300" : "text-ink-600"}`}>{quota}</p>
      <ul className={`mt-5 space-y-2.5 text-sm flex-1 ${dark ? "text-ink-300" : "text-ink-600"}`}>
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2">
            <CheckCircle2 className={`w-4 h-4 mt-0.5 shrink-0 ${dark ? "text-brand-400" : "text-brand-500"}`} />
            {f}
          </li>
        ))}
      </ul>
      {href ? <a href={href} className={`mt-6 ${ctaClass}`}>{cta}</a> : <Link to="/register" className={`mt-6 ${ctaClass}`}>{cta}</Link>}
    </div>
  );
}
