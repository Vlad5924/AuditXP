// Хук мастера импорта, хранящий состояние маппинга полей (ЛР6)
import { useMemo, useState } from "react";
import type { MappingSuggestion } from "../services/types";
import {
  duplicatedTargets, fieldState, fromSuggestions, type Mapping,
  missingRequired, toPayload,
} from "./mapping";

export function useImportMapping(suggestions: MappingSuggestion[]) {
  const [mapping, setMapping] = useState<Mapping>(() =>
    fromSuggestions(suggestions));
  const [base, setBase] = useState(suggestions);

  if (base !== suggestions) {
    setBase(suggestions);
    setMapping(fromSuggestions(suggestions));
  }

  const missing = useMemo(() => missingRequired(mapping), [mapping]);
  const duplicates = useMemo(() => duplicatedTargets(mapping), [mapping]);

  return {
    mapping,
    missing,
    duplicates,
    isValid: missing.length === 0 && duplicates.length === 0,
    stateOf: (s: MappingSuggestion) => fieldState(mapping, s.source,
      s.status),
    setTarget: (source: string, target: string | null) =>
      setMapping((m) => ({ ...m, [source]: target })),
    payload: () => toPayload(mapping),
  };
}
