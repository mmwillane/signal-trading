import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { NotePencil, Check, X } from "@phosphor-icons/react";
import { api, type Proposal } from "../api/client";

/**
 * Bouton "Journaliser ce trade". Enregistre dans le journal LOCAL le trade
 * que l'utilisateur a (ou va) exécuter lui-même. N'exécute rien chez un broker.
 * L'entrée et la quantité sont ajustables (le prix réellement obtenu peut
 * différer de la suggestion).
 */
export function JournalButton({ p }: { p: Proposal }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [entry, setEntry] = useState(String(p.entry));
  const [qty, setQty] = useState(String(p.quantity));
  const [notes, setNotes] = useState("");

  const mut = useMutation({
    mutationFn: () =>
      api.journalAdd({
        symbol: p.symbol,
        direction: p.direction,
        entry: parseFloat(entry),
        stop: p.stop_loss,
        take_profit: p.take_profit,
        quantity: parseFloat(qty),
        confidence: p.confidence,
        notes,
        source: "suggestion",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["journal"] });
      setOpen(false);
    },
  });

  if (mut.isSuccess && !open) {
    return (
      <div className="flex items-center justify-center gap-2 rounded-full py-2.5 text-sm font-semibold" style={{ backgroundColor: "rgba(52,211,153,0.12)", color: "#5be0ae" }}>
        <Check size={16} weight="bold" /> Ajouté au journal
      </div>
    );
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="press group w-full flex items-center justify-center gap-2 rounded-full py-3 text-sm font-semibold"
        style={{ backgroundColor: "rgba(52,211,153,0.14)", color: "#5be0ae", border: "1px solid rgba(52,211,153,0.28)" }}
      >
        <NotePencil size={17} weight="light" />
        Journaliser ce trade
      </button>
    );
  }

  return (
    <div className="rounded-2xl p-3 space-y-3 hairline" style={{ backgroundColor: "rgba(255,255,255,0.02)" }}>
      <div className="flex items-center justify-between">
        <span className="eyebrow">Enregistrer (exécution manuelle de ta part)</span>
        <button onClick={() => setOpen(false)} className="press" aria-label="Fermer">
          <X size={16} weight="light" color="#6b7280" />
        </button>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Prix d'entrée réel" value={entry} onChange={setEntry} />
        <Field label="Volume" value={qty} onChange={setQty} />
      </div>
      <input
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Note (optionnel)"
        className="w-full rounded-xl px-3 py-2 text-sm bg-transparent hairline outline-none"
        style={{ color: "var(--color-text)" }}
      />
      {mut.isError && (
        <p className="text-xs" style={{ color: "var(--color-rose)" }}>{(mut.error as Error).message}</p>
      )}
      <button
        onClick={() => mut.mutate()}
        disabled={mut.isPending}
        className="press w-full flex items-center justify-center gap-2 rounded-full py-2.5 text-sm font-semibold"
        style={{ backgroundColor: "var(--color-emerald)", color: "#04140d", opacity: mut.isPending ? 0.6 : 1 }}
      >
        <Check size={16} weight="bold" /> {mut.isPending ? "Enregistrement…" : "Confirmer"}
      </button>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="block">
      <span className="eyebrow">{label}</span>
      <input
        type="number"
        inputMode="decimal"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-xl px-3 py-2 text-sm tabular-nums bg-transparent hairline outline-none"
        style={{ color: "var(--color-text)", fontFamily: "var(--font-display)" }}
      />
    </label>
  );
}
