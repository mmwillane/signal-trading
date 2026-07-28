import { type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { ChartLineUp, Newspaper, TestTube, Wallet, Pulse, Notebook } from "@phosphor-icons/react";

const TABS = [
  { to: "/", label: "Signaux", icon: ChartLineUp },
  { to: "/journal", label: "Journal", icon: Notebook },
  { to: "/backtest", label: "Backtest", icon: TestTube },
  { to: "/news", label: "Actus", icon: Newspaper },
  { to: "/portfolio", label: "Comptes", icon: Wallet },
];

function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <span
        className="w-7 h-7 rounded-xl flex items-center justify-center"
        style={{ background: "linear-gradient(135deg, rgba(52,211,153,0.25), rgba(139,124,246,0.2))" }}
      >
        <Pulse size={16} weight="bold" color="#34d399" className="live-dot" />
      </span>
      <span className="font-semibold tracking-tight" style={{ fontFamily: "var(--font-display)" }}>
        Signal
      </span>
    </div>
  );
}

function ReadOnlyBadge() {
  return (
    <span className="eyebrow flex items-center gap-1.5">
      <span className="w-1.5 h-1.5 rounded-full live-dot" style={{ backgroundColor: "var(--color-emerald)" }} />
      Lecture seule
    </span>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const loc = useLocation();
  const onDetail = loc.pathname.startsWith("/instrument/");

  return (
    <div className="relative min-h-[100dvh]">
      <div className="mesh-bg" />
      <div className="grain" />

      {/* ---- Barre latérale (desktop uniquement) ---- */}
      <aside
        className="hidden lg:flex lg:flex-col lg:fixed lg:inset-y-0 lg:left-0 lg:w-64 z-40 px-5 py-7"
        style={{ borderRight: "1px solid var(--color-line)", backgroundColor: "rgba(8,9,11,0.6)" }}
      >
        <Brand />
        <nav className="mt-10 flex flex-col gap-1.5">
          {TABS.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === "/"} className="press">
              {({ isActive }) => (
                <div
                  className="flex items-center gap-3 rounded-2xl px-4 py-3 transition-all duration-500"
                  style={{
                    color: isActive ? "var(--color-text)" : "var(--color-muted)",
                    backgroundColor: isActive ? "rgba(255,255,255,0.05)" : "transparent",
                  }}
                >
                  <Icon size={20} weight={isActive ? "fill" : "light"} color={isActive ? "#34d399" : undefined} />
                  <span className="text-sm font-medium">{label}</span>
                </div>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto">
          <ReadOnlyBadge />
        </div>
      </aside>

      {/* ---- Barre supérieure (mobile uniquement) ---- */}
      <header className="lg:hidden sticky top-0 z-40 px-4 pt-4">
        <div className="glass rounded-full max-w-lg mx-auto px-4 py-2.5 flex items-center justify-between">
          <Brand />
          <ReadOnlyBadge />
        </div>
      </header>

      {/* ---- Contenu ---- */}
      <div className="lg:pl-64">
        <main className="max-w-lg lg:max-w-6xl mx-auto px-4 lg:px-10 pb-32 lg:pb-16 pt-6 lg:pt-10">
          {children}
        </main>
      </div>

      {/* ---- Nav flottante (mobile uniquement) ---- */}
      {!onDetail && (
        <nav className="lg:hidden fixed bottom-0 inset-x-0 z-40 px-4 pb-5 pt-2 pointer-events-none">
          <div
            className="glass rounded-full max-w-md mx-auto p-1.5 flex items-center justify-between pointer-events-auto"
            style={{ marginBottom: "env(safe-area-inset-bottom)" }}
          >
            {TABS.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} end={to === "/"} className="flex-1 press" aria-label={label}>
                {({ isActive }) => (
                  <div
                    className="flex flex-col items-center gap-1 py-2 rounded-full transition-all duration-500"
                    style={{
                      color: isActive ? "var(--color-text)" : "var(--color-faint)",
                      backgroundColor: isActive ? "rgba(255,255,255,0.06)" : "transparent",
                    }}
                  >
                    <Icon size={20} weight={isActive ? "fill" : "light"} color={isActive ? "#34d399" : undefined} />
                    <span className="text-[10px] font-medium">{label}</span>
                  </div>
                )}
              </NavLink>
            ))}
          </div>
        </nav>
      )}
    </div>
  );
}
