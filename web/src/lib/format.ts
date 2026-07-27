// Utilitaires de formatage (affichage seulement).

export function money(v: number, currency = "USD"): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency,
    maximumFractionDigits: v >= 1000 ? 0 : 2,
  }).format(v);
}

export function num(v: number, digits = 2): string {
  return new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(v);
}

export function pct(v: number, withSign = true): string {
  const s = new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(v);
  return `${withSign && v > 0 ? "+" : ""}${s}%`;
}

export function signedR(v: number): string {
  return `${v > 0 ? "+" : ""}${num(v, 2)} R`;
}

export function sentimentLabel(v: number): { text: string; tone: Tone } {
  if (v >= 0.15) return { text: "Positif", tone: "up" };
  if (v <= -0.15) return { text: "Négatif", tone: "down" };
  return { text: "Neutre", tone: "flat" };
}

export type Tone = "up" | "down" | "flat";

export function toneColor(tone: Tone): string {
  return tone === "up"
    ? "var(--color-emerald)"
    : tone === "down"
      ? "var(--color-rose)"
      : "var(--color-amber)";
}

export function changeTone(v: number): Tone {
  return v > 0 ? "up" : v < 0 ? "down" : "flat";
}
