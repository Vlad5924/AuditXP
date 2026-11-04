// Реестр рисков с фильтрами и карточкой (FR-3.3)
import { useState } from "react";
import { RiskLevelChip, StatusChip } from "../components/Chips";
import { RiskScene } from "../components/RiskScene";
import { Empty } from "../components/Widgets";
import { useAsync } from "../hooks/useAsync";
import { useHashRoute } from "../hooks/useHashRoute";
import { api } from "../services/api";
import type { Risk } from "../services/types";
import { useSession } from "../session";
import { formatDate, formatMoney, formatScore } from "../utils/format";
import { DEPARTMENTS, RISK_LEVELS, RISK_STATUSES } from "../utils/risk";

const PAGE = 15;

export function RisksPage() {
  const { period } = useSession();
  const [, query] = useHashRoute();
  const [filters, setFilters] = useState({ status: "open", level: "",
    department: "", q: query.get("q") ?? "" });
  const [page, setPage] = useState(0);
  // выбранный риск хранится целиком, чтобы карточка не закрывалась,
  // когда после смены состояния риск выходит за пределы фильтра
  const [selected, setSelected] = useState<Risk | null>(null);
  const [allPeriods, setAllPeriods] = useState(Boolean(query.get("q")));
  const params = { ...filters, limit: PAGE, offset: page * PAGE,
    ...(allPeriods ? {} : period) };
  const { data, reload } = useAsync(() => api.risks(params),
    [JSON.stringify(params)]);
  const current = data?.items.find((r) => r.id === selected?.id)
    ?? selected;
  const pages = Math.max(1, Math.ceil((data?.total ?? 0) / PAGE));
  const set = (key: string, value: string) => {
    setFilters({ ...filters, [key]: value });
    setPage(0);
  };

  return (
    <>
      <div className="page-title">
        <h1>Реестр рисков</h1>
        <span className="muted">найдено {data?.total ?? 0}</span>
      </div>
      <div className="card filters">
        <select value={filters.status} onChange={(e) =>
          set("status", e.target.value)}>
          <option value="open">Открытые</option>
          <option value="">Все состояния</option>
          {RISK_STATUSES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select value={filters.level} onChange={(e) =>
          set("level", e.target.value)}>
          <option value="">Все уровни</option>
          {RISK_LEVELS.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select value={filters.department} onChange={(e) =>
          set("department", e.target.value)}>
          <option value="">Все подразделения</option>
          {DEPARTMENTS.map((s) => <option key={s}>{s}</option>)}
        </select>
        <input className="grow" placeholder="Тип, контрагент или документ"
               value={filters.q} onChange={(e) => set("q", e.target.value)} />
        <label className="check">
          <input type="checkbox" checked={allPeriods}
                 onChange={(e) => setAllPeriods(e.target.checked)} />
          За все периоды
        </label>
      </div>
      <div className={`registry${current ? " with-drawer" : ""}`}>
        <section className="card table-card">
          <table className="table">
            <thead>
              <tr><th>Код</th><th>Тип риска</th>
                <th className="opt">Подразделение</th>
                <th>Контрагент</th><th className="opt">Дата</th>
                <th className="num">Сумма</th>
                <th className="num opt">Оценка</th><th className="num">Балл</th>
                <th>Уровень</th><th>Состояние</th></tr>
            </thead>
            <tbody>
              {data?.items.map((risk) => (
                <tr key={risk.id} onClick={() => setSelected(risk)}
                    className={risk.id === selected?.id ? "selected" : ""}>
                  <td className="mono">{risk.code}</td>
                  <td>{risk.risk_type}</td>
                  <td className="opt">{risk.transaction.department}</td>
                  <td>{risk.transaction.counterparty_info}</td>
                  <td className="opt">
                    {formatDate(risk.transaction.transaction_date)}</td>
                  <td className="num">{formatMoney(risk.impact, true)}</td>
                  <td className="num opt">
                    {formatScore(risk.anomaly_score)}</td>
                  <td className="num">{risk.materiality}</td>
                  <td><RiskLevelChip level={risk.level} /></td>
                  <td><StatusChip status={risk.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          {data?.items.length === 0 && <Empty>Риски не найдены</Empty>}
          <div className="pager">
            <button type="button" className="btn ghost" disabled={page === 0}
                    onClick={() => setPage(page - 1)}>Назад</button>
            <span>Страница {page + 1} из {pages}</span>
            <button type="button" className="btn ghost"
                    disabled={page + 1 >= pages}
                    onClick={() => setPage(page + 1)}>Вперед</button>
          </div>
        </section>
        {current && (
          <aside className="card drawer">
            <button type="button" className="icon-btn close"
                    onClick={() => setSelected(null)}
                    aria-label="Закрыть">×</button>
            <RiskScene risk={current} onChanged={(updated) => {
              setSelected(updated);
              reload();
            }} />
          </aside>
        )}
      </div>
    </>
  );
}
