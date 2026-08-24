import { Link } from "react-router-dom";

/** Logo ComptaFlow — pastille dégradée + wordmark. */
export function Logo({ to = "/", className = "" }: { to?: string; className?: string }) {
  return (
    <Link to={to} className={`flex items-center gap-2.5 group ${className}`}>
      <div className="relative w-9 h-9 rounded-xl bg-brand-gradient flex items-center justify-center shadow-glow transition-transform duration-200 group-hover:scale-105">
        <span className="text-white text-sm font-bold font-display tracking-tight">CF</span>
        <div className="absolute inset-0 rounded-xl ring-1 ring-inset ring-white/20" />
      </div>
      <span className="font-display font-bold text-ink-900 text-lg tracking-tight">
        Compta<span className="text-gradient">Flow</span>
      </span>
    </Link>
  );
}
