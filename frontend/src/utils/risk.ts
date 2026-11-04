// Справочники уровней, зон и состояний риска
import type { Zone } from "../services/types";

export const LEVEL_ZONE: Record<string, Zone> = {
  "Низкий": "green", "Средний": "yellow", "Высокий": "orange",
  "Критический": "red",
};

export function zoneForScore(score: number): Zone {
  if (score >= 15) return "red";
  if (score >= 10) return "orange";
  if (score >= 5) return "yellow";
  return "green";
}

export const STATUS_TONE: Record<string, string> = {
  "Выявлен": "danger", "Оценен": "warning", "Подтвержден": "accent",
  "В проработке": "primary", "Снят": "muted", "Закрыт": "success",
  "Черновик": "muted", "На проверке": "warning", "На доработке": "danger",
  "Утвержден": "success", "Успешно": "success",
  "С предупреждениями": "warning", "Ошибка": "danger",
  "Выполняется": "primary",
};

export const RISK_STATUSES = ["Выявлен", "Оценен", "Подтвержден",
  "В проработке", "Снят", "Закрыт"];
export const RISK_LEVELS = ["Критический", "Высокий", "Средний", "Низкий"];
export const DEPARTMENTS = ["Реализация", "Закупки", "Логистика",
  "Производство", "Розница", "Финансы"];
