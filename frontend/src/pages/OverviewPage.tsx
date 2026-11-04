// Рабочий стол «Обзор» (сегментный рабочий стол, ЛР6)
import { useState } from "react";
import { Gauge } from "../components/Gauge";
import { RiskCard } from "../components/RiskCard";
import { RiskScene } from "../components/RiskScene";
import { BarList, ColumnChart, Empty, KpiTile } from "../components/Widgets";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { Risk } from "../services/types";
import { useSession } from "../session";
import { formatNumber, monthTitle } from "../utils/format";

export function OverviewPage() {
  const { period } = useSession();
  const { data, error, reload } = useAsync(() => api.overview(period),
    [period]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  if (error) return <div className="alert danger">{error}</div>;
  if (!data) return <div className="loading">Загрузка…</div>;
  const scene = data.priority.find((r) => r.id === selectedId) ??
    data.priority[0];
  const onChanged = (r: Risk) => { setSelectedId(r.id); reload(); };

  return (
    <>
      <div className="page-title">
        <h1>Обзор рисков</h1>
        <span className="muted">{monthTitle(data.period_from)}</span>
      </div>
      <div className="kpi-row">
        <KpiTile label="Транзакций за период"
                 value={formatNumber(data.transactions)} hint="загружено из ERP" />
        <KpiTile label="Выявлено аномалий" value={data.risks}
                 hint="оценка не ниже 0,85" tone="accent" />
        <KpiTile label="Критических" value={data.critical}
                 hint="балл 15 и выше" tone="danger" />
        <KpiTile label="Обработано" value={data.processed}
                 hint={`${data.processed_pct}% от выявленных`}
                 tone="success" />
      </div>
      <div className="overview-grid">
        <section className="card">
          <h2>Приоритетная лента</h2>
          {data.priority.length === 0 && <Empty>Открытых рисков нет</Empty>}
          <div className="feed">
            {data.priority.map((risk) => (
              <RiskCard key={risk.id} risk={risk} active={risk === scene}
                        onSelect={(r) => setSelectedId(r.id)} />
            ))}
          </div>
        </section>
        <section className="card">
          {scene ? <RiskScene risk={scene} onChanged={onChanged} />
            : <Empty>Выберите риск</Empty>}
        </section>
        <aside className="side">
          <section className="card center">
            <h2>Нагрузка смены</h2>
            <Gauge value={data.processed_pct} label="обработано" />
            <div className="legend-row">
              {Object.entries(data.levels).map(([level, count]) => (
                <span key={level}>{level} <b>{count}</b></span>
              ))}
            </div>
          </section>
          <section className="card">
            <h2>Топ подразделений</h2>
            <BarList items={data.departments.map((d) => ({
              name: d.name, value: d.count, caption: `${d.share}%` }))} />
          </section>
          <section className="card">
            <h2>Активность по неделям</h2>
            <ColumnChart items={data.weekly} />
            <div className="muted small">Всего за период {data.risks}</div>
          </section>
        </aside>
      </div>
    </>
  );
}
