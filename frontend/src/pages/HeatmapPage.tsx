// Тепловая карта рисков периода (UC-4)
import { RiskLevelChip } from "../components/Chips";
import { HeatmapGrid } from "../components/HeatmapGrid";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { useSession } from "../session";
import { formatMoney, monthTitle } from "../utils/format";

const ZONES = [
  ["red", "Критическая зона", "балл 15–25, эскалация руководителю"],
  ["orange", "Высокая", "балл 10–14"],
  ["yellow", "Средняя", "балл 5–9"],
  ["green", "Низкая", "балл 1–4"],
];

export function HeatmapPage() {
  const { period } = useSession();
  const { data } = useAsync(() => api.heatmap(period), [period]);
  if (!data) return <div className="loading">Загрузка…</div>;
  const byZone = (zone: string) => data.cells.flat()
    .filter((c) => c.zone === zone).reduce((s, c) => s + c.count, 0);

  return (
    <>
      <div className="page-title">
        <h1>Тепловая карта рисков</h1>
        <span className="muted">{monthTitle(period.date_from)} · рисков
          {" "}{data.total}</span>
      </div>
      <div className="heat-layout">
        <section className="card">
          <HeatmapGrid data={data} />
        </section>
        <aside className="side">
          <section className="card">
            <h2>Зоны карты</h2>
            <ul className="zones">
              {ZONES.map(([zone, title, hint]) => (
                <li key={zone}>
                  <span className={`swatch zone-bg-${zone}`} />
                  <span><b>{title}</b><small>{hint}</small></span>
                  <b>{byZone(zone)}</b>
                </li>
              ))}
            </ul>
          </section>
          <section className="card">
            <h2>Топ-5 рисков</h2>
            <ol className="top-list">
              {data.top.map((r) => (
                <li key={r.id}>
                  <span className="mono">{r.code}</span>
                  <span className="grow">{r.risk_type}
                    <small>{formatMoney(r.impact, true)} · балл
                      {" "}{r.materiality}</small></span>
                  <RiskLevelChip level={r.level} />
                </li>
              ))}
            </ol>
          </section>
        </aside>
      </div>
    </>
  );
}
