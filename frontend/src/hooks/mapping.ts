// Логика сопоставления полей источника с моделью AuditXP
import type { MappingState, MappingSuggestion } from "../services/types";

export const TARGET_FIELDS: Record<string, string> = {
  doc_number: "Номер документа",
  transaction_date: "Дата проводки",
  amount: "Сумма",
  counterparty_info: "Контрагент",
  account_debit: "Счет Дт",
  account_credit: "Счет Кт",
  department: "Подразделение",
};
export const REQUIRED = ["doc_number", "transaction_date", "amount",
  "counterparty_info", "department"];

export type Mapping = Record<string, string | null>;

export function fromSuggestions(items: MappingSuggestion[]): Mapping {
  return Object.fromEntries(items.map((s) => [s.source, s.target]));
}

export function missingRequired(mapping: Mapping): string[] {
  const used = new Set(Object.values(mapping));
  return REQUIRED.filter((field) => !used.has(field));
}

export function duplicatedTargets(mapping: Mapping): string[] {
  const seen = new Map<string, number>();
  Object.values(mapping).forEach((t) => {
    if (t) seen.set(t, (seen.get(t) ?? 0) + 1);
  });
  return [...seen].filter(([, n]) => n > 1).map(([t]) => t);
}

export function fieldState(mapping: Mapping, source: string,
                           base: MappingState): MappingState {
  const target = mapping[source];
  if (!target) return "missing";
  if (duplicatedTargets(mapping).includes(target)) return "warning";
  return base === "missing" ? "ok" : base;
}

export function toPayload(mapping: Mapping): Record<string, string> {
  return Object.fromEntries(Object.entries(mapping)
    .filter((entry): entry is [string, string] => Boolean(entry[1])));
}
