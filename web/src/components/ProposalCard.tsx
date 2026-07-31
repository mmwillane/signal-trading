import { TrendUp, TrendDown, Warning, Target, Shield, Pulse, ArrowsClockwise, Info } from "@phosphor-icons/react";
import type { Proposal } from "../api/client";
import { money, num, mt5Name } from "../lib/format";
import { Pill, ConfidenceBar } from "./ui";
import { JournalButton } from "./JournalButton";

/** Distance stop/TP à appliquer depuis le prix d'entrée réel du broker. */
function distLabel(pct?: number, pips?: number | null): string {
  const parts: string[] = [];
  if (pct != null) parts.push(`${num(pct, 2)}%`);
  if (pips != null) parts.push(`${pips} pips`);
  return parts.length ? parts.join(" · ") : "—";
}

// Affiche une proposition d'ordre complète. Toujours accompagnée de
// l'avertissement : à valider et exécuter MANUELLEMENT.
export function ProposalCard({ p, currency = "USD" }: { p: Proposal; currency?: string }) {
  const buy = p.direction === "buy";
  const Icon = buy ? TrendUp : TrendDown;
  const priceDec = p.is_forex ? 5 : 2;  // le forex a besoin de plus de décimales

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ backgroundColor: buy ? "rgba(52,211,153,0.12)" : "rgba(251,90,114,0.12)" }}
          >
            <Icon size={20} weight="light" color={buy ? "#34d399" : "#fb5a72"} />
          </div>
          <div>
            <div className="text-lg font-semibold" style={{ fontFamily: "var(--font-display)" }}>
              {mt5Name(p.symbol)}
            </div>
            <Pill tone={buy ? "buy" : "sell"} dot>
              {buy ? "Buy" : "Sell"}
            </Pill>
          </div>
        </div>
        <div className="text-right">
          <div className="eyebrow">Ratio R/R</div>
          <div className="text-2xl font-semibold" style={{ fontFamily: "var(--font-display)", color: "var(--color-emerald)" }}>
            {num(p.risk_reward, 2)}
          </div>
        </div>
      </div>

      {/* Confiance + force de tendance */}
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <ConfidenceBar score={p.confidence} />
        </div>
        <div className="flex items-center gap-1.5 rounded-full px-2.5 py-1 hairline shrink-0" style={{ color: "var(--color-muted)" }}>
          <Pulse size={13} weight="light" color="#8b7cf6" />
          <span className="text-[11px] font-semibold tabular-nums">ADX {num(p.adx, 0)}</span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <Level label="Entrée ~" value={num(p.entry, priceDec)} sub="au marché" />
        <Level
          label="Stop Loss"
          value={num(p.stop_loss, priceDec)}
          sub={distLabel(p.stop_pct, p.stop_pips)}
          tone="down"
          icon={<Shield size={13} weight="light" />}
        />
        <Level
          label="Take Profit"
          value={num(p.take_profit, priceDec)}
          sub={distLabel(p.tp_pct, p.tp_pips)}
          tone="up"
          icon={<Target size={13} weight="light" />}
        />
      </div>

      {/* Prix indicatifs -> entrer au marché + appliquer les distances */}
      <div
        className="flex items-start gap-2 rounded-2xl p-3 text-[12px] leading-relaxed"
        style={{ backgroundColor: "rgba(52,211,153,0.06)", color: "#9fe6c8" }}
      >
        <Info size={15} weight="light" className="shrink-0 mt-0.5" />
        <span>
          Prix <strong>indicatifs</strong> (données différées, différentes de ton broker). Entre <strong>au marché</strong> sur ta plateforme, puis place le stop à <strong>{distLabel(p.stop_pct, p.stop_pips)}</strong> et le take profit à <strong>{distLabel(p.tp_pct, p.tp_pips)}</strong> de ton prix d'entrée réel.
        </span>
      </div>

      <div className="flex items-center gap-1.5 text-[11px]" style={{ color: "var(--color-faint)" }}>
        <Shield size={12} weight="light" /> Stop {p.stop_basis}
      </div>

      <div className="grid grid-cols-2 gap-2">
        {p.is_forex && p.lots != null ? (
          <Level label="Volume (lots)" value={num(Math.max(p.lots, 0.01), 2)} sub={`expo ${money(p.notional, currency)}`} />
        ) : (
          <Level label="Volume" value={num(p.quantity, p.quantity < 1 ? 6 : 2)} sub={`expo ${money(p.notional, currency)}`} />
        )}
        <Level label="Risque" value={money(p.risk_amount, currency)} sub="si stop touché" tone="down" />
      </div>

      {p.reasons.length > 0 && (
        <ul className="space-y-1.5 pt-1">
          {p.reasons.map((r, i) => (
            <li key={i} className="flex items-start gap-2 text-[13px]" style={{ color: "var(--color-muted)" }}>
              <span className="mt-1.5 w-1 h-1 rounded-full shrink-0" style={{ backgroundColor: "var(--color-emerald)" }} />
              {r}
            </li>
          ))}
        </ul>
      )}

      {p.trailing_rule && (
        <div
          className="flex items-start gap-2 rounded-2xl p-3 text-[12px] leading-relaxed"
          style={{ backgroundColor: "rgba(139,124,246,0.07)", color: "#b3a9f7" }}
        >
          <ArrowsClockwise size={15} weight="light" className="shrink-0 mt-0.5" />
          <span><strong>Stop suiveur</strong> : {p.trailing_rule}</span>
        </div>
      )}

      <JournalButton p={p} />

      <div
        className="flex items-start gap-2 rounded-2xl p-3 text-[12px] leading-relaxed"
        style={{ backgroundColor: "rgba(245,196,81,0.07)", color: "#e9c877" }}
      >
        <Warning size={16} weight="light" className="shrink-0 mt-0.5" />
        <span>
          Proposition à <strong>valider et exécuter manuellement</strong>. Aucune garantie de résultat — ceci n'est pas un conseil en investissement.
        </span>
      </div>
    </div>
  );
}

function Level({
  label,
  value,
  sub,
  tone,
  icon,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "up" | "down";
  icon?: React.ReactNode;
}) {
  const color = tone === "up" ? "#5be0ae" : tone === "down" ? "#ff8497" : "var(--color-text)";
  return (
    <div className="rounded-2xl p-3 hairline" style={{ backgroundColor: "rgba(255,255,255,0.02)" }}>
      <div className="eyebrow flex items-center gap-1">
        {icon}
        {label}
      </div>
      <div className="mt-1 text-[15px] font-semibold tabular-nums" style={{ color, fontFamily: "var(--font-display)" }}>
        {value}
      </div>
      {sub && <div className="text-[10px] mt-0.5" style={{ color: "var(--color-faint)" }}>{sub}</div>}
    </div>
  );
}
