// Мастер импорта транзакций из ERP или файла (UC-2, ЛР6)
import { useState } from "react";
import { REQUIRED, TARGET_FIELDS } from "../hooks/mapping";
import { useImportMapping } from "../hooks/useImportMapping";
import { api } from "../services/api";
import type { DetectionResult, ImportResult, Preview } from "../services/types";
import { useSession } from "../session";
import { formatDateTime, formatMoney, formatNumber } from "../utils/format";
import { MappingStatus } from "./MappingStatus";
import { KpiTile } from "./Widgets";

function previewCell(key: string, value: unknown): string {
  if (value === null || value === undefined) return "";
  if (key === "transaction_date") {
    return formatDateTime(String(value), false);
  }
  if (key === "amount") return formatMoney(Number(value));
  return String(value);
}

const STEPS = ["Подключение источника", "Маппинг полей",
  "Предпросмотр данных", "Скоринг и загрузка"];
const EMPTY: Preview["suggestions"] = [];

export function ImportWizard({ onDone }: { onDone: () => void }) {
  const { period, notify } = useSession();
  const [step, setStep] = useState(0);
  const [source, setSource] = useState<"erp" | "file">("erp");
  const [range, setRange] = useState(period);
  const [file, setFile] = useState<File | null>(null);
  const [checked, setChecked] = useState<string | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [score, setScore] = useState(true);
  const [strategy, setStrategy] = useState("ml");
  const [result, setResult] = useState<{ imp: ImportResult;
    det: DetectionResult | null } | null>(null);
  const mapping = useImportMapping(preview?.suggestions ?? EMPTY);

  async function guard(action: () => Promise<void>) {
    setBusy(true);
    try { await action(); } catch (err) {
      notify((err as Error).message, "danger");
    } finally { setBusy(false); }
  }

  const check = () => guard(async () => {
    const res = await api.erpCheck();
    setChecked(`Подключено к ${res.base_url} (режим ${res.source})`);
  });

  const loadPreview = () => guard(async () => {
    const data = source === "erp" ? await api.erpPreview(range)
      : await api.filePreview(file as File);
    setPreview(data);
    setStep(1);
  });

  const runImport = () => guard(async () => {
    const imp = source === "erp" ? await api.runImport(range)
      : await api.importFile(file as File, mapping.payload());
    // для файла скоринг выполняется за период, найденный в данных
    const scope = imp.period_from && imp.period_to
      ? { date_from: imp.period_from, date_to: imp.period_to } : range;
    const det = score ? await api.detect(scope, strategy) : null;
    setResult({ imp, det });
    notify(`Импорт завершен. ${imp.message}`);
    onDone();
  });

  return (
    <section className="card wizard">
      <ol className="steps">
        {STEPS.map((title, i) => (
          <li key={title} className={i === step ? "active" :
            i < step ? "done" : ""}><span>{i + 1}</span>{title}</li>
        ))}
      </ol>
      {step === 0 && (
        <div className="wizard-body">
          <div className="source-choice">
            <label className={`choice${source === "erp" ? " active" : ""}`}>
              <input type="radio" checked={source === "erp"}
                     onChange={() => setSource("erp")} />
              <b>ERP (REST API)</b>
              <small>Выгрузка проводок за период, только чтение</small>
            </label>
            <label className={`choice${source === "file" ? " active" : ""}`}>
              <input type="radio" checked={source === "file"}
                     onChange={() => setSource("file")} />
              <b>Файл CSV или XLSX</b>
              <small>Ручная загрузка выгрузки</small>
            </label>
          </div>
          {source === "erp" ? (
            <div className="row">
              <label className="field">Начало периода
                <input type="date" value={range.date_from} onChange={(e) =>
                  setRange({ ...range, date_from: e.target.value })} />
              </label>
              <label className="field">Окончание периода
                <input type="date" value={range.date_to} onChange={(e) =>
                  setRange({ ...range, date_to: e.target.value })} />
              </label>
              <button type="button" className="btn ghost align-end"
                      disabled={busy} onClick={check}>
                Проверить подключение</button>
            </div>
          ) : (
            <label className="field">Файл выгрузки
              <input type="file" accept=".csv,.xlsx" onChange={(e) =>
                setFile(e.target.files?.[0] ?? null)} />
            </label>
          )}
          {checked && source === "erp" && (
            <div className="alert success">{checked}</div>)}
          <div className="wizard-nav">
            <span />
            <button type="button" className="btn primary"
                    disabled={busy || (source === "file" && !file)}
                    onClick={loadPreview}>Далее</button>
          </div>
        </div>
      )}
      {step === 1 && preview && (
        <div className="wizard-body">
          <table className="table compact">
            <thead><tr><th>Поле источника</th><th>Поле AuditXP</th>
              <th>Состояние</th></tr></thead>
            <tbody>
              {preview.suggestions.map((s) => (
                <tr key={s.source}>
                  <td>{s.source}</td>
                  <td>
                    <select value={mapping.mapping[s.source] ?? ""}
                            disabled={source === "erp"}
                            onChange={(e) => mapping.setTarget(s.source,
                              e.target.value || null)}>
                      <option value="">Не загружать</option>
                      {Object.entries(TARGET_FIELDS).map(([key, title]) => (
                        <option key={key} value={key}>{key} · {title}
                          {REQUIRED.includes(key) ? " *" : ""}</option>
                      ))}
                    </select>
                  </td>
                  <td><MappingStatus state={mapping.stateOf(s)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          {mapping.missing.length > 0 && (
            <div className="alert danger">Не сопоставлены обязательные поля
              {" "}{mapping.missing.join(", ")}</div>)}
          {source === "erp" && <div className="muted small">Для ERP
            применяется утвержденная схема сопоставления.</div>}
          <div className="wizard-nav">
            <button type="button" className="btn ghost"
                    onClick={() => setStep(0)}>Назад</button>
            <button type="button" className="btn primary"
                    disabled={!mapping.isValid}
                    onClick={() => setStep(2)}>Далее</button>
          </div>
        </div>
      )}
      {step === 2 && preview && (
        <div className="wizard-body">
          <div className="kpi-row four">
            <KpiTile label="Строк в выгрузке"
                     value={formatNumber(preview.stats.total)} />
            <KpiTile label="Корректных" tone="success"
                     value={formatNumber(preview.stats.clean)} />
            <KpiTile label="В карантин" tone="danger"
                     value={formatNumber(preview.stats.quarantined)} />
            <KpiTile label="Дубликатов" tone="accent"
                     value={formatNumber(preview.stats.duplicates)} />
          </div>
          <div className="table-scroll">
            <table className="table compact">
              <thead><tr>{Object.keys(preview.rows[0] ?? {}).map((k) =>
                <th key={k} className={k === "amount" ? "num" : ""}>
                  {TARGET_FIELDS[k] ?? k}</th>)}</tr></thead>
              <tbody>
                {preview.rows.map((row, i) => (
                  <tr key={i}>{Object.entries(row).map(([k, v]) => (
                    <td key={k} className={k === "amount" ? "num" : ""}>
                      {previewCell(k, v)}</td>
                  ))}</tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="wizard-nav">
            <button type="button" className="btn ghost"
                    onClick={() => setStep(1)}>Назад</button>
            <button type="button" className="btn primary"
                    onClick={() => setStep(3)}>Далее</button>
          </div>
        </div>
      )}
      {step === 3 && (
        <div className="wizard-body">
          <label className="check">
            <input type="checkbox" checked={score}
                   onChange={(e) => setScore(e.target.checked)} />
            Выполнить скоринг после загрузки
          </label>
          <label className="field narrow">Метод скоринга
            <select value={strategy} disabled={!score}
                    onChange={(e) => setStrategy(e.target.value)}>
              <option value="ml">Isolation Forest</option>
              <option value="stat">Z-оценка (3 сигма)</option>
            </select>
          </label>
          {result && (
            <div className="alert success">
              {result.imp.message}. Время {result.imp.duration_s
                .toFixed(1).replace(".", ",")} с.
              {result.det && ` Скоринг ${result.det.method}, новых рисков
                ${result.det.risks_created}, критических
                ${result.det.critical}.`}
            </div>
          )}
          <div className="wizard-nav">
            <button type="button" className="btn ghost"
                    onClick={() => { setStep(0); setResult(null); }}>
              В начало</button>
            <button type="button" className="btn primary" disabled={busy}
                    onClick={runImport}>
              {busy ? "Загрузка…" : "Загрузить данные"}</button>
          </div>
        </div>
      )}
    </section>
  );
}
