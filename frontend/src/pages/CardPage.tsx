import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, fmt } from "../api";
import type { Answer, CardDetail, CheckItem, Meta, Signal } from "../types";

const STATUS: Record<string, string> = {
  done: "в срок",
  done_late: "с опозданием",
  overdue: "просрочена",
  open: "пора отметить",
  future: "впереди",
  skipped: "не закрыта",
};

export function CardPage() {
  const { id } = useParams();
  const [card, setCard] = useState<CardDetail | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState("");

  function load() {
    setError("");
    return api<CardDetail>(`/api/cards/${id}`).then(setCard).catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Карточка не открылась");
    });
  }

  useEffect(() => {
    load();
    api<Meta>("/api/meta").then(setMeta).catch(() => undefined);
  }, [id]);

  async function act(path: string, body: unknown) {
    setError("");
    try {
      const next = await api<CardDetail>(path, { method: "POST", body: JSON.stringify(body) });
      setCard(next);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не сохранилось");
    }
  }

  async function patch(body: unknown) {
    setError("");
    try {
      const next = await api<CardDetail>(`/api/cards/${id}`, { method: "PATCH", body: JSON.stringify(body) });
      setCard(next);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не сохранилось");
    }
  }

  if (error && !card) return <p className="banner warn">{error}</p>;
  if (!card) return <p className="muted">Открываем карточку…</p>;

  const mentorOptions = (meta?.people || []).filter((person) => person.role === "mentor");
  const sameLocationMentors = mentorOptions.filter((person) => {
    const location = meta?.locations.find((item) => item.name === card.location_name);
    return person.location_id === location?.id;
  });

  const days = [...new Set(card.items.map((item) => item.day))];

  return (
    <div className="page card-page" key={card.id}>
      <header className="page-head">
        <div>
          <p className="eyebrow">
            {card.track_name} · {card.location_name}
          </p>
          <h1>{card.full_name}</h1>
          <p className="lead">
            {card.position_name}. Выход {fmt(card.start_date)}. Испытание до {fmt(card.probation_end_date)}
            {card.probation_days === 0 ? " (без испытания)" : ` (${card.probation_days} дн.)`}. Источник: {card.hire_source}.
          </p>
        </div>
        <span className="stage big" data-stage={card.stage}>
          {card.stage_label}
        </span>
      </header>
      {error && <p className="banner warn">{error}</p>}
      {card.critical_count > card.critical_limit && (
        <p className="banner warn">
          В карточке {card.critical_count} критических пунктов при лимите {card.critical_limit}. Лишний пункт включён, потому что
          отмечен общий склад с RAGEX. На планёрке решите, какой пункт снять.
        </p>
      )}
      {card.separation_started && !card.dismissed_date && (
        <p className="banner warn">Расставание запущено. Кадрам или руководителю нужно внести дату увольнения в решении.</p>
      )}
      <p className="mentor-note">Отметка — «умение есть» или «нет». Шкалы «плохой сотрудник» здесь нет.</p>

      <section className="facts">
        <div>
          <span>Наставник</span>
          {card.permissions.assign_mentor ? (
            <select
              value={card.mentor?.id || ""}
              onChange={(event) => {
                const value = event.target.value;
                if (!value) patch({ clear_mentor: true });
                else patch({ mentor_id: Number(value) });
              }}
            >
              <option value="">Не назначен</option>
              {(sameLocationMentors.length ? sameLocationMentors : mentorOptions).map((person) => (
                <option key={person.id} value={person.id}>
                  {person.full_name}
                </option>
              ))}
            </select>
          ) : (
            <strong>{card.mentor_name || "не назначен"}</strong>
          )}
        </div>
        <div>
          <span>Руководитель</span>
          <strong>{card.manager_name}</strong>
        </div>
        <div>
          <span>График первой смены</span>
          <strong>{card.first_shift_schedule}</strong>
        </div>
        <div>
          <span>Допуск</span>
          <strong>{card.admission_label}</strong>
        </div>
      </section>

      <ol className="timeline">
        {card.checkpoints.map((point) => (
          <li key={point.day} data-status={point.status}>
            <span>{point.label}</span>
            <strong>{fmt(point.due_date)}</strong>
            <em>{STATUS[point.status] || point.status}</em>
          </li>
        ))}
      </ol>

      <div className="split">
        <section>
          <h2>Умения</h2>
          {days.map((day) => (
            <div key={day} className="day-group">
              <h3>{day}-й день</h3>
              {card.items
                .filter((item) => item.day === day)
                .map((item) => (
                  <CheckRow key={item.id} item={item} onMark={(mark) => act(`/api/cards/${card.id}/items/${item.id}/mark`, { mark })} />
                ))}
            </div>
          ))}
        </section>
        <section className="side-col">
          <h2>Сигналы</h2>
          {card.signals.length === 0 && <p className="muted">Открытых сигналов нет.</p>}
          {card.signals.map((signal) => (
            <SignalBox key={signal.id} signal={signal} onResolve={(body) => act(`/api/signals/${signal.id}/resolve`, body)} />
          ))}
          {card.waiting.length > 0 && (
            <>
              <h3>Ждут повторной проверки</h3>
              {card.waiting.map((signal) => (
                <p key={signal.id} className="muted">
                  {signal.title}: {fmt(signal.recheck_date)}. {signal.comment}
                </p>
              ))}
            </>
          )}

          {card.track_code === "warehouse" || card.track_code === "retail" ? (
            <AdmissionBox card={card} onSave={(body) => act(`/api/cards/${card.id}/admission`, body)} />
          ) : null}

          {card.pulses.map((pulse) => (
            <PulseBox key={pulse.day} card={card} onSave={(body) => act(`/api/cards/${card.id}/pulse`, body)} day={pulse.day} />
          ))}

          {card.probation_days >= 30 && (
            <Day30Box card={card} onSave={(body) => act(`/api/cards/${card.id}/day30`, body)} />
          )}
          {card.permissions.day60 || card.day60_stable !== null ? (
            <Day60Box card={card} onSave={(body) => act(`/api/cards/${card.id}/day60`, body)} />
          ) : null}
          <DecisionBox card={card} onSave={(body) => act(`/api/cards/${card.id}/decision`, body)} />

          {card.resolved_signals.length > 0 && (
            <details>
              <summary>Разобранные сигналы</summary>
              {card.resolved_signals.map((signal) => (
                <p key={signal.id} className="muted">
                  {signal.title}: {signal.resolution_label || "снят"}. {signal.comment}
                </p>
              ))}
            </details>
          )}

          <h2>Ход карточки</h2>
          <ul className="events">
            {card.events.map((event, index) => (
              <li key={`${event.at}-${index}`}>
                <span>{fmt(event.at)}</span>
                <p>
                  <strong>{event.actor}.</strong> {event.text}
                </p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}

function CheckRow({ item, onMark }: { item: CheckItem; onMark: (mark: "yes" | "not_yet") => void }) {
  return (
    <div className="check">
      <div>
        {item.is_critical && <span className="tag">критический</span>}
        <p>{item.title}</p>
      </div>
      <div className="check-actions">
        <button type="button" className={item.mark === "yes" ? "mark-btn yes" : "mark-btn"} disabled={!item.can_mark} onClick={() => onMark("yes")}>
          Да
        </button>
        <button type="button" className={item.mark === "not_yet" ? "mark-btn no" : "mark-btn"} disabled={!item.can_mark} onClick={() => onMark("not_yet")}>
          {item.mark === "not_yet" && item.fail_count > 0 ? `Нет х${item.fail_count}` : "Нет"}
        </button>
      </div>
    </div>
  );
}

function SignalBox({ signal, onResolve }: { signal: Signal; onResolve: (body: unknown) => void }) {
  const [resolution, setResolution] = useState(signal.allow_fixed ? "fixed" : "recheck");
  const [comment, setComment] = useState("");
  const [recheck, setRecheck] = useState("");
  const [dismissed, setDismissed] = useState("");
  return (
    <article className={`signal ${signal.severity}`}>
      <p className="signal-kicker">{signal.severity === "red" ? "Красный" : "Жёлтый"}{signal.overdue ? " · срок прошёл" : ""}</p>
      <h3>{signal.title}</h3>
      <p>{signal.detail}</p>
      {signal.owner && <p className="muted">Владелец: {signal.owner.full_name}</p>}
      {signal.can_resolve && (
        <form
          className="resolve"
          onSubmit={(event) => {
            event.preventDefault();
            onResolve({
              resolution,
              comment,
              recheck_date: recheck || null,
              dismissed_date: dismissed || null,
            });
          }}
        >
          <div className="choices">
            {signal.allow_fixed && (
              <label>
                <input type="radio" checked={resolution === "fixed"} onChange={() => setResolution("fixed")} /> Поправили условие
              </label>
            )}
            <label>
              <input type="radio" checked={resolution === "recheck"} onChange={() => setResolution("recheck")} /> Повторная проверка
            </label>
            <label>
              <input type="radio" checked={resolution === "separation"} onChange={() => setResolution("separation")} /> Расставание
            </label>
          </div>
          {!signal.allow_fixed && resolution === "recheck" && (
            <p className="fine">Пока условие в карточке открыто, сигнал сам не гаснет. Его можно отложить проверкой или закрыть расставанием.</p>
          )}
          <textarea value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Что сделали или что проверить" rows={3} />
          {resolution === "recheck" && <input type="date" value={recheck} onChange={(event) => setRecheck(event.target.value)} />}
          {resolution === "separation" && (
            <label className="inline">
              Дата увольнения, если она уже есть
              <input type="date" value={dismissed} onChange={(event) => setDismissed(event.target.value)} />
            </label>
          )}
          <button className="btn" type="submit">
            Записать исход
          </button>
        </form>
      )}
    </article>
  );
}

function PulseBox({ card, day, onSave }: { card: CardDetail; day: number; onSave: (body: unknown) => void }) {
  const pulse = card.pulses.find((item) => item.day === day)!;
  const [answers, setAnswers] = useState<Record<string, Answer | "">>({
    q1: pulse.q1 || "",
    q2: pulse.q2 || "",
    q3: pulse.q3 || "",
  });
  const [comment, setComment] = useState(pulse.comment || "");
  return (
    <div className="block">
      <h3>Ответы сотрудника, {day}-й день</h3>
      <p className="fine">Наставник записывает со слов после смены. Вопросы не меняются по ходу пилота.</p>
      {card.questions.map((question) => (
        <fieldset key={question.code}>
          <legend>{question.text}</legend>
          <div className="choices">
            {(["yes", "mid", "no"] as Answer[]).map((value) => (
              <label key={value}>
                <input
                  type="radio"
                  name={`${day}-${question.code}`}
                  checked={answers[question.code] === value}
                  onChange={() => setAnswers({ ...answers, [question.code]: value })}
                  disabled={!pulse.can_record}
                />
                {card.answer_labels[value]}
              </label>
            ))}
          </div>
        </fieldset>
      ))}
      <textarea value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Комментарий, если есть" rows={2} disabled={!pulse.can_record} />
      {pulse.can_record ? (
        <button
          className="btn"
          onClick={() => {
            if (!answers.q1 || !answers.q2 || !answers.q3) return;
            onSave({ day, q1: answers.q1, q2: answers.q2, q3: answers.q3, comment });
          }}
        >
          Записать ответы
        </button>
      ) : (
        <p className="fine">Откроется {fmt(pulse.due_date)}.</p>
      )}
    </div>
  );
}

function AdmissionBox({ card, onSave }: { card: CardDetail; onSave: (body: unknown) => void }) {
  const [value, setValue] = useState(card.admission);
  const [note, setNote] = useState(card.admission_note);
  return (
    <div className="block">
      <h3>Допуск к типовой операции</h3>
      <p className="fine">Для склада и зала это 14-й день: можно отпустить на обычную волну или на продажу с возвратом.</p>
      <div className="choices">
        <label>
          <input type="radio" checked={value === "yes"} onChange={() => setValue("yes")} disabled={!card.permissions.admission} /> Работает сам
        </label>
        <label>
          <input type="radio" checked={value === "caveat"} onChange={() => setValue("caveat")} disabled={!card.permissions.admission} /> С оговоркой
        </label>
        <label>
          <input type="radio" checked={value === "none"} onChange={() => setValue("none")} disabled={!card.permissions.admission} /> Допуска нет
        </label>
      </div>
      {value === "caveat" && (
        <textarea value={note} onChange={(event) => setNote(event.target.value)} rows={2} placeholder="Что именно ещё не тянет" disabled={!card.permissions.admission} />
      )}
      {card.permissions.admission ? (
        <button className="btn" onClick={() => onSave({ value, note })}>
          Сохранить допуск
        </button>
      ) : card.checkpoints.find((point) => point.day === 14)?.status === "future" ? (
        <p className="fine">Откроется на 14-й день, {fmt(card.checkpoints.find((point) => point.day === 14)?.due_date)}.</p>
      ) : null}
    </div>
  );
}

function Day30Box({ card, onSave }: { card: CardDetail; onSave: (body: unknown) => void }) {
  const [choice, setChoice] = useState(card.day30_choice || "independent");
  const [reason, setReason] = useState(card.day30_reason || "");
  const [recheck, setRecheck] = useState(card.day30_recheck_date || "");
  return (
    <div className="block">
      <h3>30-й день руководителя</h3>
      {card.day30_choice && (
        <p className="fine">
          Сейчас: {card.day30_choice_label}. {card.day30_reason}
        </p>
      )}
      <div className="choices column">
        <label>
          <input type="radio" checked={choice === "independent"} onChange={() => setChoice("independent")} disabled={!card.permissions.day30} /> Работает сам
        </label>
        <label>
          <input type="radio" checked={choice === "still_with_mentor"} onChange={() => setChoice("still_with_mentor")} disabled={!card.permissions.day30} /> Ещё с наставником
        </label>
        <label>
          <input type="radio" checked={choice === "role_unfit"} onChange={() => setChoice("role_unfit")} disabled={!card.permissions.day30} /> Роль не подходит
        </label>
      </div>
      {choice !== "independent" && (
        <textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={2} placeholder="Одна причина" disabled={!card.permissions.day30} />
      )}
      {choice === "still_with_mentor" && (
        <label className="inline">
          Повторная проверка в пределах двух недель
          <input type="date" value={recheck} onChange={(event) => setRecheck(event.target.value)} disabled={!card.permissions.day30} />
        </label>
      )}
      {card.permissions.day30 ? (
        <button className="btn" onClick={() => onSave({ choice, reason, recheck_date: recheck || null })}>
          Закрыть 30-й день
        </button>
      ) : (
        <p className="fine">Откроется на 30-й день.</p>
      )}
    </div>
  );
}

function Day60Box({ card, onSave }: { card: CardDetail; onSave: (body: unknown) => void }) {
  const [stable, setStable] = useState(card.day60_stable !== false);
  const [note, setNote] = useState(card.day60_note || "");
  return (
    <div className="block">
      <h3>60-й день</h3>
      <div className="choices">
        <label>
          <input type="radio" checked={stable} onChange={() => setStable(true)} disabled={!card.permissions.day60} /> Отката нет
        </label>
        <label>
          <input type="radio" checked={!stable} onChange={() => setStable(false)} disabled={!card.permissions.day60} /> Есть откат
        </label>
      </div>
      {!stable && <textarea value={note} onChange={(event) => setNote(event.target.value)} rows={2} placeholder="В чём откат" />}
      {card.permissions.day60 && (
        <button className="btn" onClick={() => onSave({ stable, note })}>
          Отметить 60-й день
        </button>
      )}
    </div>
  );
}

function DecisionBox({ card, onSave }: { card: CardDetail; onSave: (body: unknown) => void }) {
  const [decision, setDecision] = useState(card.probation_decision || "confirm");
  const [comment, setComment] = useState(card.probation_decision_comment || "");
  const [dismissed, setDismissed] = useState(card.dismissed_date || "");
  const [transfer, setTransfer] = useState(card.transfer_title || "");
  return (
    <div className="block">
      <h3>Решение по испытанию</h3>
      <p className="fine">{card.permissions.decision_hint}</p>
      {card.probation_decision && (
        <p>
          Записано: {card.probation_decision_label}. {card.probation_decision_comment}
          {card.dismissed_date ? ` Дата увольнения ${fmt(card.dismissed_date)}.` : ""}
          {card.transfer_title ? ` Новая должность: ${card.transfer_title}.` : ""}
        </p>
      )}
      {card.permissions.decision && (
        <>
          <div className="choices column">
            <label>
              <input type="radio" checked={decision === "confirm"} onChange={() => setDecision("confirm")} /> Подтверждаем
            </label>
            <label>
              <input type="radio" checked={decision === "separate"} onChange={() => setDecision("separate")} /> Расстаёмся
            </label>
            <label>
              <input type="radio" checked={decision === "transfer"} onChange={() => setDecision("transfer")} /> Переводим внутри точки
            </label>
          </div>
          <textarea value={comment} onChange={(event) => setComment(event.target.value)} rows={3} placeholder="На чём основано решение" />
          {decision === "separate" && <input type="date" value={dismissed} onChange={(event) => setDismissed(event.target.value)} />}
          {decision === "transfer" && (
            <input value={transfer} onChange={(event) => setTransfer(event.target.value)} placeholder="Должность внутри точки" />
          )}
          <button
            className="btn"
            onClick={() => onSave({ decision, comment, dismissed_date: dismissed || null, transfer_title: transfer })}
          >
            Записать решение
          </button>
        </>
      )}
    </div>
  );
}
