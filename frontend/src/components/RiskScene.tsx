// Сцена риска с действиями жизненного цикла (FR-3.3)
import { useState } from "react";
import { api } from "../services/api";
import type { Risk, RiskAction } from "../services/types";
import { useSession } from "../session";
import { formatDateTime, formatMoney, formatScore } from "../utils/format";
import { RiskLevelChip, StatusChip } from "./Chips";
import { Modal } from "./Modal";

const NEEDS_FORM = ["dismiss", "assign_mitigation", "complete_mitigation"];

interface Props {
  risk: Risk;
  onChanged: (risk: Risk) => void;
}

export function RiskScene({ risk, onChanged }: Props) {
  const { user, notify } = useSession();
  const [dialog, setDialog] = useState<RiskAction | null>(null);
  const [form, setForm] = useState({ comment: "", mitigation_plan: "",
    mitigation_owner: "", mitigation_due: "", effective: false });
  const canAct = user.role_name !== "Администратор";
  const t = risk.transaction;

  async function run(action: string) {
    try {
      const updated = await api.transition(risk.id, {
        action, comment: form.comment || undefined,
        mitigation_plan: form.mitigation_plan || undefined,
        mitigation_owner: form.mitigation_owner || undefined,
        mitigation_due: form.mitigation_due || undefined,
        effectiveness_confirmed: form.effective,
      });
      setDialog(null);
      notify(`${risk.code} переведен в состояние «${updated.status}»`);
      onChanged(updated);
    } catch (err) {
      notify((err as Error).message, "danger");
    }
  }

  async function escalate() {
    try {
      onChanged(await api.escalate(risk.id));
      notify(`${risk.code} эскалирован руководителю службы`);
    } catch (err) {
      notify((err as Error).message, "danger");
    }
  }

  return (
    <div className="scene">
      <div className="scene-head">
        <div>
          <div className="muted mono">{risk.code} · {risk.method}</div>
          <h2>{risk.risk_type}</h2>
        </div>
        <div className="chips">
          <RiskLevelChip level={risk.level} />
          <StatusChip status={risk.status} />
        </div>
      </div>
      <p className="scene-text">{risk.description}</p>
      <div className="metrics">
        <div><small>Оценка аномальности</small>
          <b>{formatScore(risk.anomaly_score)}</b></div>
        <div><small>Вероятность</small><b>{formatScore(risk.probability)}</b>
        </div>
        <div><small>Ущерб</small><b>{formatMoney(risk.impact, true)}</b></div>
        <div><small>Балл</small><b>{risk.materiality} из 25</b></div>
      </div>
      <table className="kv">
        <tbody>
          <tr><th>Документ</th><td className="mono">{t.doc_number}</td></tr>
          <tr><th>Дата проводки</th>
            <td>{formatDateTime(t.transaction_date, false)}</td></tr>
          <tr><th>Контрагент</th><td>{t.counterparty_info}</td></tr>
          <tr><th>Сумма</th><td>{formatMoney(t.amount)}</td></tr>
          <tr><th>Счета Дт и Кт</th><td className="mono">
            {t.account_debit} / {t.account_credit}</td></tr>
          <tr><th>Подразделение</th><td>{t.department}</td></tr>
          {risk.mitigation_plan && <tr><th>Мероприятие</th>
            <td>{risk.mitigation_plan}, {risk.mitigation_owner}</td></tr>}
          {risk.comment && <tr><th>Комментарий</th>
            <td>{risk.comment}</td></tr>}
        </tbody>
      </table>
      {canAct && (
        <div className="actions">
          {risk.actions.map((a, index) => (
            <button key={a.action} type="button"
                    className={`btn ${index === 0 ? "primary" : "ghost"}` +
                      (a.action === "dismiss" ? " danger-text" : "")}
                    onClick={() => NEEDS_FORM.includes(a.action)
                      ? setDialog(a) : run(a.action)}>{a.title}</button>
          ))}
          {risk.status !== "Закрыт" && (
            <button type="button" className="btn ghost"
                    onClick={escalate}>Эскалировать</button>
          )}
        </div>
      )}
      {dialog && (
        <Modal title={`${dialog.title} ${risk.code}`}
               onClose={() => setDialog(null)} footer={
          <>
            <button type="button" className="btn ghost"
                    onClick={() => setDialog(null)}>Отмена</button>
            <button type="button" className="btn primary"
                    onClick={() => run(dialog.action)}>{dialog.title}</button>
          </>}>
          {dialog.action === "dismiss" && (
            <label className="field">Причина отклонения
              <textarea rows={3} value={form.comment} onChange={(e) =>
                setForm({ ...form, comment: e.target.value })} />
            </label>
          )}
          {dialog.action === "assign_mitigation" && (
            <>
              <label className="field">Корректирующее мероприятие
                <textarea rows={3} value={form.mitigation_plan}
                          onChange={(e) => setForm({ ...form,
                            mitigation_plan: e.target.value })} />
              </label>
              <div className="row">
                <label className="field grow">Ответственный
                  <input value={form.mitigation_owner} onChange={(e) =>
                    setForm({ ...form, mitigation_owner: e.target.value })} />
                </label>
                <label className="field">Срок
                  <input type="date" value={form.mitigation_due}
                         onChange={(e) => setForm({ ...form,
                           mitigation_due: e.target.value })} />
                </label>
              </div>
            </>
          )}
          {dialog.action === "complete_mitigation" && (
            <label className="check">
              <input type="checkbox" checked={form.effective}
                     onChange={(e) => setForm({ ...form,
                       effective: e.target.checked })} />
              Эффективность мероприятия подтверждена
            </label>
          )}
        </Modal>
      )}
    </div>
  );
}
