// Импорт данных и журнал импорта (UC-2)
import { useState } from "react";
import { StatusChip } from "../components/Chips";
import { ImportWizard } from "../components/ImportWizard";
import { Modal } from "../components/Modal";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { ImportBatch } from "../services/types";
import { formatDate, formatDateTime, formatNumber } from "../utils/format";

export function ImportPage() {
  const journal = useAsync(() => api.journal(), []);
  const [batch, setBatch] = useState<ImportBatch | null>(null);
  const quarantine = useAsync(() => batch
    ? api.quarantine(batch.id) : Promise.resolve([]), [batch?.id]);

  return (
    <>
      <div className="page-title"><h1>Импорт данных</h1>
        <span className="muted">ETL-интеграция с корпоративной ERP</span>
      </div>
      <ImportWizard onDone={journal.reload} />
      <section className="card table-card">
        <h2>Журнал импорта</h2>
        <table className="table">
          <thead><tr><th>Запуск</th><th>Источник</th><th>Период</th>
            <th>Состояние</th><th className="num">Строк</th>
            <th className="num">Загружено</th><th className="num">Карантин</th>
            <th className="num">Дубликаты</th><th className="num">Пропущено</th>
            <th>Пользователь</th></tr></thead>
          <tbody>
            {journal.data?.map((b) => (
              <tr key={b.id} onClick={() => b.rows_quarantined && setBatch(b)}>
                <td>{formatDateTime(b.started_at)}</td>
                <td>{b.source === "erp" ? "ERP" : "Файл"}</td>
                <td>{b.period_from ? `${formatDate(b.period_from)} – ` +
                  `${formatDate(b.period_to)}` : "–"}</td>
                <td><StatusChip status={b.status} /></td>
                <td className="num">{formatNumber(b.rows_total)}</td>
                <td className="num">{formatNumber(b.rows_loaded)}</td>
                <td className="num link-cell">{b.rows_quarantined}</td>
                <td className="num">{b.duplicates}</td>
                <td className="num">{formatNumber(b.skipped_existing)}</td>
                <td>{b.user}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      {batch && (
        <Modal title={`Карантин запуска № ${batch.id}`}
               onClose={() => setBatch(null)}>
          <table className="table compact">
            <thead><tr><th>Документ</th><th>Причина</th></tr></thead>
            <tbody>
              {(quarantine.data ?? []).slice(0, 50).map((q) => (
                <tr key={q.id}><td className="mono">{q.doc_number ?? "–"}</td>
                  <td>{q.reason}</td></tr>
              ))}
            </tbody>
          </table>
        </Modal>
      )}
    </>
  );
}

