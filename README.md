# Assistant de trading personnel — aide à la décision, **lecture seule**

Un outil Python qui **analyse le marché et propose des ordres complets, prêts à
exécuter manuellement**. Il n'exécute jamais rien, ne se connecte aux brokers
qu'en lecture, et n'a aucune capacité de passer, modifier ou annuler un ordre.

> ⚠️ Ce logiciel ne prédit pas le marché et ne garantit aucun résultat. Les
> propositions sont des aides à la décision, à valider et exécuter vous-même.

Trois façons de l'utiliser :
- **Application web & mobile** (recommandé) — interface premium, installable sur
  téléphone (PWA). Voir [Application web & mobile](#application-web--mobile).
- **Terminal** — `python main.py` (voir plus bas).
- **API** — backend FastAPI lecture seule (`api/`), consommé par l'app.

---

## Application web & mobile

Interface graphique moderne (React + Vite), pensée mobile d'abord et
**installable comme une app** sur iOS/Android (PWA). Elle s'appuie sur un
backend FastAPI qui réutilise toute la logique Python — toujours en lecture
seule.

### Lancer l'app (backend + frontend)

Le plus simple, sous Windows :

```powershell
./start.ps1
```

Cela ouvre le backend (port 8010) et le frontend (port 5173), puis l'app dans
le navigateur. Manuellement, en deux terminaux :

```bash
# 1) Backend API (lecture seule)
python -m uvicorn api.main:app --port 8010

# 2) Frontend web/mobile
cd web
npm install        # première fois
npm run dev        # http://localhost:5173
```

> Le backend écoute sur le port **8010** (le 8000 étant souvent pris par
> d'autres apps locales). Le proxy Vite pointe déjà dessus.

Détails, build de production et installation PWA sur téléphone : voir
[`web/README.md`](web/README.md).

---

## Partager pour tester (avec des amis)

Le backend peut servir le frontend buildé : **toute l'app tient alors sur une
seule URL / un seul port (8010)**, facile à partager.

### Option A — Réseau local (le plus sûr, immédiat)

```powershell
./share.ps1
```

Le script build le frontend, lance le service sur `0.0.0.0:8010` et affiche
l'adresse à donner (`http://TON_IP:8010`). Tes amis **connectés au même
Wi-Fi** l'ouvrent dans leur navigateur. Ton PC doit rester allumé. (Le
pare-feu Windows peut demander d'autoriser Python : accepte.)

### Option B — Internet via tunnel (rapide, temporaire)

Pour des amis **hors de ton réseau**, un tunnel expose le port 8010 avec une
URL publique https (idéal aussi pour installer la PWA). Avec Cloudflare
(gratuit, sans compte pour un tunnel éphémère) :

```bash
# 1) lance l'app en local d'abord (share.ps1 ou uvicorn ... --port 8010)
# 2) dans un autre terminal :
cloudflared tunnel --url http://localhost:8010
```

Cloudflared affiche une URL `https://xxxx.trycloudflare.com` à partager. Elle
change à chaque redémarrage (tunnel éphémère). Ton PC doit rester allumé.

### Option C — Hébergement cloud (URL stable, PC éteint possible)

Pour une URL permanente, héberge le service unique (FastAPI + `web/dist`) sur
un hébergeur gratuit (Render, Railway, Fly.io). Build : `npm --prefix web run
build` puis lancer `uvicorn api.main:app --host 0.0.0.0 --port $PORT`.

### ⚠ Points importants pour le partage

- **Sécurité** : en mode démo (aucune clé broker), l'app n'expose que des
  **données de marché publiques** — rien de sensible. Ne mets **jamais** de
  clés broker dans un `.env` déployé publiquement.
- **Journal partagé** : il n'y a pas de comptes utilisateurs. Toutes les
  personnes qui ont l'URL écrivent dans **le même** `data/journal.json`. C'est
  acceptable pour un test entre amis, mais chacun voit/modifie le journal
  commun. (Une séparation par utilisateur serait à ajouter pour un vrai
  multi-utilisateur.)
- L'app reste **lecture seule côté broker** en toutes circonstances.

---

## Ce que l'outil NE fait JAMAIS

- Exécuter, envoyer, modifier ou annuler un ordre.
- Se connecter à un broker autrement qu'en **lecture seule**.
- Stocker des identifiants de compte au-delà des clés API (lecture seule) du `.env`.
- Prétendre prédire le marché ou garantir un gain.

Cet invariant est **testé** : `tests/test_readonly.py` échoue si une méthode
d'exécution apparaît sur un connecteur ou si le code référence un endpoint
d'écriture broker.

---

## Architecture (un module par responsabilité)

```
main.py                 Orchestrateur mode démo (propositions)
run_backtest.py         Lancement du backtest
src/
  security/             Fondations : env, logging caviardé, sanitize, réseau
    env.py              Chargement/validation .env, accès secret unique
    safe_logging.py     Logger qui masque tout secret
    sanitize.py         Nettoyage des entrées externes (API, news)
    net.py              GET robuste : timeout + retries + backoff
  data/market_data.py   Données de marché (yfinance)
  news/                 news_feed.py (RSS) + sentiment.py (VADER)
  analysis/             indicators.py (MA/RSI/MACD/ATR) + analyzer.py (setup)
  knowledge/            trading_rules.py (principes de risque, reformulés)
  proposal/             position_sizing.py + order_proposal.py
  backtest/engine.py    Backtest de la MÊME logique de setup
  connectors/           base.py (interface lecture seule) + adaptateurs
                        + aggregator.py (vue consolidée)
tests/                  Tests logique, sécurité, invariant lecture seule
```

**Point clé** : la logique de setup vit dans `analysis/analyzer.py` et est
réutilisée telle quelle par le backtest — on teste exactement ce qu'on propose.

---

## Installation

```bash
cd trading-assistant
python -m venv .venv
# Windows : .venv\Scripts\activate      |  macOS/Linux : source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows : copy .env.example .env
```

Éditez `.env` : au minimum `CAPITAL`, `RISK_PER_TRADE`, `WATCHLIST`.
Les clés broker restent **vides** tant que vous êtes en mode démo.

---

## Utilisation

### 1. Mode démo (par défaut, aucune connexion broker)

```bash
python main.py
```

Lit les données publiques de la watchlist, calcule les indicateurs, croise le
sentiment des news, et affiche des **propositions d'ordre** (entrée, stop,
take profit, R/R, taille de position, raisonnement). S'il n'y a pas de setup
clair, il le dit franchement.

```bash
python main.py --no-news      # sans sentiment news
python main.py --brokers      # ajoute la vue portefeuille (si clés read-only)
```

### 2. Backtest

```bash
python run_backtest.py                 # watchlist du .env
python run_backtest.py AAPL MSFT --period 5y
```

Sort win rate, profit factor, R/R moyen, drawdown max (en R), résultat total.

### 3. Tests

```bash
pytest -q
```

---

## Configurer le capital et le risque par trade

Dans `.env` :

```
CAPITAL=10000          # capital total pris en compte
RISK_PER_TRADE=0.01    # 1 % du capital risqué par trade (borne dure : 10 %)
```

La taille de position est calculée pour que, si le stop est touché, la perte
soit d'environ `CAPITAL × RISK_PER_TRADE`. L'exposition ne dépasse jamais le
capital (aucun levier implicite).

---

## Connecter un broker en **lecture seule**

Le mode démo n'a besoin d'aucun broker. Pour afficher un portefeuille réel en
lecture, installez le SDK concerné (dans `requirements.txt`, décommentez la
ligne) puis renseignez des clés **read-only** dans `.env`.

### Créer des clés en permission lecture seule

| Broker | Comment obtenir une clé lecture seule |
|--------|----------------------------------------|
| **Alpaca** | Dashboard → API Keys → générez une clé, cochez le profil « read only ». Laissez `ALPACA_PAPER=true` pour explorer. |
| **Binance** | API Management → créez une clé, **ne cochez QUE « Enable Reading »**. Ne cochez jamais « Enable Spot Trading ». |
| **Kraken** | Security → API → New Key, cochez uniquement **« Query Funds / Query Open Orders & Trades »**, décochez « Create & Modify Orders ». |
| **OANDA** | Manage API Access → générez un token. Utilisez un compte `practice` pour l'exploration. |
| **Interactive Brokers** | Pas de clé dans `.env`. Lancez IB Gateway/TWS et cochez **Configuration → API → Read-Only API**. La passerelle refuse alors tout ordre au niveau protocole. |

Après avoir renseigné les clés :

```bash
python main.py --brokers
```

Un broker sans SDK installé, sans clé, ou dont l'API est restreinte est
**signalé et ignoré** — jamais une cause de plantage.

---

## Ajouter un nouvel adaptateur broker

1. Créez `src/connectors/mon_broker.py`.
2. Héritez de `ReadOnlyBrokerConnector` (`src/connectors/base.py`) et
   implémentez **uniquement** : `is_available`, `get_balance`,
   `get_positions`, `get_order_history`, `get_account_info`.
3. Lisez vos secrets via `broker_secret("MON_BROKER_KEY")` (jamais `os.environ`
   en direct), et importez le SDK **paresseusement** dans une méthode pour que
   son absence n'empêche pas le reste de tourner.
4. Traduisez l'API du broker vers les DTO neutres (`Balance`, `Position`,
   `OrderRecord`, `AccountInfo`).
