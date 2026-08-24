import { Navigate, NavLink, Outlet, useNavigate } from "react-router-dom";
import { LayoutDashboard, Upload, Settings, ShieldCheck, LogOut } from "lucide-react";
import { cn } from "../lib/utils";
import { useAuth } from "../lib/CabinetContext";
import { Logo } from "./Logo";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-xl transition-all duration-150",
    isActive
      ? "bg-brand-50 text-brand-700 font-semibold shadow-soft"
      : "text-ink-500 hover:text-ink-900 hover:bg-ink-100/70"
  );

/** Coquille des pages protégées : exige une session, sinon redirige vers /login. */
export function Layout() {
  const { cabinet, cabinetId, demoMode, loading, logout } = useAuth();
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-ink-50">
        <div className="flex items-center gap-3 text-ink-400">
          <span className="w-5 h-5 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
          <span className="text-sm">Chargement…</span>
        </div>
      </div>
    );
  }

  if (!cabinetId) return <Navigate to="/login" replace />;

  const handleLogout = () => { logout(); navigate("/login"); };

  return (
    <div className="min-h-screen bg-ink-50/50">
      <header className="sticky top-0 z-30 glass border-b border-ink-200/60">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Logo to="/dashboard" />
            <nav className="hidden md:flex items-center gap-1">
              <NavLink to="/dashboard" className={navLinkClass}><LayoutDashboard className="w-4 h-4" /> Tableau de bord</NavLink>
              <NavLink to="/upload" className={navLinkClass}><Upload className="w-4 h-4" /> Ajouter</NavLink>
              <NavLink to="/settings" className={navLinkClass}><Settings className="w-4 h-4" /> Réglages</NavLink>
              {cabinet?.is_admin && (
                <NavLink to="/admin" className={navLinkClass}><ShieldCheck className="w-4 h-4" /> Admin</NavLink>
              )}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2">
              <span className="text-sm font-medium text-ink-700">{cabinet?.name}</span>
              {demoMode && <span className="text-xs bg-amber-100 text-amber-700 rounded-full px-2 py-0.5 font-medium">démo</span>}
              {cabinet?.is_admin && <span className="text-xs bg-accent-500/10 text-accent-600 rounded-full px-2 py-0.5 font-medium">admin</span>}
            </div>
            <button onClick={handleLogout}
              className="inline-flex items-center gap-1.5 text-sm text-ink-500 hover:text-ink-900 border border-ink-200 rounded-xl px-3 py-1.5 hover:bg-white transition-colors">
              <LogOut className="w-4 h-4" /> <span className="hidden sm:inline">Déconnexion</span>
            </button>
          </div>
        </div>
      </header>
      <div className="animate-fade-in"><Outlet /></div>
    </div>
  );
}
