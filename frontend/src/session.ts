// Контекст сеанса пользователя
import { createContext, useContext } from "react";
import type { Period, User } from "./services/types";

export interface SessionValue {
  user: User;
  period: Period;
  setPeriod: (p: Period) => void;
  notify: (text: string, tone?: "success" | "danger") => void;
}

export const SessionContext = createContext<SessionValue | null>(null);

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("SessionContext не инициализирован");
  return value;
}