5. Ajoutez une instance dans `default_connectors()` de `aggregator.py`.
6. **N'ajoutez aucune méthode d'écriture** : `pytest tests/test_readonly.py`
   doit rester vert.

---

## Sécurité — résumé

- **Secrets** : uniquement dans `.env` (ignoré par git). `.env.example` liste
  les variables sans valeurs. Jamais de secret en dur.
- **Validation au démarrage** : variables obligatoires vérifiées, message clair
  sinon (`src/security/env.py`).
- **Entrées externes** : réponses API et news assainies avant tout traitement
  (`src/security/sanitize.py`). Aucune confiance envers le réseau.
- **Logs** : un filtre masque automatiquement toute valeur ressemblant à un
  secret (`src/security/safe_logging.py`). Aucun solde/clé/ID loggé
  volontairement.
- **Réseau** : timeouts, retries et backoff exponentiel + respect de
  `Retry-After` (`src/security/net.py`).
- **Dépendances** : versions épinglées. Auditez avec :

  ```bash
  pip-audit -r requirements.txt
  ```

### En cas de fuite d'une clé

1. **Révoquez immédiatement** la clé dans le dashboard du broker concerné.
2. Générez-en une nouvelle en **lecture seule**.
3. Mettez à jour `.env` (jamais commité).
4. Comme toutes les clés sont read-only, une fuite ne permet pas de trader —
   mais révoquez tout de même sans délai.

---

## Avertissement

Outil personnel d'aide à la décision, fourni sans garantie. Il ne constitue pas
un conseil en investissement. Les performances passées (y compris de backtest)
ne préjugent pas des résultats futurs. Vous restez seul responsable de vos
décisions et de leur exécution.
