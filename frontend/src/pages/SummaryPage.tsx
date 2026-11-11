import { useEffect, useState } from "react";
import { api, pct } from "../api";
import type { Ratio, Summary } from "../types";

export function SummaryPage() {
  const [data, setData] = useState<Summary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Summary>("/api/summary")
      .then(setData)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Ошибка"));
  }, []);

  if (error) return <p className="banner warn">{error}</p>;
  if (!data) return <p className="muted">Считаем сводку…</p>;

  const pilot = data.pilot;
  return (
    <div className="page">
      <header className="page-head">
        <div>
          <p className="eyebrow">Сводка · {data.month_label}</p>
          <h1>Сводка по адаптации</h1>
          <p className="lead">
            Выходы, красные сигналы и отметки наставника видны сразу. Долю тех, кто доработал 90 дней, по людям этого месяца
            считать рано: их испытание ещё не закончилось. {data.scope_note}
          </p>
        </div>
      </header>

      <section>
        <h2>Этот месяц в кабинете</h2>
        <div className="kpis">
          <Kpi label="Выходы" value={String(data.operations.starts)} />
          <Kpi label="Красные сейчас" value={String(data.operations.open_reds)} />
          <Kpi label="Красные старше срока" value={String(data.operations.open_reds_overdue)} />
          <Kpi label="Точки закрыты" value={String(data.operations.checkpoints_closed)} />
          <Kpi label="Уволились до 30 дней" value={String(data.operations.left_under_30)} />
          <Kpi label="Уволились до 90 дней" value={String(data.operations.left_under_90)} />
        </div>
        <table className="grid">
          <thead>
            <tr>
              <th>Подразделение</th>
              <th>Выходы</th>
              <th>Красные</th>
              <th>Уволились до 30</th>
              <th>Уволились до 90</th>
              <th>Допуск к 14-му дню</th>
            </tr>
          </thead>
          <tbody>
            {data.operations.by_department.map((row) => (
              <tr key={row.name}>
                <td>{row.name}</td>
                <td>{row.starts}</td>
                <td>{row.open_reds}</td>
                <td>{row.left_under_30}</td>
                <td>{row.left_under_90}</td>
                <td>{row.admitted}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2>Показатели пилота</h2>
        <div className="ratio-list">
          <RatioCard title="Наставник до первого дня" ratio={pilot.mentor_before_day1} />
          <RatioCard title="1-й и 14-й день в срок" ratio={pilot.day1_and_14_on_time} />
          <RatioCard title="Сам к 14-му дню" ratio={pilot.independent_by_14} />
          <RatioCard title="Красные разобраны за 2 дня" ratio={pilot.reds_in_two_days} />
          <RatioCard title="Решение записано в карточке" ratio={pilot.decisions_recorded} />
        </div>
      </section>

      <section>
        <h2>База за 12 месяцев</h2>
        <p className="lead">{data.baseline.caption}</p>
        <div className="kpis">
          <Kpi label="Выходов в базе" value={String(data.baseline.hired)} />
          <Kpi label="Уволились" value={String(data.baseline.left)} />
          <Kpi label="Из них до 90 дней" value={pct(data.baseline.share_leavers_under_90)} />
          <Kpi label="Работали на 30-й день" value={pct(data.baseline.survival_30)} />
          <Kpi label="Работали на 90-й день" value={pct(data.baseline.survival_90)} />
        </div>
        <table className="grid">
          <thead>
            <tr>
              <th>Подразделение</th>
              <th>Выходы</th>
              <th>Уволились</th>
              <th>Из них до 90 дней</th>
              <th>Работали на 90-й день</th>
            </tr>
          </thead>
          <tbody>
            {data.baseline.by_department.map((row) => (
              <tr key={row.name}>
                <td>{row.name}</td>
                <td>{row.hired}</td>
                <td>{row.left}</td>
                <td>{pct(row.share_leavers_under_90)}</td>
                <td>{pct(row.survival_90)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="kpi">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RatioCard({ title, ratio }: { title: string; ratio: Ratio }) {
  const text = ratio.den === 0 ? "пока некого считать" : `${ratio.num} из ${ratio.den}`;
  return (
    <article className="ratio">
      <h3>{title}</h3>
      <strong>{text}</strong>
      <p>{ratio.hint}</p>
    </article>
  );
}
