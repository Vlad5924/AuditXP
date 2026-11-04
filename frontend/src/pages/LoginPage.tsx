// Экран входа и восстановления пароля (UC-1)
import { useState } from "react";
import { api, setToken } from "../services/api";
import type { User } from "../services/types";

function Brand() {
  return (
    <section className="login-brand">
      <div className="brand big">
        <img src="/favicon.svg" alt="" width={44} height={44} />
        <span><b>AuditXP</b><small>Риск-менеджмент</small></span>
      </div>
      <h2>Выявление и оценка рисков на основе данных внутреннего аудита</h2>
      <ul>
        <li>Импорт транзакций из ERP с очисткой и карантином</li>
        <li>Скоринг аномалий методом Isolation Forest</li>
        <li>Тепловая карта и отчеты с электронной подписью</li>
      </ul>
      <small>ООО «Голдберг-Софт» · 2026</small>
    </section>
  );
}

export function LoginPage({ onLogin }: { onLogin: (u: User) => void }) {
  const [mode, setMode] = useState<"login" | "recover">("login");
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") {
        const result = await api.login(login.trim(), password);
        setToken(result.access_token, remember);
        onLogin(result.user);
      } else {
        setInfo((await api.recover(email.trim())).detail);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-screen">
      <Brand />
      <section className="login-panel">
        <form className="card login-card" onSubmit={submit}>
          <h1>{mode === "login" ? "Вход в AuditXP" : "Восстановление пароля"}
          </h1>
          {mode === "login" ? (
            <>
              <label className="field">Логин
                <input value={login} autoComplete="username" autoFocus
                       onChange={(e) => setLogin(e.target.value)} required />
              </label>
              <label className="field">Пароль
                <input type="password" value={password}
                       autoComplete="current-password" required
                       onChange={(e) => setPassword(e.target.value)} />
              </label>
              <div className="row between">
                <label className="check">
                  <input type="checkbox" checked={remember}
                         onChange={(e) => setRemember(e.target.checked)} />
                  Запомнить меня
                </label>
                <button type="button" className="link"
                        onClick={() => { setMode("recover"); setError(null); }}>
                  Забыли пароль?</button>
              </div>
            </>
          ) : (
            <>
              <p className="muted">Укажите корпоративную почту, на нее придет
                ссылка для смены пароля.</p>
              <label className="field">Корпоративная почта
                <input type="email" value={email} required
                       onChange={(e) => setEmail(e.target.value)} />
              </label>
              {info && <div className="alert success">{info}</div>}
            </>
          )}
          {error && <div className="alert danger">{error}</div>}
          <button className="btn primary wide" disabled={busy}>
            {mode === "login" ? "Войти" : "Отправить ссылку"}</button>
          {mode === "recover" && (
            <button type="button" className="link center"
                    onClick={() => { setMode("login"); setInfo(null); }}>
              Вернуться ко входу</button>
          )}
        </form>
      </section>
    </div>
  );
}

export function ResetPage({ token }: { token: string | null }) {
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(
    null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== repeat) {
      setResult({ ok: false, text: "Пароли не совпадают" });
      return;
    }
    try {
      const res = await api.reset(token ?? "", password);
      setResult({ ok: true, text: res.detail });
    } catch (err) {
      setResult({ ok: false, text: (err as Error).message });
    }
  }

  return (
    <div className="login-screen">
      <Brand />
      <section className="login-panel">
        <form className="card login-card" onSubmit={submit}>
          <h1>Новый пароль</h1>
          <label className="field">Пароль
            <input type="password" value={password} required
                   onChange={(e) => setPassword(e.target.value)} />
          </label>
          <label className="field">Повторите пароль
            <input type="password" value={repeat} required
                   onChange={(e) => setRepeat(e.target.value)} />
          </label>
          {result && <div className={`alert ${result.ok ? "success" :
            "danger"}`}>{result.text}</div>}
          <button className="btn primary wide">Сохранить</button>
          <a className="link center" href="#/overview">Перейти ко входу</a>
        </form>
      </section>
    </div>
  );
}
