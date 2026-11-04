// Корневой компонент: сеанс, маршруты и общий макет
import { useCallback, useEffect, useState } from "react";
import { ContextBar } from "./components/ContextBar";
import { Header, tabsFor } from "./components/Header";
import { useHashRoute } from "./hooks/useHashRoute";
import { AuditPage } from "./pages/AuditPage";
import { HeatmapPage } from "./pages/HeatmapPage";
import { ImportPage } from "./pages/ImportPage";
import { LoginPage, ResetPage } from "./pages/LoginPage";
import { OverviewPage } from "./pages/OverviewPage";
import { ReportsPage } from "./pages/ReportsPage";
import { RisksPage } from "./pages/RisksPage";
import { UsersPage } from "./pages/UsersPage";
import { api, hasToken, setToken } from "./services/api";
import type { Period, User } from "./services/types";
import { SessionContext } from "./session";

const PAGES: Record<string, () => React.JSX.Element> = {
  overview: OverviewPage, risks: RisksPage, heatmap: HeatmapPage,
  import: ImportPage, reports: ReportsPage, users: UsersPage,
  audit: AuditPage,
};

export function App() {
  const [route, query] = useHashRoute();
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(hasToken());
  const [latest, setLatest] = useState<Period | null>(null);
  const [period, setPeriod] = useState<Period | null>(null);
  const [toast, setToast] = useState<{ text: string; tone: string } | null>(
    null);

  useEffect(() => {
    if (!hasToken()) return;
    api.me().then(setUser).catch(() => setToken(null))
      .finally(() => setChecking(false));
  }, []);

  useEffect(() => {
    const logout = () => { setToken(null); setUser(null); };
    window.addEventListener("auditxp:logout", logout);
    return () => window.removeEventListener("auditxp:logout", logout);
  }, []);

  useEffect(() => {
    if (!user) return;
    api.overview().then((o) => {
      const p = { date_from: o.period_from, date_to: o.period_to };
      setLatest(p);
      setPeriod((current) => current ?? p);
    }).catch(() => undefined);
  }, [user]);

  const notify = useCallback((text: string, tone = "success") => {
    setToast({ text, tone });
    window.setTimeout(() => setToast(null), 4000);
  }, []);

  if (route === "reset") return <ResetPage token={query.get("token")} />;
  if (checking) return <div className="splash">Загрузка…</div>;
  if (!user) return <LoginPage onLogin={setUser} />;
  if (!period || !latest) return <div className="splash">Загрузка…</div>;

  const allowed = tabsFor(user.role_name).map((t) => t.id);
  const Page = PAGES[allowed.includes(route) ? route : "overview"];
  return (
    <SessionContext.Provider value={{ user, period, setPeriod, notify }}>
      <Header user={user} route={route} onLogout={() => {
        setToken(null);
        setUser(null);
      }} />
      <ContextBar period={period} latest={latest} onChange={setPeriod} />
      <main className="page"><Page /></main>
      {toast && <div className={`toast ${toast.tone}`}>{toast.text}</div>}
    </SessionContext.Provider>
  );
}
