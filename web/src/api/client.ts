// Client API typé (lecture seule). Toutes les routes sont des GET ;
// il n'existe aucune fonction d'exécution d'ordre côté client.

export interface Proposal {
  symbol: string;
  direction: "buy" | "sell";
  entry: number;
  stop_loss: number;
  take_profit: number;
  stop_pct?: number;
  tp_pct?: number;
  stop_pips?: number | null;
  tp_pips?: number | null;
  risk_reward: number;
  quantity: number;
  is_forex?: boolean;
  lots?: number | null;   // volume MT5 (lots) pour le forex
  notional: number;
  risk_amount: number;
  reasons: string[];
  sentiment: number;
  confidence: number;
  adx: number;
  stop_basis: string;
  trailing_rule: string;
  currency?: string;   // devise des montants de compte (risque, exposition)
}

export interface DashboardItem {
  symbol: string;
  status: "ok" | "insufficient_data";
  message?: string;
  price?: number;
  change_pct?: number;
  is_live?: boolean;
  sentiment?: number;
  spark?: number[];
  has_setup?: boolean;
  direction?: "buy" | "sell" | null;
  confidence?: number;
  adx?: number;
  mtf?: string | null;
  reasons?: string[];
  proposal?: Proposal;
}

export interface Quote {
  price: number;
  change_pct: number;
  is_live: boolean;
}

export interface Dashboard {
  generated_for: string;
  currency: string;
  fx_rate: number;
  timeframe: string;
  capital: number;
  risk_per_trade?: number;
  risk_amount: number;
  n_setups: number;
  items: DashboardItem[];
}

export interface Principle {
  name: string;
  principle: string;
  rationale: string;
}

export interface Settings {
  capital: number;
  risk_per_trade: number;
  risk_amount: number;
  base_currency: string;
  watchlist: string[];
  asset_class: string;
  ai_enabled: boolean;
  principles: Principle[];
}

// Appréciation IA CONSULTATIVE. `available:false` = IA désactivée / indispo.
export interface AiAnalysis {
  available: boolean;
  reason?: string;
  demo?: boolean;   // true = exemple hors-ligne (gratuit), pas une vraie analyse IA
  model?: string;
  verdict?: "favorable" | "prudent" | "défavorable";
  conviction?: number;
  drivers?: string[];
  risks?: string[];
  news_read?: string;
  rationale?: string;
  caution?: string | null;
}

export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}
export interface LinePoint {
  time: string;
  value: number;
}

export interface NewsItem {
  source: string;
  title: string;
  summary: string;
  url: string | null;
  themes: string[];
}

export interface InstrumentDetail {
  symbol: string;
  status: string;
  price: number;
  change_pct: number;
  is_live: boolean;
  timeframe: string;
  currency: string;
  candles: Candle[];
  sma20: LinePoint[];
  sma50: LinePoint[];
  indicators: { rsi: number; macd_hist: number; atr: number; adx: number; sma_trend: number };
  sentiment: number;
  confidence: number;
  adx: number;
  mtf: string | null;
  has_setup: boolean;
  direction: "buy" | "sell" | null;
  reasons: string[];
  proposal?: Proposal;
  news: NewsItem[];
}

export interface NewsFeed {
  overall_sentiment: number;
  label: string;
  count: number;
  items: NewsItem[];
}

export interface BacktestResult {
  symbol: string;
  status: string;
  period: string;
  trailing: boolean;
  stats: {
    n_trades: number;
    win_rate: number;
    profit_factor: number | null;
    avg_rr: number;
    max_drawdown_r: number;
    total_r: number;
  };
  equity_curve: { i: number; r: number }[];
  trades: { direction: string; entry: number; exit: number; r: number; outcome: string }[];
}

export interface Portfolio {
  total_equity: number;
  available_brokers: string[];
  unavailable_brokers: string[];
  balances: { broker: string; currency: string; cash: number; equity: number }[];
  positions: { broker: string; symbol: string; quantity: number; unrealized_pnl: number }[];
  demo_mode: boolean;
}

