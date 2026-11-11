import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { CardDetail, Meta } from "../types";

export function NewCardPage() {
  const navigate = useNavigate();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState("");
  const [position, setPosition] = useState("");
  const [locationId, setLocationId] = useState("");
  const [managerId, setManagerId] = useState("");
  const [mentorId, setMentorId] = useState("");
  const [probation, setProbation] = useState(90);
  const [shared, setShared] = useState(false);
  const [shiftFrom, setShiftFrom] = useState("");
  const [shiftTo, setShiftTo] = useState("");
  const [shiftNote, setShiftNote] = useState("");

  useEffect(() => {
    api<Meta>("/api/meta").then((data) => {
      setMeta(data);
      setPosition(data.positions[0]?.code || "");
    });
  }, []);

  const selected = meta?.positions.find((item) => item.code === position);
  const locations = meta?.locations.filter((item) => item.department_code === selected?.track_code) || [];
  const location = locations.find((item) => String(item.id) === locationId) || locations[0];
  const managers = meta?.people.filter((item) => item.role === "manager" && item.location_id === location?.id) || [];
  const mentors = meta?.people.filter((item) => item.role === "mentor" && item.location_id === location?.id) || [];

  useEffect(() => {
    if (location && String(location.id) !== locationId) setLocationId(String(location.id));
  }, [location, locationId]);

  useEffect(() => {
    if (managers[0] && String(managers[0].id) !== managerId) setManagerId(String(managers[0].id));
  }, [managers, managerId]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    if (!shiftFrom || !shiftTo || shiftTo <= shiftFrom) {
      setError("Укажите часы смены: конец должен быть позже начала");
      return;
    }
    const note = shiftNote.trim();
    const schedule = note ? `${shiftFrom}–${shiftTo}, ${note}` : `${shiftFrom}–${shiftTo}`;
    try {
      const card = await api<CardDetail>("/api/cards", {
        method: "POST",
        body: JSON.stringify({
          full_name: String(form.get("full_name") || ""),
          position_code: position,
          location_id: Number(locationId),
          start_date: String(form.get("start_date") || ""),
          probation_days: probation,
          first_shift_schedule: schedule,
          mentor_id: mentorId ? Number(mentorId) : null,
          manager_id: Number(managerId),
          hire_source: String(form.get("source") || ""),
          shared_warehouse: shared,
        }),
      });
      navigate(`/cards/${card.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось создать карточку");
    }
  }

  if (!meta) return <p className="muted">Готовим форму…</p>;

  return (
    <div className="page narrow">
      <header className="page-head">
        <div>
          <p className="eyebrow">Новый выход</p>
          <h1>Зафиксировать выход</h1>
          <p className="lead">
            В рабочей системе это делает робот Битрикс24 в момент статуса «выходит». Здесь кадровик заводит выход вручную, и
            точки на 1, 7, 14, 30, 60 и 90 дней создаются сразу.
          </p>
        </div>
      </header>
      {error && <p className="banner warn">{error}</p>}
      <form className="form" onSubmit={submit}>
        <label>
          ФИО
          <input name="full_name" required minLength={5} placeholder="Имя Фамилия" />
        </label>
        <label>
          Должность
          <select value={position} onChange={(event) => setPosition(event.target.value)}>
            {meta.positions.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name} · {item.track_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Точка
          <select value={locationId} onChange={(event) => setLocationId(event.target.value)}>
            {locations.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Дата выхода
          <input name="start_date" type="date" required />
        </label>
        <label>
          Испытание
          <select value={probation} onChange={(event) => setProbation(Number(event.target.value))}>
            {meta.probation_options.map((item) => (
              <option key={item.days} value={item.days}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <div className="shift">
          <p className="shift-title">График первой смены</p>
          <div className="shift-hours">
            <label>
              С
              <input type="time" required step={3600} value={shiftFrom} onChange={(event) => setShiftFrom(event.target.value)} />
            </label>
            <label>
              До
              <input type="time" required step={3600} value={shiftTo} onChange={(event) => setShiftTo(event.target.value)} />
            </label>
          </div>
          <label>
            Комментарий
            <input
              value={shiftNote}
              maxLength={200}
              placeholder="зал, рядом с наставником"
              onChange={(event) => setShiftNote(event.target.value)}
            />
          </label>
        </div>
        <label>
          Руководитель
          <select value={managerId} onChange={(event) => setManagerId(event.target.value)}>
            {managers.map((item) => (
              <option key={item.id} value={item.id}>
                {item.full_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Наставник, если уже известен
          <select value={mentorId} onChange={(event) => setMentorId(event.target.value)}>
            <option value="">Пока не назван</option>
            {mentors.map((item) => (
              <option key={item.id} value={item.id}>
                {item.full_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Источник найма
          <input name="source" list="sources" required defaultValue={meta.sources[0]} />
          <datalist id="sources">
            {meta.sources.map((source) => (
              <option key={source} value={source} />
            ))}
          </datalist>
        </label>
        {selected?.track_code === "warehouse" && (
          <label className="checkline">
            <input type="checkbox" checked={shared} onChange={(event) => setShared(event.target.checked)} />
            Склад общий с техникой RAGEX: добавить пункт про гарантийный стикер
          </label>
        )}
        <button className="btn" type="submit">
          Создать карточку
        </button>
      </form>
    </div>
  );
}
