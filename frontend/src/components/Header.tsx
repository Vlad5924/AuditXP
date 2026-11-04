// Шапка с сегментными вкладками, поиском и профилем (ЛР6)
import { useState } from "react";
import { navigate } from "../hooks/useHashRoute";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { Role, User } from "../services/types";
import { formatDateTime, initials } from "../utils/format";

const TABS: { id: string; title: string; roles: Role[] }[] = [
  { id: "overview", title: "Обзор", roles: ["Аудитор", "Руководитель",
    "Администратор"] },
  { id: "risks", title: "Риски", roles: ["Аудитор", "Руководитель",
    "Администратор"] },
  { id: "heatmap", title: "Карта", roles: ["Аудитор", "Руководитель",
    "Администратор"] },
  { id: "import", title: "Импорт", roles: ["Аудитор", "Руководитель"] },
  { id: "reports", title: "Отчеты", roles: ["Аудитор", "Руководитель",
    "Администратор"] },
  { id: "users", title: "Пользователи", roles: ["Администратор"] },
  { id: "audit", title: "Журнал", roles: ["Руководитель", "Администратор"] },
];

export const tabsFor = (role: Role) => TABS.filter((t) =>
  t.roles.includes(role));

interface Props {
  user: User;
  route: string;
  onLogout: () => void;
}

export function Header({ user, route, onLogout }: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<"menu" | "bell" | null>(null);
  const notes = useAsync(() => api.notifications(), [route]);
  const unread = notes.data?.filter((n) => !n.is_read).length ?? 0;

  return (
    <header className="app-header">
      <a className="brand" href="#/overview">
        <img src="/favicon.svg" alt="" width={30} height={30} />
        <span><b>AuditXP</b><small>Риск-менеджмент</small></span>
      </a>
      <nav className="segments">
        {tabsFor(user.role_name).map((tab) => (
          <a key={tab.id} href={`#/${tab.id}`}
             className={route === tab.id ? "active" : ""}>{tab.title}</a>
        ))}
      </nav>
      <form className="search" onSubmit={(e) => {
        e.preventDefault();
        navigate(`risks?q=${encodeURIComponent(query)}`);
      }}>
        <input value={query} onChange={(e) => setQuery(e.target.value)}
               placeholder="Поиск риска, контрагента, документа" />
      </form>
      <div className="header-actions">
        <button type="button" className="icon-btn bell"
                aria-label="Уведомления"
                onClick={() => setOpen(open === "bell" ? null : "bell")}>
          <svg viewBox="0 0 24 24" width="20" height="20"><path
            d="M12 22a2.5 2.5 0 0 0 2.4-2h-4.8a2.5 2.5 0 0 0 2.4 2zm7-6V11a7
            7 0 0 0-5.5-6.8V3a1.5 1.5 0 0 0-3 0v1.2A7 7 0 0 0 5 11v5l-2
            2v1h18v-1z" fill="currentColor" /></svg>
          {unread > 0 && <span className="badge">{unread}</span>}
        </button>
        <button type="button" className="avatar"
                onClick={() => setOpen(open === "menu" ? null : "menu")}>
          {initials(user.full_name)}
        </button>
        {open === "bell" && (
          <div className="dropdown notes">
            <div className="dropdown-head">
              <b>Уведомления</b>
              <button type="button" className="link" onClick={async () => {
                await api.readAll();
                notes.reload();
              }}>Прочитать все</button>
            </div>
            {(notes.data ?? []).slice(0, 8).map((n) => (
              <div key={n.id} className={`note${n.is_read ? "" : " unread"}`}>
                <div>{n.message}</div>
                <small>{formatDateTime(n.created_at)}</small>
              </div>
            ))}
            {notes.data?.length === 0 && <div className="note">Нет
              уведомлений</div>}
          </div>
        )}
        {open === "menu" && (
          <div className="dropdown menu">
            <b>{user.full_name}</b>
            <small>{user.role_name} · {user.login}</small>
            <button type="button" className="btn ghost wide"
                    onClick={onLogout}>Выйти</button>
          </div>
        )}
      </div>
    </header>
  );
}
