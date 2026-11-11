import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmt } from "../api";
import type { QueueResponse, SessionUser } from "../types";

export function QueuePage({ user }: { user: SessionUser }) {
  const [data, setData] = useState<QueueResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<QueueResponse>("/api/queue")
      .then(setData)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Ошибка"));
  }, []);

  const title = user.role === "hr" ? "Разобрать сегодня" : user.role === "director" ? "Красные по функции" : "Сигналы моих людей";
  const lead =
    user.role === "hr"
      ? "В очереди только красные. Жёлтые сюда не попадают: их смотрит руководитель на планёрке."
      : user.role === "director"
        ? "Просрочка видна здесь. Разбор делает руководитель точки, не директор."
        : "Красный сигнал — задача со сроком два рабочих дня. Жёлтый — к планёрке, без карточки у кадров.";

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <p className="eyebrow">Очередь</p>
          <h1>{title}</h1>
          <p className="lead">{lead}</p>
        </div>
      </header>
      {error && <p className="banner warn">{error}</p>}
      {!data ? (
        <p className="muted">Собираем сигналы…</p>
      ) : data.items.length === 0 ? (
        <p className="banner ok">Открытых сигналов нет. Так выглядит утро, когда просрочек нет.</p>
      ) : (
        <div className="stack">
          {data.items.map((row) => (
            <article key={row.signal.id} className={`signal ${row.signal.severity}`}>
              <div>
                <p className="signal-kicker">
                  {row.signal.severity === "red" ? "Красный" : "Жёлтый"}
                  {row.signal.overdue ? " · срок разбора прошёл" : row.signal.due_date ? ` · разобрать до ${fmt(row.signal.due_date)}` : ""}
                </p>
                <h2>{row.signal.title}</h2>
                <p>{row.signal.detail}</p>
                <p className="muted">
                  {row.full_name} · {row.position_name} · {row.location_name}
                  {row.signal.owner ? ` · владелец: ${row.signal.owner.full_name}` : ""}
                </p>
              </div>
              <Link className="btn slim" to={`/cards/${row.id}`}>
                Открыть карточку
              </Link>
            </article>
          ))}
        </div>
      )}
      {data && data.waiting.length > 0 && (
        <section className="later">
          <h2>Ждут повторной проверки</h2>
          <ul>
            {data.waiting.map((row) => (
              <li key={row.signal.id}>
                <Link to={`/cards/${row.id}`}>{row.full_name}</Link>
                <span>
                  {row.signal.title} · {fmt(row.signal.recheck_date)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
