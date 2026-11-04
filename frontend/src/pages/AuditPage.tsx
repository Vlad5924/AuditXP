// Журнал аудита, доступный только для чтения (AUD-01, AUD-02)
import { useState } from "react";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { formatDateTime } from "../utils/format";

const TABLES = [["", "Все объекты"], ["users", "Пользователи"],
  ["erp_transactions", "Транзакции"], ["risks", "Риски"],
  ["audit_reports", "Отчеты"]];

export function AuditPage() {
  const [table, setTable] = useState("");
  const { data } = useAsync(() => api.auditLog(table || undefined), [table]);
  return (
    <>
      <div className="page-title">
        <h1>Журнал аудита</h1>
        <select value={table} onChange={(e) => setTable(e.target.value)}>
          {TABLES.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
        </select>
      </div>
      <section className="card table-card">
        <table className="table">
          <thead><tr><th>Время</th><th>Пользователь</th><th>Объект</th>
            <th>Действие</th><th className="num">Запись</th><th>Подробности</th>
          </tr></thead>
          <tbody>
            {data?.map((e) => (
              <tr key={e.id}>
                <td>{formatDateTime(e.created_at)}</td><td>{e.user}</td>
                <td className="mono">{e.table_name}</td>
                <td><span className="chip tone-muted">{e.action}</span></td>
                <td className="num">{e.record_id ?? ""}</td>
                <td>{e.details}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="muted small">Записи журнала не могут быть изменены
          или удалены.</div>
      </section>
    </>
  );
}
