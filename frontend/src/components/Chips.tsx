// Цветовые метки уровня риска и статуса (UI-02)
import { LEVEL_ZONE, STATUS_TONE } from "../utils/risk";

export function RiskLevelChip({ level }: { level: string }) {
  const zone = LEVEL_ZONE[level] ?? "green";
  return <span className={`chip zone-${zone}`}>{level}</span>;
}

export function StatusChip({ status }: { status: string }) {
  return (
    <span className={`chip tone-${STATUS_TONE[status] ?? "muted"}`}>
      {status}
    </span>
  );
}
