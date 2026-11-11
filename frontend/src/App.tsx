import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { api, setToken, token } from "./api";
import { CardPage } from "./pages/CardPage";
import { CardsPage } from "./pages/CardsPage";
import { GuidePage } from "./pages/GuidePage";
import { LoginPage } from "./pages/LoginPage";
import { NewCardPage } from "./pages/NewCardPage";
import { QueuePage } from "./pages/QueuePage";
import { Shell } from "./pages/Shell";
import { SummaryPage } from "./pages/SummaryPage";
import { TemplatesPage } from "./pages/TemplatesPage";
import type { SessionUser } from "./types";

export function App() {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [ready, setReady] = useState(!token());
  const navigate = useNavigate();

  useEffect(() => {
    if (!token()) return;
    api<SessionUser>("/api/me")
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setReady(true));
  }, []);

  function onLogin(next: SessionUser, authToken: string) {
    setToken(authToken);
    setUser(next);
    navigate(next.role === "director" ? "/summary" : "/queue");
  }

  function onLogout() {
    setToken(null);
    setUser(null);
    navigate("/");
  }

  if (!ready) return <div className="boot">Открываем кабинет…</div>;

  return (
    <Routes>
      <Route path="/" element={user ? <Navigate to={user.role === "director" ? "/summary" : "/queue"} replace /> : <LoginPage onLogin={onLogin} />} />
      <Route element={user ? <Shell user={user} onLogout={onLogout} /> : <Navigate to="/" replace />}>
        <Route path="/queue" element={user ? <QueuePage user={user} /> : <Navigate to="/" replace />} />
        <Route path="/cards" element={<CardsPage />} />
        <Route path="/cards/new" element={<NewCardPage />} />
        <Route path="/cards/:id" element={<CardPage />} />
        <Route path="/summary" element={<SummaryPage />} />
        <Route path="/templates" element={user ? <TemplatesPage user={user} /> : <Navigate to="/" replace />} />
        <Route path="/guide" element={<GuidePage />} />
      </Route>
      <Route path="*" element={<Navigate to={user ? "/queue" : "/"} replace />} />
    </Routes>
  );
}
