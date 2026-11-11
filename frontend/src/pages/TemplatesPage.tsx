import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { SessionUser, TrackTemplate } from "../types";

const INCLUDE: Record<string, string> = {
  always: "всем в треке",
  position: "только должности",
  shared_warehouse: "если склад общий с RAGEX",
};

export function TemplatesPage({ user }: { user: SessionUser }) {
  const [tracks, setTracks] = useState<TrackTemplate[]>([]);
  const [error, setError] = useState("");

  function load() {
    api<TrackTemplate[]>("/api/templates").then(setTracks).catch((reason) => setError(reason.message));
  }

  useEffect(load, []);

  async function toggle(id: number, isActive: boolean) {
    setError("");
    try {
      await api(`/api/templates/${id}`, { method: "PATCH", body: JSON.stringify({ is_active: !isActive }) });
      load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не сохранилось");
    }
  }

  async function add(event: FormEvent<HTMLFormElement>, code: string) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError("");
    try {
      await api(`/api/tracks/${code}/items`, {
        method: "POST",
        body: JSON.stringify({
          title: String(form.get("title") || ""),
          checkpoint_day: Number(form.get("day") || 1),
          is_critical: form.get("critical") === "on",
        }),
      });
      event.currentTarget.reset();
      load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Пункт не добавлен");
    }
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <p className="eyebrow">Содержание</p>
          <h1>Чек-листы треков</h1>
          <p className="lead">
            Новый пункт попадает в следующие карточки. Уже открытые карточки не переписываются. Критических пунктов в треке не
            больше пяти.
          </p>
        </div>
      </header>
      {error && <p className="banner warn">{error}</p>}
      {tracks.map((track) => (
        <section key={track.code} className="track-block">
          <h2>
            {track.name}{" "}
            <span className={track.critical_count > track.critical_limit ? "count red" : "count"}>
              {track.critical_count} из {track.critical_limit} критических
            </span>
          </h2>
          <ul className="template-list">
            {track.items.map((item) => (
              <li key={item.id} className={item.is_active ? "" : "off"}>
                <div>
                  <strong>{item.day}-й день.</strong> {item.title}{" "}
                  {item.is_critical && <span className="tag">критический</span>}
                  <span className="muted"> {INCLUDE[item.include_mode] || item.include_mode}</span>
                  {item.position_code && <span className="muted"> · {item.position_code}</span>}
                </div>
                {user.role === "hr" && (
                  <button className="btn ghost slim" onClick={() => toggle(item.id, item.is_active)}>
                    {item.is_active ? "Выключить для новых" : "Включить"}
                  </button>
                )}
              </li>
            ))}
          </ul>
          {user.role === "hr" && (
            <form className="inline-form" onSubmit={(event) => add(event, track.code)}>
              <input name="title" required minLength={8} placeholder="Новый наблюдаемый пункт" />
              <select name="day" defaultValue="14">
                <option value="1">1-й день</option>
                <option value="7">7-й день</option>
                <option value="14">14-й день</option>
                <option value="30">30-й день</option>
              </select>
              <label className="checkline">
                <input name="critical" type="checkbox" /> критический
              </label>
              <button className="btn" type="submit">
                Добавить
              </button>
            </form>
          )}
        </section>
      ))}
    </div>
  );
}
