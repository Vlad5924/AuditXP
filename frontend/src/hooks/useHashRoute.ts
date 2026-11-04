// Маршрутизация по фрагменту адреса (#/risks?id=1)
import { useSyncExternalStore } from "react";

function subscribe(callback: () => void) {
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
}

export function useHashRoute(): [string, URLSearchParams] {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash);
  const [path, query = ""] = hash.replace(/^#\/?/, "").split("?");
  return [path || "overview", new URLSearchParams(query)];
}

export function navigate(path: string): void {
  window.location.hash = `#/${path}`;
}
