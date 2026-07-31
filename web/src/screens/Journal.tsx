import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Notebook, TrendUp, TrendDown, Check, Trash, X } from "@phosphor-icons/react";
import { api, type JournalTrade } from "../api/client";
import { num, pct, signedR } from "../lib/format";
import { Bezel, Eyebrow, Pill, SectionHeading } from "../components/ui";
import { Reveal } from "../components/Reveal";
import { Skeleton, ErrorState } from "../components/Skeleton";

export function Journal() {
  const q = useQuery({ queryKey: ["journal"], queryFn: () => api.journal() });

  const open = q.data?.trades.filter((t) => t.status === "open") ?? [];
  const closed = q.data?.trades.filter((t) => t.status === "closed") ?? [];
  const e = q.data?.expectancy;
  const hasData = (q.data?.trades.length ?? 0) > 0;

  return (
    <div className="space-y-7">
      <Reveal>
        <SectionHeading
          eyebrow="Ton edge réel"
          title="Journal"
          desc="Enregistre les trades que tu exécutes toi-même. L'app mesure ton espérance réelle dans le temps — l'habitude n°1 des traders sérieux."
        />
      </Reveal>

      {q.isLoading && <Skeleton className="h-40 w-full" />}
      {q.isError && <ErrorState message={(q.error as Error).message} />}

      {q.data && !hasData && (
        <Reveal delay={60}>
          <Bezel className="p-6 text-center space-y-4">
            <div className="w-14 h-14 rounded-2xl mx-auto flex items-center justify-center" style={{ backgroundColor: "rgba(52,211,153,0.1)" }}>
              <Notebook size={26} weight="light" color="#34d399" />
            </div>
            <div className="space-y-1.5">
              <div className="text-lg font-semibold" style={{ fontFamily: "var(--font-display)" }}>Journal vide</div>
              <p className="text-sm max-w-xs mx-auto" style={{ color: "var(--color-muted)" }}>
                Depuis une proposition (onglet Signaux → un instrument), touche <strong style={{ color: "var(--color-text)" }}>« Journaliser ce trade »</strong> quand tu prends une position. Elle apparaîtra ici.
              </p>
            </div>
          </Bezel>
        </Reveal>
      )}

      {e && hasData && (
        <Reveal delay={60}>
          <Bezel className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="eyebrow">Espérance par trade</div>
                <div
                  className="mt-1 text-4xl font-semibold tabular-nums"
                  style={{ fontFamily: "var(--font-display)", color: e.expectancy_r >= 0 ? "#34d399" : "#fb5a72" }}
                >
                  {signedR(e.expectancy_r)}
                </div>
                <div className="text-[11px] mt-1" style={{ color: "var(--color-faint)" }}>
                  gain moyen attendu par trade ({e.n_closed} clôturés)
                </div>
              </div>
              <Pill tone={e.expectancy_r >= 0 ? "up" : "down"} dot>
                {e.expectancy_r >= 0 ? "Positive" : "Négative"}
              </Pill>
            </div>
          </Bezel>
        </Reveal>
      )}

      {e && e.n_closed > 0 && (
        <Reveal delay={90}>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
            <Stat label="Win rate" value={pct(e.win_rate * 100, false)} tone={e.win_rate >= 0.5 ? "up" : undefined} />
            <Stat label="Profit factor" value={e.profit_factor === null ? "∞" : num(e.profit_factor, 2)} tone={(e.profit_factor ?? 99) >= 1 ? "up" : "down"} />
            <Stat label="Gain moyen" value={signedR(e.avg_win_r)} tone="up" />
            <Stat label="Perte moyenne" value={signedR(e.avg_loss_r)} tone="down" />
            <Stat label="Résultat total" value={signedR(e.total_r)} tone={e.total_r >= 0 ? "up" : "down"} />
            <Stat label="En cours" value={String(e.n_open)} />
          </div>
        </Reveal>
      )}

      {open.length > 0 && (
        <Reveal delay={110}>
          <div className="space-y-3">
            <Eyebrow>Positions ouvertes ({open.length})</Eyebrow>
            <div className="grid gap-3 md:grid-cols-2">
              {open.map((t) => <OpenRow key={t.id} t={t} />)}
            </div>
          </div>
        </Reveal>
      )}

      {closed.length > 0 && (
        <Reveal delay={130}>
          <div className="space-y-3">
            <Eyebrow>Historique ({closed.length})</Eyebrow>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {closed.map((t) => <ClosedRow key={t.id} t={t} />)}
            </div>
          </div>
        </Reveal>
      )}
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "up" | "down" }) {
  const color = tone === "up" ? "#5be0ae" : tone === "down" ? "#ff8497" : "var(--color-text)";
  return (
    <Bezel className="p-4">
      <div className="eyebrow">{label}</div>
      <div className="mt-1.5 text-xl font-semibold tabular-nums" style={{ color, fontFamily: "var(--font-display)" }}>
        {value}
      </div>
    </Bezel>
  );
}

