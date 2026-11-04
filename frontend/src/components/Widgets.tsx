// Плитки показателей и простые диаграммы
import type { ReactNode } from "react";

export function KpiTile({ label, value, hint, tone = "primary" }:
  { label: string; value: ReactNode; hint?: string; tone?: string }) {
  return (
    <div className={`card kpi tone-line-${tone}`}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {hint && <div className="kpi-hint">{hint}</div>}
    </div>
  );
}

export function BarList({ items }:
  { items: { name: string; value: number; caption?: string }[] }) {
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <ul className="bar-list">
      {items.map((item) => (
        <li key={item.name}>
          <span className="bar-name">{item.name}</span>
          <span className="bar-track">
            <span className="bar-fill"
                  style={{ width: `${(100 * item.value) / max}%` }} />
          </span>
          <span className="bar-value">{item.caption ?? item.value}</span>
        </li>
      ))}
    </ul>
  );
}

export function ColumnChart({ items }:
  { items: { label: string; count: number }[] }) {
  const max = Math.max(1, ...items.map((i) => i.count));
  return (
    <div className="columns">
      {items.map((item) => (
        <div key={item.label} className="column">
          <span className="column-value">{item.count}</span>
          <span className="column-bar"
                style={{ height: `${(80 * item.count) / max + 4}px` }} />
          <span className="column-label">{item.label}</span>
        </div>
      ))}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty-state">{children}</div>;
}
