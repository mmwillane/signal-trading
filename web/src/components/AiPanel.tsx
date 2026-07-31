import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sparkle, Warning, ShieldWarning, TrendUp, ArrowClockwise } from "@phosphor-icons/react";
import { api } from "../api/client";
import { Bezel, Eyebrow, Pill } from "./ui";

/** Panneau analyste IA CONSULTATIF, à la demande (pas d'appel automatique :
 *  l'utilisateur clique pour lancer l'analyse, ce qui évite de facturer
 *  l'API à chaque chargement de page). Se cache si l'IA est désactivée. */
export function AiPanel({
  symbol,
  tf,
  capital,
  risk,
  fractional,
  moreSignals,
  currency,
}: {
  symbol: string;
  tf: string;
  capital?: number | null;
  risk?: number | null;
  fractional?: boolean;
  moreSignals?: boolean;
  currency?: string;
}) {
  const [run, setRun] = useState(false);

  const q = useQuery({
    queryKey: ["ai", symbol, tf, capital, risk, fractional, moreSignals, currency],
    queryFn: () => api.ai(symbol, tf, capital, risk, fractional, moreSignals, currency),
    enabled: run,
    staleTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const a = q.data;

  return (
    <Bezel className="p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center"
            style={{ backgroundColor: "rgba(139,124,246,0.14)" }}
          >
            <Sparkle size={16} weight="fill" color="#8b7cf6" />
          </div>
          <div>
            <div className="text-sm font-semibold" style={{ fontFamily: "var(--font-display)" }}>
              Analyse IA
            </div>
            <div className="text-[10px]" style={{ color: "var(--color-faint)" }}>
              Second regard · Claude
            </div>
          </div>
        </div>
        {a?.available && a.demo ? (
          <span
            className="text-[10px] font-semibold rounded-full px-2 py-0.5"
            style={{ backgroundColor: "rgba(245,196,81,0.14)", color: "#e9c877" }}
          >
            Démo
          </span>
        ) : a?.model ? (
          <span className="text-[10px] rounded-full px-2 py-0.5 hairline" style={{ color: "var(--color-faint)" }}>
            {a.model}
          </span>
        ) : null}
      </div>

      {/* État initial : bouton pour lancer (à la demande) */}
      {!run && (
        <>
          <p className="text-[13px] leading-relaxed" style={{ color: "var(--color-muted)" }}>
            Fais lire le setup et les actualités par un analyste IA : conviction,
            facteurs clés et risques, en complément du score technique.
          </p>
          <button
            onClick={() => setRun(true)}
            className="press w-full rounded-full py-2.5 text-sm font-semibold"
            style={{ backgroundColor: "rgba(139,124,246,0.16)", color: "#b3a9f7" }}
          >
            Lancer l'analyse IA
          </button>
        </>
      )}

      {run && q.isLoading && (
        <div className="flex items-center gap-2 py-3 text-sm" style={{ color: "var(--color-muted)" }}>
          <ArrowClockwise size={16} weight="light" className="ai-spin" />
          L'analyste lit le marché et les actualités…
        </div>
      )}

      {run && q.isError && (
        <p className="text-sm" style={{ color: "#ff8497" }}>
          Analyse indisponible pour le moment.
        </p>
      )}

      {a && !a.available && (
        <div className="space-y-2">
          <p className="text-[13px]" style={{ color: "var(--color-muted)" }}>
            {a.reason === "insufficient_data"
              ? "Données insuffisantes pour une analyse fiable sur cet instrument."
              : "L'analyste IA n'est pas configuré sur ce déploiement."}
          </p>
          {a.reason !== "insufficient_data" && (
            <p className="text-[11px]" style={{ color: "var(--color-faint)" }}>
              Ajoute une clé <code>ANTHROPIC_API_KEY</code> dans la configuration pour l'activer.
            </p>
          )}
        </div>
      )}

      {a && a.available && (
        <div className="space-y-4">
          {a.demo && (
            <div
              className="rounded-2xl p-3 text-[11px] leading-relaxed"
              style={{ backgroundColor: "rgba(245,196,81,0.08)", color: "#e9c877" }}
            >
              <strong>Exemple (mode démo)</strong> — généré hors-ligne à partir du setup,
              sans appel payant. Ce n'est pas une vraie analyse Claude. Ajoute une clé{" "}
              <code>ANTHROPIC_API_KEY</code> pour l'analyse réelle.
            </div>
          )}
          {/* Verdict + conviction */}
          <div className="flex items-center justify-between">
            <VerdictPill verdict={a.verdict} />
            {typeof a.conviction === "number" && (
              <div className="text-right">
                <div className="eyebrow">Conviction</div>
                <div
                  className="text-xl font-semibold tabular-nums"
                  style={{ fontFamily: "var(--font-display)", color: convictionColor(a.conviction) }}
                >
                  {a.conviction}/100
                </div>
              </div>
            )}
          </div>

          {a.rationale && (
            <p className="text-[13px] leading-relaxed" style={{ color: "var(--color-text)" }}>
              {a.rationale}
            </p>
          )}

          {a.news_read && (
            <div className="rounded-2xl p-3 text-[12px] leading-relaxed" style={{ backgroundColor: "rgba(255,255,255,0.02)", color: "var(--color-muted)" }}>
              <span className="eyebrow block mb-1">Lecture des actus</span>
              {a.news_read}
            </div>
          )}

          {a.drivers && a.drivers.length > 0 && (
            <FactorList title="Facteurs favorables" items={a.drivers} tone="up" />
          )}
          {a.risks && a.risks.length > 0 && (
            <FactorList title="Risques à surveiller" items={a.risks} tone="down" />
          )}

          {a.caution && (
            <div
              className="flex items-start gap-2 rounded-2xl p-3 text-[12px] leading-relaxed"
              style={{ backgroundColor: "rgba(245,196,81,0.08)", color: "#e9c877" }}
            >
              <ShieldWarning size={15} weight="light" className="shrink-0 mt-0.5" />
              <span>{a.caution}</span>
            </div>
          )}

          <button
            onClick={() => q.refetch()}
            disabled={q.isFetching}
            className="press inline-flex items-center gap-1.5 text-[11px] rounded-full px-3 py-1.5 hairline"
            style={{ color: "var(--color-muted)" }}
          >
            <ArrowClockwise size={12} weight="light" className={q.isFetching ? "ai-spin" : ""} />
            Réanalyser
          </button>
        </div>
      )}

      {/* Avertissement permanent */}
      <div
        className="flex items-start gap-2 rounded-2xl p-3 text-[11px] leading-relaxed"
        style={{ backgroundColor: "rgba(139,124,246,0.06)", color: "#b3a9f7" }}
      >
        <Warning size={14} weight="light" className="shrink-0 mt-0.5" />
        <span>
          Avis IA <strong>consultatif</strong> : n'exécute rien, ne prédit pas le marché et
          ne remplace pas ton jugement. Ce n'est pas un conseil en investissement.
        </span>
      </div>
    </Bezel>
  );
}

function VerdictPill({ verdict }: { verdict?: string }) {
  if (!verdict) return null;
  const tone = verdict === "favorable" ? "buy" : verdict === "défavorable" ? "sell" : "flat";
  return (
    <Pill tone={tone} dot>
      <TrendUp size={12} weight="bold" style={{ display: verdict === "favorable" ? "inline" : "none" }} />
      {verdict.charAt(0).toUpperCase() + verdict.slice(1)}
    </Pill>
  );
}

function FactorList({ title, items, tone }: { title: string; items: string[]; tone: "up" | "down" }) {
  const dot = tone === "up" ? "var(--color-emerald)" : "var(--color-rose)";
  return (
    <div className="space-y-1.5">
      <Eyebrow>{title}</Eyebrow>
      <ul className="space-y-1.5">
        {items.map((it, i) => (
          <li key={i} className="flex items-start gap-2 text-[13px]" style={{ color: "var(--color-muted)" }}>
            <span className="mt-1.5 w-1 h-1 rounded-full shrink-0" style={{ backgroundColor: dot }} />
            {it}
          </li>
        ))}
      </ul>
    </div>
  );
}

function convictionColor(score: number): string {
  if (score >= 75) return "#34d399";
  if (score >= 60) return "#8bd47f";
  if (score >= 45) return "#f5c451";
  return "#fb5a72";
}
