// Карточка риска в приоритетной ленте
import type { Risk } from "../services/types";
import { formatMoney, formatScore } from "../utils/format";
import { RiskLevelChip } from "./Chips";

interface Props {
  risk: Risk;
  active?: boolean;
  onSelect?: (risk: Risk) => void;
}

export function RiskCard({ risk, active, onSelect }: Props) {
  return (
    <button type="button" className={`risk-card zone-edge-${risk.zone}` +
      (active ? " active" : "")} onClick={() => onSelect?.(risk)}>
      <div className="risk-card-top">
        <span className="mono">{risk.code}</span>
        <RiskLevelChip level={risk.level} />
      </div>
      <div className="risk-card-title">{risk.risk_type}</div>
      <div className="risk-card-meta">
        <span>{risk.transaction.department}</span>
        <span>оценка {formatScore(risk.anomaly_score)}</span>
        <span>{formatMoney(risk.impact, true)}</span>
      </div>
    </button>
  );
}
