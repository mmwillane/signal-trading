import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { CaretRight, Sparkle, ShieldCheck, PencilSimple } from "@phosphor-icons/react";
import { api, type DashboardItem } from "../api/client";
import { money, moneyCompact, pct, changeTone, num } from "../lib/format";
import { Reveal } from "../components/Reveal";
import { Bezel, Pill, Eyebrow, ConfidenceRing, LiveBadge } from "../components/ui";
import { Sparkline } from "../components/Sparkline";
import { CardSkeleton, ErrorState } from "../components/Skeleton";
import { SettingsSheet } from "../components/SettingsSheet";
import { useUserSettings } from "../lib/userSettings";

export function Dashboard() {
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api.settings() });
  const user = useUserSettings();
  const [editing, setEditing] = useState(false);

  const dash = useQuery({
    queryKey: ["dashboard", user.capital, user.risk, user.fractional, user.moreSignals, user.currency, user.tf],
    queryFn: () => api.dashboard(true, user.capital, user.risk, user.fractional, user.moreSignals, user.currency, user.tf),
    refetchInterval: 30_000,           // rafraîchissement auto ~30 s (live-ish)
  });

  const TF_LABEL: Record<string, string> = { "1m": "1 min", "5m": "5 min", "15m": "15 min", "1h": "1 h", "1d": "Journalier" };
  const tfLabel = TF_LABEL[dash.data?.timeframe ?? user.tf] ?? "Journalier";

  // Devise de COMPTE (capital/risque) : choix utilisateur. Les PRIX restent en USD.
  const currency = dash.data?.currency ?? user.currency ?? "USD";
  const anyLive = dash.data?.items.some((i) => i.is_live) ?? false;

  // Valeurs effectives affichées (réponse serveur = déjà l'override utilisateur).
  const capital = dash.data?.capital ?? user.capital ?? settings.data?.capital ?? null;
  const riskFrac = dash.data?.risk_per_trade ?? user.risk ?? settings.data?.risk_per_trade ?? null;
  const riskAmount = dash.data?.risk_amount ?? (capital && riskFrac ? capital * riskFrac : null);

  return (
    <div className="space-y-8">
      {/* Hero */}
      <Reveal>
        <div className="space-y-4 pt-2">
          <Eyebrow>
            <Sparkle size={11} weight="fill" color="#34d399" /> Aide à la décision
          </Eyebrow>
          <h1
            className="text-4xl sm:text-5xl font-semibold tracking-tight leading-[1.05]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Tes signaux du jour,
            <br />
            <span style={{ color: "var(--color-muted)" }}>prêts à valider.</span>
          </h1>
        </div>
      </Reveal>

      {/* Bandeau capital / risque / setups */}
      <Reveal delay={80}>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Eyebrow>Ton compte</Eyebrow>
              <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold" style={{ backgroundColor: "rgba(52,211,153,0.12)", color: "#5be0ae" }}>
                {tfLabel}
              </span>
            </div>
            <button
              onClick={() => setEditing(true)}
              className="press flex items-center gap-1.5 rounded-full px-3 py-1.5"
              style={{ backgroundColor: "rgba(52,211,153,0.12)", color: "#5be0ae" }}
              aria-label="Régler capital, risque, devise et style"
            >
              <PencilSimple size={12} weight="bold" />
              <span className="text-[11px] font-semibold">Régler</span>
            </button>
          </div>
          <Bezel className="p-1.5">
            <div className="grid grid-cols-3 divide-x" style={{ borderColor: "var(--color-line)" }}>
              <Metric label="Capital" value={capital != null ? moneyCompact(capital, currency) : "—"} />
              <Metric
                label="Risque / trade"
                value={riskFrac != null ? `${num(riskFrac * 100, 0)}%` : "—"}
                sub={riskAmount != null ? moneyCompact(riskAmount, currency) : ""}
              />
              <Metric label="Setups" value={dash.data ? String(dash.data.n_setups) : "—"} accent />
            </div>
          </Bezel>
        </div>
      </Reveal>

      {editing && capital != null && riskFrac != null && (
        <SettingsSheet
          currentCapital={capital}
          currentRiskPct={Math.round(riskFrac * 100 * 100) / 100}
          currentFractional={user.fractional}
          currentMoreSignals={user.moreSignals}
          currency={currency}
          currentTf={user.tf}
          onClose={() => setEditing(false)}
        />
      )}

      {/* Liste watchlist */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Eyebrow>Watchlist</Eyebrow>
          <div className="flex items-center gap-2">
            {dash.isFetching && (
              <span className="text-[10px]" style={{ color: "var(--color-faint)" }}>Sync…</span>
            )}
            <LiveBadge live={anyLive} />
          </div>
        </div>

        {dash.isLoading && (
          <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        )}

        {dash.isError && <ErrorState message={(dash.error as Error).message} />}

        {dash.data && (
          <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
            {dash.data.items.map((item, i) => (
              <Reveal key={item.symbol} delay={i * 60}>
                <InstrumentRow item={item} />
              </Reveal>
            ))}
          </div>
        )}
      </div>

      {/* Rappel lecture seule */}
      <Reveal>
        <div className="flex items-center gap-3 rounded-2xl p-4 hairline" style={{ backgroundColor: "rgba(52,211,153,0.04)" }}>
          <ShieldCheck size={22} weight="light" color="#34d399" className="shrink-0" />
          <p className="text-[12px] leading-relaxed" style={{ color: "var(--color-muted)" }}>
            Cet assistant <strong style={{ color: "var(--color-text)" }}>n'exécute jamais d'ordre</strong>. Il lit le marché et propose — tu décides et exécutes toi-même sur ta plateforme.
          </p>
        </div>
      </Reveal>
    </div>
  );
}

