// Индикатор состояния сопоставления поля
import type { MappingState } from "../services/types";

const TEXT: Record<MappingState, string> = {
  ok: "Сопоставлено", warning: "Внимание", missing: "Не сопоставлено",
};

export function MappingStatus({ state }: { state: MappingState }) {
  return <span className={`mapping-status ${state}`}>{TEXT[state]}</span>;
}
