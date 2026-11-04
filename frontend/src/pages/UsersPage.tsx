// Администрирование учетных записей (UC-7)
import { useState } from "react";
import { Modal } from "../components/Modal";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { useSession } from "../session";
import { formatDateTime } from "../utils/format";

const ROLES = ["Аудитор", "Руководитель", "Администратор"];
const EMPTY = { login: "", full_name: "", email: "", password: "",
  role: "Аудитор" };

export function UsersPage() {
  const { user: me, notify } = useSession();
  const users = useAsync(() => api.users(), []);
  const [form, setForm] = useState<typeof EMPTY | null>(null);

  async function act(action: () => Promise<unknown>, text: string) {
    try {
      await action();
      notify(text);
      setForm(null);
      users.reload();
    } catch (err) {
      notify((err as Error).message, "danger");
    }
  }

  return (
    <>
      <div className="page-title">
        <h1>Пользователи</h1>
        <button type="button" className="btn primary"
                onClick={() => setForm(EMPTY)}>Добавить пользователя</button>
      </div>
      <section className="card table-card">
        <table className="table">
          <thead><tr><th>ФИО</th><th>Логин</th><th>Почта</th><th>Роль</th>
            <th>Состояние</th><th>Последний вход</th><th /></tr></thead>
          <tbody>
            {users.data?.map((u) => (
              <tr key={u.id} className={u.is_active ? "" : "inactive"}>
                <td>{u.full_name}</td>
                <td className="mono">{u.login}</td>
                <td>{u.email}</td>
                <td>
                  <select value={u.role_name} disabled={!u.is_active ||
                    u.id === me.id} onChange={(e) => act(() =>
                    api.updateUser(u.id, { role: e.target.value }),
                    `Роль ${u.login} изменена`)}>
                    {ROLES.map((r) => <option key={r}>{r}</option>)}
                  </select>
                </td>
                <td>{!u.is_active ? <span className="chip tone-muted">
                  Удален</span> : u.is_locked
                  ? <span className="chip tone-danger">Заблокирован</span>
                  : <span className="chip tone-success">Активен</span>}</td>
                <td>{formatDateTime(u.last_login_at)}</td>
                <td className="row-actions">
                  {u.is_active && u.id !== me.id && (
                    <>
                      <button type="button" className="btn ghost small"
                              onClick={() => act(() => api.blockUser(u.id,
                                !u.is_locked), u.is_locked
                                ? "Учетная запись разблокирована"
                                : "Учетная запись заблокирована")}>
                        {u.is_locked ? "Разблокировать" : "Заблокировать"}
                      </button>
                      <button type="button" className="btn ghost small
                        danger-text" onClick={() => window.confirm(
                          `Удалить учетную запись ${u.login}?`) && act(() =>
                          api.deleteUser(u.id), "Учетная запись удалена")}>
                        Удалить</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      {form && (
        <Modal title="Новый пользователь" onClose={() => setForm(null)}
               footer={<button type="button" className="btn primary"
                               onClick={() => act(() => api.createUser(form),
                                 "Учетная запись создана")}>Создать</button>}>
          {([["full_name", "ФИО"], ["login", "Логин"],
            ["email", "Корпоративная почта"], ["password", "Пароль"]] as const)
            .map(([key, label]) => (
              <label key={key} className="field">{label}
                <input type={key === "password" ? "password" : "text"}
                       value={form[key]} onChange={(e) =>
                  setForm({ ...form, [key]: e.target.value })} />
              </label>
            ))}
          <label className="field">Роль
            <select value={form.role} onChange={(e) =>
              setForm({ ...form, role: e.target.value })}>
              {ROLES.map((r) => <option key={r}>{r}</option>)}
            </select>
          </label>
        </Modal>
      )}
    </>
  );
}
