import { NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "../api";
import type { SessionUser } from "../types";

const LABELS: Record<string, string> = {
  queue: "Очередь",
  cards: "Карточки",
  new: "Новый выход",
  summary: "Сводка",
  templates: "Чек-листы",
  guide: "Регламент",
};

export function Shell({ user, onLogout }: { user: SessionUser; onLogout: () => void }) {
  const { pathname } = useLocation();
  async function resetDemo() {
    if (!window.confirm("Вернуть вымышленных сотрудников и очередь к исходному состоянию?")) return;
    await api("/api/demo/reset", { method: "POST", body: "{}" });
    location.reload();
  }

  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">
          <span className="mark">90</span>
          <div>
            <strong>Первые 90</strong>
            <span>Адаптация</span>
          </div>
        </div>
        <nav>
          {user.nav.map((item) => (
            <NavLink
              key={item}
              to={item === "new" ? "/cards/new" : `/${item}`}
              end
              className={({ isActive }) => {
                const cardOpen = item === "cards" && /^\/cards\/\d+$/.test(pathname);
                return isActive || cardOpen ? "active" : "";
              }}
            >
              {LABELS[item]}
            </NavLink>
          ))}
        </nav>
        <div className="userbox">
          <strong>{user.full_name}</strong>
          <span>{user.title}</span>
          {user.location_name && <span>{user.location_name}</span>}
          <button className="btn ghost" onClick={onLogout}>
            Сменить роль
          </button>
          <button className="btn ghost" onClick={resetDemo}>
            Вернуть демо
          </button>
        </div>
      </aside>
      <div className="main">
        <div className="strip">Вымышленные сотрудники. Можно нажимать что угодно и вернуть исходные данные кнопкой слева.</div>
        <Outlet />
      </div>
    </div>
  );
}
