import { useEffect, useState } from "react";

// Réglages PROPRES à chaque utilisateur, stockés dans le navigateur
// (localStorage). Il n'y a pas de comptes : chacun met SON capital et son
// risque, et l'app les envoie à l'API pour le calcul des positions.

const KEY = "signal.userSettings.v1";

export interface UserSettings {
  capital: number | null; // null => on utilise la valeur par défaut du serveur
  risk: number | null; // fraction (0.01 = 1 %)
  fractional: boolean; // le broker permet les actions fractionnées (petits budgets)
  moreSignals: boolean; // mode « plus de signaux » (seuils assouplis, moins fiable)
}

const EMPTY: UserSettings = { capital: null, risk: null, fractional: false, moreSignals: false };

export function loadUserSettings(): UserSettings {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...EMPTY };
    const v = JSON.parse(raw);
    return {
      capital: typeof v.capital === "number" && v.capital > 0 ? v.capital : null,
      risk: typeof v.risk === "number" && v.risk > 0 && v.risk <= 0.1 ? v.risk : null,
      fractional: v.fractional === true,
      moreSignals: v.moreSignals === true,
    };
  } catch {
    return { ...EMPTY };
  }
}

export function saveUserSettings(v: UserSettings): void {
  localStorage.setItem(KEY, JSON.stringify(v));
  // Notifie les composants abonnés (même onglet).
  window.dispatchEvent(new Event("signal:usersettings"));
}

export function useUserSettings(): UserSettings {
  const [s, setS] = useState<UserSettings>(loadUserSettings);
  useEffect(() => {
    const handler = () => setS(loadUserSettings());
    window.addEventListener("signal:usersettings", handler);
    window.addEventListener("storage", handler); // autres onglets
    return () => {
      window.removeEventListener("signal:usersettings", handler);
      window.removeEventListener("storage", handler);
    };
  }, []);
  return s;
}
