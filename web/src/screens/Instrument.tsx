import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import { CaretLeft, ArrowUpRight } from "@phosphor-icons/react";
import { api } from "../api/client";
import { money, pct, num, changeTone, sentimentLabel } from "../lib/format";
import { Bezel, Pill, Eyebrow, ConfidenceRing, LiveBadge } from "../components/ui";
import { Reveal } from "../components/Reveal";
import { PriceChart } from "../components/PriceChart";
import { ProposalCard } from "../components/ProposalCard";
import { Skeleton, ErrorState } from "../components/Skeleton";
import { useUserSettings } from "../lib/userSettings";

const MTF_LABEL: Record<string, string> = {
  "aligné": "intraday aligné",
  "opposé": "intraday opposé",
  neutre: "intraday neutre",
};

const TF_CHIPS = [
  { code: "1m", label: "1m" },
  { code: "5m", label: "5m" },
  { code: "15m", label: "15m" },
  { code: "1h", label: "1h" },
  { code: "1d", label: "Jour" },
];

export function Instrument() {
  const { symbol = "" } = useParams();
  const navigate = useNavigate();
  const user = useUserSettings();
  const [tf, setTf] = useState<string>(user.tf);
  const q = useQuery({
    queryKey: ["instrument", symbol, tf, user.capital, user.risk, user.fractional, user.moreSignals, user.currency],
    queryFn: () => api.instrument(symbol, true, tf, user.capital, user.risk, user.fractional, user.moreSignals, user.currency),
    refetchInterval: 30_000,
  });
  // Devise de compte (proposition) ; les prix restent en USD.
  const currency = q.data?.currency ?? user.currency ?? "USD";

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate(-1)}
        className="press inline-flex items-center gap-1.5 text-sm rounded-full pl-2 pr-4 py-2 hairline"
        style={{ color: "var(--color-muted)" }}
      >
        <CaretLeft size={16} weight="light" /> Retour
      </button>

      {q.isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-10 w-40" />
          <Skeleton className="h-72 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      )}

      {q.isError && <ErrorState message={(q.error as Error).message} />}

      {q.data && q.data.status === "ok" && (
        <>
          <Reveal>
            <div className="flex items-end justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-4xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display)" }}>
                    {q.data.symbol}
                  </h1>
                  <LiveBadge live={q.data.is_live} />
                </div>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="text-xl tabular-nums">{money(q.data.price, "USD")}</span>
                  <span
                    className="text-sm font-semibold tabular-nums"
                    style={{ color: changeTone(q.data.change_pct) === "up" ? "#5be0ae" : changeTone(q.data.change_pct) === "down" ? "#ff8497" : "#f5c451" }}
                  >
                    {pct(q.data.change_pct)}
                  </span>
                </div>
              </div>
              {q.data.has_setup && q.data.proposal ? (
                <ConfidenceRing score={q.data.confidence} size={52} />
              ) : (
                <Pill tone="flat">Pas de setup</Pill>
              )}
            </div>
          </Reveal>

          {/* Corps : 2 colonnes sur ordinateur, empilé sur mobile */}
          <div className="space-y-6 lg:space-y-0 lg:grid lg:grid-cols-3 lg:gap-6 lg:items-start">
            {/* Colonne principale : graphique, indicateurs, tendance, actus */}
            <div className="lg:col-span-2 space-y-6">
              <Reveal delay={60}>
                <Bezel className="p-3">
                  <div className="flex items-center gap-2 px-1 pb-2 pt-1 flex-wrap">
                    <div className="flex gap-1 rounded-full p-1 hairline" style={{ backgroundColor: "rgba(255,255,255,0.02)" }}>
                      {TF_CHIPS.map((c) => (
                        <TfChip key={c.code} active={tf === c.code} onClick={() => setTf(c.code)}>{c.label}</TfChip>
                      ))}
                    </div>
                    <div className="flex items-center gap-3 ml-auto text-[11px]" style={{ color: "var(--color-faint)" }}>
                      <Legend color="#8b7cf6" label="SMA 20" />
                      <Legend color="#f5c451" label="SMA 50" />
                    </div>
                  </div>
                  {q.data.candles.length > 0 ? (
                    <PriceChart candles={q.data.candles} sma20={q.data.sma20} sma50={q.data.sma50} />
                  ) : (
                    <div className="h-[300px] sm:h-[360px] lg:h-[460px] flex items-center justify-center text-sm" style={{ color: "var(--color-faint)" }}>
                      Données intraday indisponibles pour cet instrument.
                    </div>
                  )}
                </Bezel>
              </Reveal>

              <Reveal delay={100}>
                <div className="grid grid-cols-4 gap-2">
                  <Indicator label="RSI" value={num(q.data.indicators.rsi, 0)} tone={q.data.indicators.rsi >= 70 ? "down" : q.data.indicators.rsi <= 30 ? "up" : undefined} />
                  <Indicator label="MACD" value={num(q.data.indicators.macd_hist, 2)} tone={q.data.indicators.macd_hist >= 0 ? "up" : "down"} />
                  <Indicator label="ADX" value={num(q.data.indicators.adx, 0)} tone={q.data.indicators.adx >= 20 ? "up" : "down"} />
                  <Indicator label="Sentiment" value={sentimentLabel(q.data.sentiment).text} />
                </div>
              </Reveal>

              <Reveal delay={120}>
                <div className="flex items-center gap-2 flex-wrap text-[11px]">
                  <span className="rounded-full px-3 py-1 hairline" style={{ color: q.data.indicators.adx >= 20 ? "#5be0ae" : "var(--color-faint)" }}>
                    {q.data.indicators.adx >= 20 ? "Tendance établie" : "Marché sans tendance"} · ADX {num(q.data.indicators.adx, 0)}
                  </span>
                  {q.data.mtf && (
                    <span
                      className="rounded-full px-3 py-1 hairline"
                      style={{ color: q.data.mtf === "aligné" ? "#5be0ae" : q.data.mtf === "opposé" ? "#ff8497" : "var(--color-faint)" }}
                    >
                      {MTF_LABEL[q.data.mtf] ?? q.data.mtf}
                    </span>
                  )}
                </div>
              </Reveal>

              {q.data.news.length > 0 && (
                <Reveal delay={180}>
                  <div className="space-y-3">
                    <Eyebrow>Actualités liées</Eyebrow>
                    <div className="grid gap-3 xl:grid-cols-2">
                      {q.data.news.map((n, i) => (
                        <a key={i} href={n.url ?? "#"} target="_blank" rel="noreferrer" className="block">
                          <Bezel className="p-4 press">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "var(--color-faint)" }}>{n.source}</div>
                                <div className="text-sm leading-snug">{n.title}</div>
                              </div>
                              <ArrowUpRight size={16} weight="light" color="#6b7280" className="shrink-0 mt-0.5" />
                            </div>
                          </Bezel>
                        </a>
                      ))}
                    </div>
                  </div>
                </Reveal>
              )}
            </div>

            {/* Colonne latérale : proposition (collante sur desktop) */}
            <div className="lg:col-span-1">
              <div className="lg:sticky lg:top-10">
                <Reveal delay={140}>
                  <Bezel className="p-5">
                    {q.data.proposal ? (
                      <ProposalCard p={q.data.proposal} currency={currency} />
                    ) : (
                      <div className="text-center py-6 space-y-2">
                        <Eyebrow>Analyse</Eyebrow>
                        <p className="text-sm" style={{ color: "var(--color-muted)" }}>
                          Pas de setup conforme actuellement.
                        </p>
                        <p className="text-xs" style={{ color: "var(--color-faint)" }}>
                          {q.data.reasons[0]} — ne rien faire est une décision valable.
                        </p>
                      </div>
                    )}
                  </Bezel>
                </Reveal>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="w-3 h-0.5 rounded-full" style={{ backgroundColor: color }} /> {label}
    </span>
  );
}

function TfChip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className="press rounded-full px-3 py-1 text-xs font-medium transition-all duration-500"
      style={{
        backgroundColor: active ? "rgba(52,211,153,0.16)" : "transparent",
        color: active ? "#5be0ae" : "var(--color-muted)",
      }}
    >
      {children}
    </button>
  );
}

function Indicator({ label, value, tone }: { label: string; value: string; tone?: "up" | "down" }) {
  const color = tone === "up" ? "#5be0ae" : tone === "down" ? "#ff8497" : "var(--color-text)";
  return (
    <Bezel className="p-3">
      <div className="eyebrow">{label}</div>
      <div className="mt-1 text-sm font-semibold tabular-nums" style={{ color, fontFamily: "var(--font-display)" }}>
        {value}
      </div>
    </Bezel>
  );
}