function Head({ t }: { t: JournalTrade }) {
  const buy = t.direction === "buy";
  const Icon = buy ? TrendUp : TrendDown;
  return (
    <div className="flex items-center gap-2.5">
      <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ backgroundColor: buy ? "rgba(52,211,153,0.12)" : "rgba(251,90,114,0.12)" }}>
        <Icon size={16} weight="light" color={buy ? "#34d399" : "#fb5a72"} />
      </div>
      <div>
        <div className="font-semibold" style={{ fontFamily: "var(--font-display)" }}>{t.symbol}</div>
        <div className="text-[10px]" style={{ color: "var(--color-faint)" }}>{t.opened_at} · {buy ? "Buy" : "Sell"}</div>
      </div>
    </div>
  );
}

function OpenRow({ t }: { t: JournalTrade }) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [exit, setExit] = useState(String(t.take_profit || t.entry));

  const closeMut = useMutation({
    mutationFn: () => api.journalClose(t.id, parseFloat(exit)),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["journal"] }),
  });
  const delMut = useMutation({
    mutationFn: () => api.journalDelete(t.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["journal"] }),
  });

  return (
    <Bezel className="p-4">
      <div className="flex items-center justify-between">
        <Head t={t} />
        <div className="text-right">
          <div className="text-[10px] eyebrow">Entrée · Stop · TP</div>
          <div className="text-xs tabular-nums" style={{ color: "var(--color-muted)" }}>
            {num(t.entry, 2)} · {num(t.stop, 2)} · {num(t.take_profit, 2)}
          </div>
        </div>
      </div>

      {!editing ? (
        <div className="mt-3 flex gap-2">
          <button
            onClick={() => setEditing(true)}
            className="press flex-1 rounded-full py-2 text-xs font-semibold"
            style={{ backgroundColor: "rgba(52,211,153,0.12)", color: "#5be0ae" }}
          >
            Clôturer
          </button>
          <button
            onClick={() => delMut.mutate()}
            className="press rounded-full px-3 py-2"
            style={{ backgroundColor: "rgba(255,255,255,0.04)" }}
            aria-label="Supprimer"
          >
            <Trash size={15} weight="light" color="#6b7280" />
          </button>
        </div>
      ) : (
        <div className="mt-3 flex items-center gap-2">
          <input
            type="number"
            inputMode="decimal"
            value={exit}
            onChange={(e) => setExit(e.target.value)}
            placeholder="Prix de sortie"
            className="flex-1 rounded-full px-3 py-2 text-sm tabular-nums bg-transparent hairline outline-none"
            style={{ color: "var(--color-text)" }}
          />
          <button
            onClick={() => closeMut.mutate()}
            disabled={closeMut.isPending}
            className="press rounded-full px-3 py-2"
            style={{ backgroundColor: "var(--color-emerald)", color: "#04140d" }}
            aria-label="Valider la clôture"
          >
            <Check size={16} weight="bold" />
          </button>
          <button onClick={() => setEditing(false)} className="press rounded-full px-2 py-2" aria-label="Annuler">
            <X size={16} weight="light" color="#6b7280" />
          </button>
        </div>
      )}
    </Bezel>
  );
}

function ClosedRow({ t }: { t: JournalTrade }) {
  const qc = useQueryClient();
  const delMut = useMutation({
    mutationFn: () => api.journalDelete(t.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["journal"] }),
  });
  const r = t.r_multiple ?? 0;
  const win = r >= 0;

  return (
    <Bezel className="p-4">
      <div className="flex items-center justify-between">
        <Head t={t} />
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div
              className="text-lg font-semibold tabular-nums"
              style={{ fontFamily: "var(--font-display)", color: win ? "#5be0ae" : "#ff8497" }}
            >
              {signedR(r)}
            </div>
            <div className="text-[10px]" style={{ color: "var(--color-faint)" }}>
              sortie {num(t.exit_price ?? 0, 2)}
            </div>
          </div>
          <button onClick={() => delMut.mutate()} className="press" aria-label="Supprimer">
            <Trash size={14} weight="light" color="#4b5563" />
          </button>
        </div>
      </div>
      {t.notes && (
        <p className="mt-2 text-[12px]" style={{ color: "var(--color-muted)" }}>« {t.notes} »</p>
      )}
    </Bezel>
  );
}
