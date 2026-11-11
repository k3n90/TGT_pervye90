import { useEffect, useState } from "react";
import { api } from "../api";
import type { Account, SessionUser } from "../types";

const ORDER = ["hr", "manager", "mentor", "director"];

export function LoginPage({ onLogin }: { onLogin: (user: SessionUser, token: string) => void }) {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [error, setError] = useState("");
  const [pending, setPending] = useState("");

  useEffect(() => {
    api<Account[]>("/api/auth/accounts")
      .then(setAccounts)
      .catch(() => setError("Сервис ещё поднимается. Обновите страницу через несколько секунд."));
  }, []);

  async function enter(username: string) {
    setPending(username);
    setError("");
    try {
      const result = await api<{ token: string; user: SessionUser }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password: "demo" }),
      });
      onLogin(result.user, result.token);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось войти");
      setPending("");
    }
  }

  const groups = ORDER.map((role) => accounts.filter((account) => account.role === role)).filter((group) => group.length);

  return (
    <div className="login">
      <div className="login-copy">
        <p className="eyebrow">Демо-кабинет ЗАО «ТГТ»</p>
        <h1>Первые 90</h1>
        <p>
          Адаптация сотрудников склада, зала GOODSPORTS, опта, RAGEX и офиса. Люди, даты и ответы вымышлены: к Битрикс24 и к живым
          кадровым данным кабинет не подключён.
        </p>
        <h2>Возможности демо:</h2>
        <ol>
          <li>Войти кадровиком и открыть очередь красных карточек.</li>
          <li>Назначить наставника из роли руководителя склада.</li>
          <li>Отметить умения из роли наставника.</li>
          <li>Посмотреть сводку директора.</li>
        </ol>
      </div>
      <div>
        {error && <p className="banner warn">{error}</p>}
        {groups.map((group) => (
          <section key={group[0].role} className="login-group">
            <h2>{group[0].role_label}</h2>
            <div className="account-list">
              {group.map((account) => (
                <button key={account.username} className="account" disabled={pending === account.username} onClick={() => enter(account.username)}>
                  <strong>{account.full_name}</strong>
                  <span>{account.title}</span>
                  <span>{account.location_name}</span>
                </button>
              ))}
            </div>
          </section>
        ))}
        <p className="fine">Пароль у всех один: demo. Кнопка входит сразу.</p>
      </div>
    </div>
  );
}
