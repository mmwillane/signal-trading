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

export function AppShell({ children }: { children: ReactNode }) {
  const loc = useLocation();
  const onDetail = loc.pathname.startsWith("/instrument/");

  return (
    <div className="relative min-h-[100dvh]">
      <div className="mesh-bg" />
      <div className="grain" />

      {/* Barre supérieure : marque flottante (jamais collée edge-to-edge). */}
      <header className="sticky top-0 z-40 px-4 pt-4">
        <div className="glass rounded-full max-w-lg mx-auto px-4 py-2.5 flex items-center justify-between">
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
          <span className="eyebrow flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full live-dot" style={{ backgroundColor: "var(--color-emerald)" }} />
            Lecture seule
          </span>
        </div>
      </header>

      <main className="max-w-lg mx-auto px-4 pb-32 pt-6">{children}</main>

      {/* Nav flottante en bas (mobile-first, glass pill détachée). */}
      {!onDetail && (
        <nav className="fixed bottom-0 inset-x-0 z-40 px-4 pb-5 pt-2 pointer-events-none">
          <div className="glass rounded-full max-w-md mx-auto p-1.5 flex items-center justify-between pointer-events-auto"
               style={{ marginBottom: "env(safe-area-inset-bottom)" }}>
            {TABS.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className="flex-1 press"
                aria-label={label}
              >
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
