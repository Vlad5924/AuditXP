// Тепловая карта 5x5 «вероятность x ущерб» (FR-4.1)
import type { Heatmap } from "../services/types";
import { formatMoney } from "../utils/format";

export function HeatmapGrid({ data, compact = false }:
  { data: Heatmap; compact?: boolean }) {
  const rows = [4, 3, 2, 1, 0];
  return (
    <div className={`heatmap${compact ? " compact" : ""}`}>
      <div className="heatmap-axis-y">Вероятность</div>
      <div className="heatmap-grid">
        {rows.map((p) => (
          <div className="heatmap-row" key={p}>
            <div className="heatmap-label">{data.probability_labels[p]}</div>
            {data.cells[p].map((cell, d) => (
              <div key={d} className={`heatmap-cell zone-bg-${cell.zone}` +
                (cell.count ? "" : " empty")}
                   title={`${data.probability_labels[p]} / ` +
                     `${data.damage_labels[d]}. Балл ${cell.score}. ` +
                     `Рисков ${cell.count}, ${formatMoney(cell.impact)}`}>
                <strong>{cell.count || ""}</strong>
                {!compact && cell.count > 0 && (
                  <small>{formatMoney(cell.impact, true)}</small>
                )}
              </div>
            ))}
          </div>
        ))}
        <div className="heatmap-row heatmap-footer">
          <div className="heatmap-label" />
          {data.damage_labels.map((label) => (
            <div key={label} className="heatmap-label center">{label}</div>
          ))}
        </div>
        <div className="heatmap-axis-x">Ущерб</div>
      </div>
    </div>
  );
}
