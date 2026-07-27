# Signal — Frontend web & mobile (PWA)

Interface **React + Vite** de l'assistant de trading. Design premium sombre,
pensée mobile d'abord, installable sur téléphone comme une vraie app (PWA).
Elle consomme l'API FastAPI **lecture seule** (aucune exécution d'ordre).

## Stack

- **React 19 + Vite 6 + TypeScript**
- **Tailwind CSS v4** (design tokens dans `src/index.css`)
- **lightweight-charts** (graphiques en chandeliers, TradingView)
- **@tanstack/react-query** (cache + états de chargement)
- **@phosphor-icons/react** (icônes fines)
- **vite-plugin-pwa** (service worker + manifest, installable)
- Polices : Space Grotesk (titres) + Plus Jakarta Sans (corps)

## Écrans

| Route | Écran |
|-------|-------|
| `/` | Signaux — watchlist, propositions du jour, capital/risque |
| `/instrument/:symbol` | Détail — graphique, indicateurs, proposition complète, news liées |
| `/backtest` | Backtest — stats + courbe d'équité |
| `/news` | Actualités — flux macro filtrés + sentiment |
| `/portfolio` | Comptes — vue brokers lecture seule (démo par défaut) |

## Développement

Le frontend a besoin du backend API (port **8010**). Depuis la racine du projet :

```bash
# Terminal 1 — backend
python -m uvicorn api.main:app --port 8010

# Terminal 2 — frontend
cd web
npm install      # première fois seulement
npm run dev      # http://localhost:5173
```

En dev, Vite proxifie `/api` vers `http://127.0.0.1:8010` (voir `vite.config.ts`).

## Build de production (PWA)

```bash
cd web
npm run build    # génère dist/ + service worker (sw.js) + manifest
npm run preview  # sert le build localement
```

## Installer sur téléphone

1. Ouvre l'app dans le navigateur du téléphone (même réseau : remplace
   `localhost` par l'IP locale de ton PC, et lance Vite avec `--host`).
2. **iOS Safari** : Partager → « Sur l'écran d'accueil ».
   **Android Chrome** : menu → « Installer l'application ».
3. L'app s'ouvre en plein écran, avec l'icône Signal.

> Le service worker ne met en cache que l'app (coquille statique), **jamais**
> les réponses d'API : les données de marché restent fraîches.

## Régénérer les icônes

```bash
cd web
python scripts/make_icons.py
```

## Sécurité

Le frontend n'appelle que des endpoints GET d'analyse et de consultation. Il
n'existe aucune fonction d'exécution d'ordre côté client. Toutes les clés
broker restent côté serveur, dans le `.env` (jamais exposées au navigateur).