export interface JournalTrade {
  id: string;
  symbol: string;
  direction: "buy" | "sell";
  entry: number;
  stop: number;
  take_profit: number;
  quantity: number;
  risk_amount: number;
  confidence: number;
  status: "open" | "closed";
  opened_at: string;
  exit_price: number | null;
  closed_at: string | null;
  r_multiple: number | null;
  notes: string;
  source: string;
}

export interface Expectancy {
  n_closed: number;
  n_open: number;
  win_rate: number;
  avg_win_r: number;
  avg_loss_r: number;
  expectancy_r: number;
  profit_factor: number | null;
  total_r: number;
  total_risk_amount: number;
}

export interface Journal {
  trades: JournalTrade[];
  expectancy: Expectancy;
}

export interface NewTrade {
  symbol: string;
  direction: "buy" | "sell";
  entry: number;
  stop: number;
  take_profit: number;
  quantity: number;
  confidence?: number;
  notes?: string;
  source?: string;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { Accept: "application/json" } });
  if (!res.ok) {
    let detail = `Erreur ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* réponse non-JSON : on garde le message générique */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

async function send<T>(path: string, method: "POST" | "PATCH" | "DELETE", body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `Erreur ${res.status}`;
    try {
      const b = await res.json();
      if (b?.detail) detail = b.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  settings: () => get<Settings>("/api/settings"),
  dashboard: (
    news = true,
    capital?: number | null,
    risk?: number | null,
    fractional = false,
    moreSignals = false,
    currency?: string,
    tf = "1d"
  ) => {
    const p = new URLSearchParams({ news: String(news), tf });
    if (capital != null) p.set("capital", String(capital));
    if (risk != null) p.set("risk", String(risk));
    if (fractional) p.set("fractional", "true");
    if (moreSignals) p.set("more_signals", "true");
    if (currency) p.set("currency", currency);
    return get<Dashboard>(`/api/dashboard?${p.toString()}`);
  },
  instrument: (
    symbol: string,
    news = true,
    tf = "1d",
    capital?: number | null,
    risk?: number | null,
    fractional = false,
    moreSignals = false,
    currency?: string
  ) => {
    const p = new URLSearchParams({ news: String(news), tf });
    if (capital != null) p.set("capital", String(capital));
    if (risk != null) p.set("risk", String(risk));
    if (fractional) p.set("fractional", "true");
    if (moreSignals) p.set("more_signals", "true");
    if (currency) p.set("currency", currency);
    return get<InstrumentDetail>(`/api/instrument/${encodeURIComponent(symbol)}?${p.toString()}`);
  },
  ai: (
    symbol: string,
    tf = "1d",
    capital?: number | null,
    risk?: number | null,
    fractional = false,
    moreSignals = false,
    currency?: string
  ) => {
    const p = new URLSearchParams({ tf });
    if (capital != null) p.set("capital", String(capital));
    if (risk != null) p.set("risk", String(risk));
    if (fractional) p.set("fractional", "true");
    if (moreSignals) p.set("more_signals", "true");
    if (currency) p.set("currency", currency);
    return get<AiAnalysis>(`/api/ai/${encodeURIComponent(symbol)}?${p.toString()}`);
  },
  news: () => get<NewsFeed>("/api/news"),
  backtest: (symbol: string, period = "2y", trailing = true) =>
    get<BacktestResult>(
      `/api/backtest/${encodeURIComponent(symbol)}?period=${period}&trailing=${trailing}`
    ),
  quotes: (symbols: string[]) =>
    get<{ quotes: Record<string, Quote> }>(`/api/quotes?symbols=${symbols.join(",")}`),
  portfolio: () => get<Portfolio>("/api/portfolio"),

  // Journal de trades (écritures locales — jamais un broker).
  journal: () => get<Journal>("/api/journal"),
  journalAdd: (trade: NewTrade) => send<JournalTrade>("/api/journal", "POST", trade),
  journalClose: (id: string, exit_price: number) =>
    send<JournalTrade>(`/api/journal/${id}/close`, "PATCH", { exit_price }),
  journalDelete: (id: string) => send<{ deleted: boolean }>(`/api/journal/${id}`, "DELETE"),
};
