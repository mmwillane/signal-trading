import { useQuery } from "@tanstack/react-query";
import { Plugs, ShieldCheck, LockKey } from "@phosphor-icons/react";
import { api } from "../api/client";
import { money } from "../lib/format";
import { Bezel, Eyebrow, SectionHeading } from "../components/ui";
import { Reveal } from "../components/Reveal";
import { Skeleton, ErrorState } from "../components/Skeleton";

export function Portfolio() {
  const q = useQuery({ queryKey: ["portfolio"], queryFn: () => api.portfolio() });

  return (
    <div className="space-y-7">
      <Reveal>
        <SectionHeading eyebrow="Lecture seule" title="Comptes" desc="Vue consolidée de tes brokers connectés — en lecture seule. Aucune connexion ne peut passer d'ordre." />
      </Reveal>

      {q.isLoading && <Skeleton className="h-40 w-full" />}
      {q.isError && <ErrorState message={(q.error as Error).message} />}

      {q.data && (
        <>
          {q.data.demo_mode ? (
            <Reveal delay={60}>
              <Bezel className="p-6 text-center space-y-4">
                <div className="w-14 h-14 rounded-2xl mx-auto flex items-center justify-center" style={{ backgroundColor: "rgba(52,211,153,0.1)" }}>
                  <LockKey size={26} weight="light" color="#34d399" />
                </div>
                <div className="space-y-1.5">
                  <div className="text-lg font-semibold" style={{ fontFamily: "var(--font-display)" }}>Mode démo</div>
                  <p className="text-sm max-w-xs mx-auto" style={{ color: "var(--color-muted)" }}>
                    Aucun compte broker connecté. Ajoute des clés API <strong style={{ color: "var(--color-text)" }}>en lecture seule</strong> dans le fichier <code>.env</code> pour voir ton portefeuille ici.
                  </p>
                </div>
              </Bezel>
            </Reveal>
          ) : (
            <>
              <Reveal delay={60}>
                <Bezel className="p-6">
                  <div className="eyebrow">Équité totale consolidée</div>
                  <div className="mt-1 text-4xl font-semibold tabular-nums" style={{ fontFamily: "var(--font-display)" }}>
                    {money(q.data.total_equity)}
                  </div>
                </Bezel>
              </Reveal>
              {q.data.balances.map((b, i) => (
                <Reveal key={b.broker} delay={80 + i * 40}>
                  <Bezel className="p-4 flex items-center justify-between">
                    <span className="font-medium">{b.broker}</span>
                    <span className="tabular-nums" style={{ color: "var(--color-muted)" }}>{money(b.equity, b.currency)}</span>
                  </Bezel>
                </Reveal>
              ))}
            </>
          )}

          {/* État des connecteurs */}
          <Reveal delay={120}>
            <div className="space-y-3">
              <Eyebrow>Connecteurs disponibles</Eyebrow>
              <div className="grid grid-cols-1 gap-2">
                {[...q.data.available_brokers.map((b) => ({ b, on: true })), ...q.data.unavailable_brokers.map((b) => ({ b, on: false }))].map(({ b, on }) => (
                  <Bezel key={b} className="p-3.5 flex items-center gap-3">
                    <Plugs size={18} weight="light" color={on ? "#34d399" : "#6b7280"} />
                    <span className="flex-1 text-sm" style={{ color: on ? "var(--color-text)" : "var(--color-muted)" }}>{b}</span>
                    <span className="text-[11px] rounded-full px-2 py-0.5" style={{ backgroundColor: on ? "rgba(52,211,153,0.12)" : "rgba(255,255,255,0.04)", color: on ? "#5be0ae" : "var(--color-faint)" }}>
                      {on ? "connecté" : "non connecté"}
                    </span>
                  </Bezel>
                ))}
              </div>
            </div>
          </Reveal>

          <Reveal delay={160}>
            <div className="flex items-start gap-3 rounded-2xl p-4 hairline" style={{ backgroundColor: "rgba(52,211,153,0.04)" }}>
              <ShieldCheck size={22} weight="light" color="#34d399" className="shrink-0" />
              <p className="text-[12px] leading-relaxed" style={{ color: "var(--color-muted)" }}>
                Les connecteurs n'exposent que des méthodes de <strong style={{ color: "var(--color-text)" }}>lecture</strong> (solde, positions, historique). Il est structurellement impossible de passer, modifier ou annuler un ordre.
              </p>
            </div>
          </Reveal>
        </>
      )}
    </div>
  );
}
