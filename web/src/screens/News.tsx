import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight } from "@phosphor-icons/react";
import { api } from "../api/client";
import { sentimentLabel } from "../lib/format";
import { Bezel, Pill, Eyebrow, SectionHeading } from "../components/ui";
import { Reveal } from "../components/Reveal";
import { CardSkeleton, ErrorState } from "../components/Skeleton";

const THEME_LABELS: Record<string, string> = {
  taux: "Taux",
  inflation: "Inflation",
  "banques centrales": "Banques centrales",
  "géopolitique": "Géopolitique",
};

export function News() {
  const q = useQuery({ queryKey: ["news"], queryFn: () => api.news() });

  return (
    <div className="space-y-7">
      <Reveal>
        <SectionHeading eyebrow="Marché & macro" title="Actualités" desc="Quelques sources financières solides, filtrées et notées en sentiment. Pas de ratissage massif." />
      </Reveal>

      {q.data && (
        <Reveal delay={60}>
          <Bezel className="p-5 flex items-center justify-between">
            <div>
              <div className="eyebrow">Sentiment global</div>
              <div className="mt-1 text-2xl font-semibold" style={{ fontFamily: "var(--font-display)" }}>
                {sentimentLabel(q.data.overall_sentiment).text}
              </div>
            </div>
            <Pill tone={sentimentLabel(q.data.overall_sentiment).tone} dot>
              {q.data.overall_sentiment >= 0 ? "+" : ""}{q.data.overall_sentiment.toFixed(2)}
            </Pill>
          </Bezel>
        </Reveal>
      )}

      {q.isLoading && <div className="space-y-3"><CardSkeleton /><CardSkeleton /></div>}
      {q.isError && <ErrorState message={(q.error as Error).message} />}

      {q.data && (
        <div className="space-y-3">
          <Eyebrow>{q.data.count} articles</Eyebrow>
          {q.data.items.map((n, i) => (
            <Reveal key={i} delay={Math.min(i * 40, 300)}>
              <a href={n.url ?? "#"} target="_blank" rel="noreferrer" className="block">
                <Bezel className="p-4 press">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 space-y-2">
                      <div className="text-[10px] uppercase tracking-wider" style={{ color: "var(--color-faint)" }}>{n.source}</div>
                      <div className="text-sm leading-snug">{n.title}</div>
                      {n.themes.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {n.themes.map((t) => (
                            <span key={t} className="rounded-full px-2 py-0.5 text-[10px] font-medium hairline" style={{ color: "var(--color-violet)" }}>
                              {THEME_LABELS[t] ?? t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <ArrowUpRight size={16} weight="light" color="#6b7280" className="shrink-0 mt-0.5" />
                  </div>
                </Bezel>
              </a>
            </Reveal>
          ))}
        </div>
      )}
    </div>
  );
}
