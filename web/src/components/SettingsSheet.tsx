import { useState } from "react";
import { X, Wallet, ShieldCheck, CurrencyCircleDollar } from "@phosphor-icons/react";
import { saveUserSettings } from "../lib/userSettings";
import { money } from "../lib/format";

const CURRENCIES = [
  { code: "USD", label: "Dollar US" },
  { code: "EUR", label: "Euro" },
  { code: "GBP", label: "Livre sterling" },
  { code: "XOF", label: "Franc CFA (Ouest)" },
  { code: "XAF", label: "Franc CFA (Centre)" },
  { code: "NGN", label: "Naira (Nigeria)" },
  { code: "GHS", label: "Cedi (Ghana)" },
  { code: "KES", label: "Shilling (Kenya)" },
  { code: "ZAR", label: "Rand (Afrique du Sud)" },
  { code: "MAD", label: "Dirham (Maroc)" },
];

// Feuille de réglages : l'utilisateur saisit SON capital et SON risque par
// trade. Stocké localement (par navigateur), pris en compte par l'API pour
// dimensionner les positions. Aucune donnée sensible, aucun ordre.
export function SettingsSheet({
  currentCapital,
  currentRiskPct,
  currentFractional = false,
  currentMoreSignals = false,
  currency: currentCurrency = "USD",
  onClose,
}: {
  currentCapital: number;
  currentRiskPct: number; // en % (ex. 1)
  currentFractional?: boolean;
  currentMoreSignals?: boolean;
  currency?: string;
  onClose: () => void;
}) {
  const [capital, setCapital] = useState(String(Math.round(currentCapital)));
  const [riskPct, setRiskPct] = useState(String(currentRiskPct));
  const [fractional, setFractional] = useState(currentFractional);
  const [moreSignals, setMoreSignals] = useState(currentMoreSignals);
  const [currency, setCurrency] = useState(currentCurrency);

  const capNum = parseFloat(capital);
  const riskNum = parseFloat(riskPct);
  const capValid = capNum > 0;
  const riskValid = riskNum > 0 && riskNum <= 10;
  const riskAmount = capValid && riskValid ? (capNum * riskNum) / 100 : 0;
  const smallBudget = capValid && capNum <= 300;

  function save() {
    if (!capValid || !riskValid) return;
    saveUserSettings({ capital: capNum, risk: riskNum / 100, fractional, moreSignals, currency });
    onClose();
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-end sm:items-center justify-center p-4"
      style={{ background: "rgba(3,3,5,0.7)", backdropFilter: "blur(6px)" }}
      onClick={onClose}
    >
      <div
        className="bezel w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
        style={{ animation: "none" }}
      >
        <div className="bezel-core p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="eyebrow">Tes réglages</div>
              <h2 className="text-2xl font-semibold tracking-tight mt-1" style={{ fontFamily: "var(--font-display)" }}>
                Capital & risque
              </h2>
            </div>
            <button onClick={onClose} className="press rounded-full p-2 hairline" aria-label="Fermer">
              <X size={18} weight="light" color="#9aa0ac" />
            </button>
          </div>

          <label className="block">
            <span className="eyebrow flex items-center gap-1.5">
              <CurrencyCircleDollar size={16} weight="light" color="#8b7cf6" /> Devise
            </span>
            <div className="mt-2 rounded-2xl px-4 py-3 hairline" style={{ backgroundColor: "rgba(255,255,255,0.02)" }}>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full bg-transparent outline-none text-sm"
                style={{ color: "var(--color-text)" }}
              >
                {CURRENCIES.map((c) => (
                  <option key={c.code} value={c.code} style={{ backgroundColor: "#101218" }}>
                    {c.code} — {c.label}
                  </option>
                ))}
              </select>
            </div>
          </label>

          <Field
            icon={<Wallet size={16} weight="light" color="#34d399" />}
            label="Ton capital"
            suffix={currency}
            value={capital}
            onChange={setCapital}
            invalid={!capValid && capital !== ""}
          />

          <Field
            icon={<ShieldCheck size={16} weight="light" color="#f5c451" />}
            label="Risque par trade"
            suffix="%"
            value={riskPct}
            onChange={setRiskPct}
            invalid={!riskValid && riskPct !== ""}
            hint="Fraction du capital risquée sur un trade (max 10 %)."
          />

          <div className="rounded-2xl p-4 hairline" style={{ backgroundColor: "rgba(52,211,153,0.05)" }}>
            <div className="flex items-center justify-between">
              <span className="text-sm" style={{ color: "var(--color-muted)" }}>Risque max par trade</span>
              <span className="text-lg font-semibold tabular-nums" style={{ fontFamily: "var(--font-display)", color: "#5be0ae" }}>
                {riskAmount > 0 ? money(riskAmount, currency) : "—"}
              </span>
            </div>
          </div>

          {/* Actions fractionnées — clé pour les petits budgets */}
          <button
            onClick={() => setFractional((v) => !v)}
            className="press w-full rounded-2xl p-4 hairline text-left"
            style={{ backgroundColor: fractional ? "rgba(139,124,246,0.08)" : "rgba(255,255,255,0.02)" }}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="text-sm font-medium">Actions fractionnées</div>
                <div className="text-[11px] mt-0.5" style={{ color: "var(--color-faint)" }}>
                  Pour les petits budgets : acheter une fraction d'action (ex. 0,08 AAPL). Active-le si ton broker le permet.
                </div>
              </div>
              <span
                className="shrink-0 w-11 h-6 rounded-full p-0.5 transition-all duration-300"
                style={{ backgroundColor: fractional ? "var(--color-violet)" : "rgba(255,255,255,0.12)" }}
              >
                <span
                  className="block w-5 h-5 rounded-full bg-white transition-all duration-300"
                  style={{ transform: fractional ? "translateX(20px)" : "translateX(0)" }}
                />
              </span>
            </div>
          </button>

          {smallBudget && !fractional && (
            <p className="text-[11px] leading-relaxed rounded-xl p-2.5" style={{ backgroundColor: "rgba(245,196,81,0.08)", color: "#e9c877" }}>
              💡 Avec un budget ≤ 300, la plupart des actions coûtent plus qu'une part entière. Active « actions fractionnées » pour obtenir des propositions adaptées.
            </p>
          )}

          {/* Mode « plus de signaux » — seuils assouplis */}
          <button
            onClick={() => setMoreSignals((v) => !v)}
            className="press w-full rounded-2xl p-4 hairline text-left"
            style={{ backgroundColor: moreSignals ? "rgba(245,196,81,0.08)" : "rgba(255,255,255,0.02)" }}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="text-sm font-medium">Plus de signaux</div>
                <div className="text-[11px] mt-0.5" style={{ color: "var(--color-faint)" }}>
                  Assouplit les filtres (ADX, confluence, confiance) → plus d'opportunités, mais <strong style={{ color: "#e9c877" }}>moins fiables</strong>. Utile pour apprendre en démo.
                </div>
              </div>
              <span
                className="shrink-0 w-11 h-6 rounded-full p-0.5 transition-all duration-300"
                style={{ backgroundColor: moreSignals ? "var(--color-amber)" : "rgba(255,255,255,0.12)" }}
              >
                <span
                  className="block w-5 h-5 rounded-full bg-white transition-all duration-300"
                  style={{ transform: moreSignals ? "translateX(20px)" : "translateX(0)" }}
                />
              </span>
            </div>
          </button>

          <button
            onClick={save}
            disabled={!capValid || !riskValid}
            className="press w-full rounded-full py-3.5 text-sm font-semibold"
            style={{
              backgroundColor: capValid && riskValid ? "var(--color-emerald)" : "rgba(255,255,255,0.06)",
              color: capValid && riskValid ? "#04140d" : "var(--color-faint)",
            }}
          >
            Enregistrer
          </button>

          <p className="text-[11px] text-center leading-relaxed" style={{ color: "var(--color-faint)" }}>
            Enregistré sur cet appareil uniquement. L'app dimensionne les positions à partir de ces valeurs — elle n'exécute rien.
          </p>
        </div>
      </div>
    </div>
  );
}

function Field({
  icon,
  label,
  suffix,
  value,
  onChange,
  invalid,
  hint,
}: {
  icon: React.ReactNode;
  label: string;
  suffix: string;
  value: string;
  onChange: (v: string) => void;
  invalid?: boolean;
  hint?: string;
}) {
  return (
    <label className="block">
      <span className="eyebrow flex items-center gap-1.5">{icon} {label}</span>
      <div
        className="mt-2 flex items-center gap-2 rounded-2xl px-4 py-3 hairline"
        style={{ backgroundColor: "rgba(255,255,255,0.02)", borderColor: invalid ? "var(--color-rose)" : undefined }}
      >
        <input
          type="number"
          inputMode="decimal"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 bg-transparent outline-none text-lg tabular-nums"
          style={{ color: "var(--color-text)", fontFamily: "var(--font-display)" }}
        />
        <span className="text-sm" style={{ color: "var(--color-faint)" }}>{suffix}</span>
      </div>
      {hint && <span className="text-[11px] mt-1 block" style={{ color: "var(--color-faint)" }}>{hint}</span>}
    </label>
  );
}