function Metric({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: boolean }) {
  return (
    <div className="px-3 py-3 text-center">
      <div className="eyebrow">{label}</div>
      <div
        className="mt-1 text-lg font-semibold tabular-nums"
        style={{ fontFamily: "var(--font-display)", color: accent ? "var(--color-emerald)" : "var(--color-text)" }}
      >
        {value}
      </div>
      {sub && <div className="text-[10px]" style={{ color: "var(--color-faint)" }}>{sub}</div>}
    </div>
  );
}

function InstrumentRow({ item }: { item: DashboardItem }) {
  if (item.status !== "ok") {
    return (
      <Bezel className="p-4">
        <div className="flex items-center justify-between">
          <span className="font-semibold" style={{ fontFamily: "var(--font-display)" }}>{item.symbol}</span>
          <span className="text-xs" style={{ color: "var(--color-faint)" }}>Données insuffisantes</span>
        </div>
      </Bezel>
    );
  }

  const tone = changeTone(item.change_pct ?? 0);
  const setup = item.has_setup && item.proposal;

  return (
    <Link to={`/instrument/${item.symbol}`} className="block">
      <Bezel className="p-4 press">
        <div className="flex items-center gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-[17px]" style={{ fontFamily: "var(--font-display)" }}>{item.symbol}</span>
              {setup && (
                <Pill tone={item.proposal!.direction === "buy" ? "buy" : "sell"} dot>
                  {item.proposal!.direction === "buy" ? "Achat" : "Vente"}
                </Pill>
              )}
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-[15px] tabular-nums" style={{ color: "var(--color-muted)" }}>
                {money(item.price ?? 0, "USD")}
              </span>
              <span
                className="text-xs font-semibold tabular-nums"
                style={{ color: tone === "up" ? "#5be0ae" : tone === "down" ? "#ff8497" : "#f5c451" }}
              >
                {pct(item.change_pct ?? 0)}
              </span>
            </div>
          </div>

          <Sparkline data={item.spark ?? []} tone={tone} />

          <div className="flex items-center gap-1.5 pl-1">
            {setup ? (
              <ConfidenceRing score={item.confidence ?? item.proposal!.confidence} size={42} />
            ) : (
              <span className="text-[10px] max-w-[64px] text-right leading-tight" style={{ color: "var(--color-faint)" }}>
                Pas de setup
              </span>
            )}
            <CaretRight size={16} weight="light" color="#6b7280" />
          </div>
        </div>
      </Bezel>
    </Link>
  );
}
