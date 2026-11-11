import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmt } from "../api";
import type { CardBrief } from "../types";

export function CardsPage() {
  const [cards, setCards] = useState<CardBrief[]>([]);
  const [track, setTrack] = useState("all");
  const [attention, setAttention] = useState("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    api<CardBrief[]>("/api/cards").then(setCards);
  }, []);

  const tracks = useMemo(() => {
    const map = new Map<string, string>();
    cards.forEach((card) => map.set(card.track_code, card.track_name));
    return [...map.entries()];
  }, [cards]);

  const visible = cards.filter((card) => {
    if (track !== "all" && card.track_code !== track) return false;
    if (attention === "red" && card.red_count === 0) return false;
    if (attention === "yellow" && card.yellow_count === 0) return false;
    if (attention === "calm" && (card.red_count > 0 || card.yellow_count > 0)) return false;
    if (query && !card.full_name.toLowerCase().includes(query.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <p className="eyebrow">Карточки</p>
          <h1>Кто сейчас на адаптации</h1>
        </div>
      </header>
      <div className="filters">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Имя" />
        <select value={track} onChange={(event) => setTrack(event.target.value)}>
          <option value="all">Все треки</option>
          {tracks.map(([code, name]) => (
            <option key={code} value={code}>
              {name}
            </option>
          ))}
        </select>
        <select value={attention} onChange={(event) => setAttention(event.target.value)}>
          <option value="all">Любые сигналы</option>
          <option value="red">Есть красные</option>
          <option value="yellow">Есть жёлтые</option>
          <option value="calm">Без сигналов</option>
        </select>
      </div>
      <table className="grid">
        <thead>
          <tr>
            <th>Человек</th>
            <th>Точка</th>
            <th>Выход</th>
            <th>Стадия</th>
            <th>Наставник</th>
            <th>Сигналы</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((card) => (
            <tr key={card.id}>
              <td>
                <Link to={`/cards/${card.id}`}>{card.full_name}</Link>
                <span className="sub">{card.position_name}</span>
              </td>
              <td>{card.location_name}</td>
              <td>{fmt(card.start_date)}</td>
              <td>
                <span className="stage" data-stage={card.stage}>
                  {card.stage_label}
                </span>
              </td>
              <td>{card.mentor_name || "не назначен"}</td>
              <td>
                {card.red_count > 0 && <span className="count red">{card.red_count}</span>}
                {card.yellow_count > 0 && <span className="count yellow">{card.yellow_count}</span>}
                {card.red_count === 0 && card.yellow_count === 0 && <span className="muted">нет</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
