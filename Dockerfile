# Image unique : build le frontend (Node) puis sert front + API (Python).
# Fonctionne sur Render, Railway, Fly.io, etc. Une seule URL à partager.

# --- Étape 1 : build du frontend React ---
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# --- Étape 2 : runtime Python (sert web/dist + l'API) ---
FROM python:3.13-slim
WORKDIR /app

# Dépendances Python (wheels précompilés, pas de compilation).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Code applicatif.
COPY src/ ./src/
COPY api/ ./api/

# Frontend buildé, récupéré depuis l'étape 1.
COPY --from=web /web/dist ./web/dist

# Le journal (données locales) vit ici. Éphémère sur les offres gratuites.
RUN mkdir -p data

# La plupart des hébergeurs fournissent $PORT ; défaut 8010 en local.
ENV PORT=8010
EXPOSE 8010
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8010}"]
