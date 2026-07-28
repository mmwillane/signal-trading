import { useState } from "react";
import { X, Wallet, ShieldCheck } from "@phosphor-icons/react";
import { saveUserSettings } from "../lib/userSettings";
import { money } from "../lib/format";

// Feuille de réglages : l'utilisateur saisit SON capital et SON risque par
// trade. Stocké localement (par navigateur), pris en compte par l'API pour
// dimensionner les positions. Aucune donnée sensible, aucun ordre.
export function SettingsSheet({
  currentCapital,
  currentRiskPct,
  currency = "USD",
  onClose,
}: {
  currentCapital: number;
  currentRiskPct: number; // en % (ex. 1)
  currency?: string;
  onClose: () => void;
}) {
  const [capital, setCapital] = useState(String(Math.round(currentCapital)));
  const [riskPct, setRiskPct] = useState(String(currentRiskPct));

  const capNum = parseFloat(capital);
  const riskNum = parseFloat(riskPct);
  const capValid = capNum > 0;
  const riskValid = riskNum > 0 && riskNum <= 10;
  const riskAmount = capValid && riskValid ? (capNum * riskNum) / 100 : 0;

  function save() {
    if (!capValid || !riskValid) return;
    saveUserSettings({ capital: capNum, risk: riskNum / 100 });
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
