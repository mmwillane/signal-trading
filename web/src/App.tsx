import { Routes, Route } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { Dashboard } from "./screens/Dashboard";
import { Instrument } from "./screens/Instrument";
import { Backtest } from "./screens/Backtest";
import { News } from "./screens/News";
import { Portfolio } from "./screens/Portfolio";
import { Journal } from "./screens/Journal";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/journal" element={<Journal />} />
        <Route path="/instrument/:symbol" element={<Instrument />} />
        <Route path="/backtest" element={<Backtest />} />
        <Route path="/news" element={<News />} />
        <Route path="/portfolio" element={<Portfolio />} />
      </Routes>
    </AppShell>
  );
}
