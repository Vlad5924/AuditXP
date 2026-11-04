// Контекстная строка периода и прогресса обработки
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { Period } from "../services/types";
import { formatDateTime, monthPeriod, monthTitle } from "../utils/format";

interface Props {
  period: Period;
  latest: Period;
  onChange: (p: Period) => void;
}

function months(latest: Period): Period[] {
  const [y, m] = latest.date_from.split("-").map(Number);
  return Array.from({ length: 6 }, (_, i) => {
    const date = new Date(Date.UTC(y, m - 1 - i, 1));
    return monthPeriod(date.getUTCFullYear(), date.getUTCMonth() + 1);
  });
}

export function ContextBar({ period, latest, onChange }: Props) {
  const { data } = useAsync(() => api.overview(period), [period]);
  return (
    <div className="context-bar">
      <label>
        Период
        <select value={period.date_from} onChange={(e) => {
          const next = months(latest).find((p) =>
            p.date_from === e.target.value);
          if (next) onChange(next);
        }}>
          {months(latest).map((p) => (
            <option key={p.date_from} value={p.date_from}>
              {monthTitle(p.date_from)}</option>
          ))}
        </select>
      </label>
      <span className="dot">·</span>
      <span>Подразделение все</span>
      <span className="dot">·</span>
      <span className="muted">обновлено {formatDateTime(
        data?.last_import ?? null)}</span>
      <span className="spacer" />
      <span className="progress-label">обработано {data?.processed_pct ?? 0}%
      </span>
      <span className="progress"><span style={{
        width: `${data?.processed_pct ?? 0}%` }} /></span>
    </div>
  );
}
