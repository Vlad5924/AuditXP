// Отчеты по рискам, согласование и экспорт (UC-4, UC-5, UC-6)
import { useState } from "react";
import { StatusChip } from "../components/Chips";
import { HeatmapGrid } from "../components/HeatmapGrid";
import { Modal } from "../components/Modal";
import { BarList, Empty, KpiTile } from "../components/Widgets";
import { useAsync } from "../hooks/useAsync";
import { api, download } from "../services/api";
import { useSession } from "../session";
import { formatDate, formatDateTime, formatMoney, formatNumber }
  from "../utils/format";

export function ReportsPage() {
  const { user, period, notify } = useSession();
  const list = useAsync(() => api.reports(), []);
  const [selected, setSelected] = useState<number | null>(null);
  const id = selected ?? list.data?.[0]?.id ?? null;
  const report = useAsync(() => id ? api.report(id) : Promise.resolve(null),
    [id]);
  const [dialog, setDialog] = useState<"create" | "return" | null>(null);
  const [title, setTitle] = useState("Отчет по рискам");
  const [comment, setComment] = useState("");
  const [valid, setValid] = useState<boolean | null>(null);
  const r = report.data;
  const isChief = user.role_name === "Руководитель";
  const canEdit = user.role_name !== "Администратор";

  async function act(action: () => Promise<unknown>, text: string) {
    try {
      await action();
      notify(text);
      setDialog(null);
      list.reload();
      report.reload();
    } catch (err) {
      notify((err as Error).message, "danger");
    }
  }

  async function exportAs(format: "pdf" | "xlsx") {
    if (!r) return;
    const blob = await api.exportReport(r.id, format);
    download(blob, `AuditXP_отчет_${r.id}.${format}`);
  }

  return (
    <>
      <div className="page-title">
        <h1>Отчеты</h1>
        {canEdit && <button type="button" className="btn primary"
                            onClick={() => setDialog("create")}>
          Сформировать отчет</button>}
      </div>
      <div className="reports-layout">
        <section className="card list">
          {list.data?.map((item) => (
            <button key={item.id} type="button"
                    className={`list-item${item.id === id ? " active" : ""}`}
                    onClick={() => { setSelected(item.id); setValid(null); }}>
              <span><b>{item.title}</b>
                <small>{formatDate(item.period_from)} –
                  {" "}{formatDate(item.period_to)}</small></span>
              <StatusChip status={item.status} />
            </button>
          ))}
          {list.data?.length === 0 && <Empty>Отчетов пока нет</Empty>}
        </section>
        {r && (
          <section className="card report-preview">
            <div className="scene-head">
              <div>
                <div className="muted">Отчет № {r.id} · автор {r.author}</div>
                <h2>{r.title}</h2>
                <div className="muted">Период {formatDate(r.period_from)} –
                  {" "}{formatDate(r.period_to)}</div>
              </div>
              <StatusChip status={r.status} />
            </div>
            <div className="kpi-row four">
              <KpiTile label="Транзакций"
                       value={formatNumber(r.summary.transactions)} />
              <KpiTile label="Аномалий" tone="accent"
                       value={r.summary.risks} />
              <KpiTile label="Критических" tone="danger"
                       value={r.summary.critical} />
              <KpiTile label="Обработано" tone="success"
                       value={r.summary.processed}
                       hint={formatMoney(r.summary.total_impact, true)} />
            </div>
            <div className="report-body">
              {r.summary.heatmap && <HeatmapGrid data={r.summary.heatmap}
                                                 compact />}
              <div>
                <h3>Подразделения</h3>
                <BarList items={r.summary.departments.slice(0, 6).map(
                  ([name, value]) => ({ name, value }))} />
              </div>
            </div>
            {r.review_comment && r.status === "На доработке" && (
              <div className="alert danger">Комментарий руководителя
                {" "}{r.review_comment}</div>)}
            {r.signature && (
              <div className="signature">
                Утвержден {formatDateTime(r.approved_at)}, {r.approver}.
                ЭЦП <span className="mono">{r.signature.slice(0, 24)}…</span>
                <button type="button" className="link" onClick={async () =>
                  setValid((await api.verifyReport(r.id)).valid)}>
                  Проверить подпись</button>
                {valid !== null && <b className={valid ? "ok" : "bad"}>
                  {valid ? "подпись действительна" : "подпись неверна"}</b>}
              </div>
            )}
            <div className="actions">
              <button type="button" className="btn ghost"
                      onClick={() => exportAs("pdf")}>Экспорт PDF</button>
              <button type="button" className="btn ghost"
                      onClick={() => exportAs("xlsx")}>Экспорт XLSX</button>
              {canEdit && ["Черновик", "На доработке"].includes(r.status) && (
                <button type="button" className="btn primary" onClick={() =>
                  act(() => api.submitReport(r.id),
                    "Отчет отправлен на утверждение")}>
                  Отправить на утверждение</button>)}
              {isChief && r.status === "На проверке" && (
                <>
                  <button type="button" className="btn primary" onClick={() =>
                    act(() => api.approveReport(r.id),
                      "Отчет утвержден и подписан ЭЦП")}>Утвердить</button>
                  <button type="button" className="btn ghost danger-text"
                          onClick={() => setDialog("return")}>
                    Вернуть на доработку</button>
                </>
              )}
            </div>
          </section>
        )}
      </div>
      {dialog === "create" && (
        <Modal title="Новый отчет" onClose={() => setDialog(null)} footer={
          <button type="button" className="btn primary" onClick={() =>
            act(() => api.createReport({ ...period, title }),
              "Отчет сформирован")}>Сформировать</button>}>
          <label className="field">Название
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <div className="muted">Период {formatDate(period.date_from)} –
            {" "}{formatDate(period.date_to)} выбирается в строке контекста.
          </div>
        </Modal>
      )}
      {dialog === "return" && r && (
        <Modal title="Вернуть на доработку" onClose={() => setDialog(null)}
               footer={<button type="button" className="btn primary"
                               onClick={() => act(() => api.returnReport(
                                 r.id, comment), "Отчет возвращен автору")}>
                 Вернуть</button>}>
          <label className="field">Комментарий для автора
            <textarea rows={4} value={comment}
                      onChange={(e) => setComment(e.target.value)} />
          </label>
        </Modal>
      )}
    </>
  );
}
