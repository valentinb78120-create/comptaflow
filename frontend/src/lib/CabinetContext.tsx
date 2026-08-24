import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, tokenStore, type AuthResponse, type Cabinet } from "./api";

const DEMO_KEY = "comptaflow_cabinet_id";

interface AuthState {
  cabinetId: string | null;
  cabinet: Cabinet | null;
  demoMode: boolean;
  loading: boolean;
  loginWithToken: (auth: AuthResponse) => void;
  startDemo: () => Promise<void>;
  logout: () => void;
}

const CabinetContext = createContext<AuthState | null>(null);

/**
 * Gère la session : compte connecté (JWT) ou mode démo (cabinet anonyme).
 * - Token en localStorage → GET /auth/me pour valider et récupérer le cabinet
 * - Sinon, cabinet démo mémorisé → vérifié côté serveur
 * - Sinon → non connecté, le routeur redirige vers /login
 */
export function CabinetProvider({ children }: { children: React.ReactNode }) {
  const [cabinet, setCabinet] = useState<Cabinet | null>(null);
  const [demoMode, setDemoMode] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      // 1. Session authentifiée ?
      if (tokenStore.get()) {
        try {
          setCabinet(await api.me());
          setLoading(false);
          return;
        } catch {
          tokenStore.clear(); // token expiré/invalide
        }
      }
      // 2. Cabinet démo mémorisé ?
      const demoId = localStorage.getItem(DEMO_KEY);
      if (demoId) {
        try {
          setCabinet(await api.getCabinet(demoId));
          setDemoMode(true);
        } catch {
          localStorage.removeItem(DEMO_KEY);
        }
      }
      setLoading(false);
    })();
  }, []);

  const loginWithToken = useCallback((auth: AuthResponse) => {
    tokenStore.set(auth.token);
    localStorage.removeItem(DEMO_KEY);
    setCabinet(auth.cabinet);
    setDemoMode(false);
  }, []);

  const startDemo = useCallback(async () => {
    const demo = await api.createCabinet({
      name: "Cabinet Démo",
      email: `demo-${Date.now()}@comptaflow.fr`,
    });
    localStorage.setItem(DEMO_KEY, demo.id);
    setCabinet(demo);
    setDemoMode(true);
  }, []);

  const logout = useCallback(() => {
    tokenStore.clear();
    localStorage.removeItem(DEMO_KEY);
    setCabinet(null);
    setDemoMode(false);
  }, []);

  return (
    <CabinetContext.Provider
      value={{
        cabinetId: cabinet?.id ?? null,
        cabinet,
        demoMode,
        loading,
        loginWithToken,
        startDemo,
        logout,
      }}
    >
      {children}
    </CabinetContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(CabinetContext);
  if (!ctx) throw new Error("useAuth doit être utilisé sous CabinetProvider");
  return ctx;
}

/** Id du cabinet courant — à utiliser uniquement dans les routes protégées. */
export function useCabinetId(): string {
  const { cabinetId } = useAuth();
  if (!cabinetId) throw new Error("useCabinetId appelé hors session active");
  return cabinetId;
}
