// Utilitaires de formatage (affichage seulement).

// Correspondance symbole interne (Yahoo) -> nom affiché façon MetaTrader 5.
// L'app continue d'utiliser le symbole Yahoo pour les données ; seul
// l'affichage change, pour matcher ce que l'utilisateur voit sur MT5.
// NB : les noms des actions/indices peuvent varier légèrement selon le broker.
const MT5_NAMES: Record<string, string> = {
  "EURUSD=X": "EURUSD",
  "GBPUSD=X": "GBPUSD",
  "GC=F": "XAUUSD",
  "^GSPC": "US500",
  "^NDX": "USTEC",
  "BTC-USD": "BTCUSD",
  "ETH-USD": "ETHUSD",
  "XRP-USD": "XRPUSD",
  "SOL-USD": "SOLUSD",
  "BNB-USD": "BNBUSD",
  AAPL: "#AAPL",
  MSFT: "#MSFT",
  NVDA: "#NVDA",
  GOOGL: "#GOOGL",
  AMZN: "#AMZN",
  TSLA: "#TSLA",
  META: "#META",
};

export function mt5Name(symbol: string): string {
  return MT5_NAMES[symbol.toUpperCase()] ?? symbol;
}

export function money(v: number, currency = "USD"): string {
  try {
    return new Intl.NumberFormat("fr-FR", {
      style: "currency",
      currency,
      maximumFractionDigits: v >= 1000 ? 0 : 2,
    }).format(v);
  } catch {
    return `${num(v, 0)} ${currency}`;
  }
}

/** Montant compact pour les grands nombres (ex. 1,5 M $US) — évite les
 *  débordements dans les tuiles étroites. */
export function moneyCompact(v: number, currency = "USD"): string {
  try {
    if (Math.abs(v) >= 100_000) {
      return new Intl.NumberFormat("fr-FR", {
        style: "currency",
        currency,
        notation: "compact",
        maximumFractionDigits: 1,
      }).format(v);
    }
    return money(v, currency);
  } catch {
    return `${num(v, 0)} ${currency}`;
  }
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
