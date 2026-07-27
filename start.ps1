# Lance l'assistant de trading complet (backend API + frontend web/mobile).
# Usage :  clic droit > Exécuter avec PowerShell   OU   ./start.ps1
#
# Ouvre deux fenêtres :
#   - Backend  FastAPI  (lecture seule) sur http://127.0.0.1:8010
#   - Frontend Vite/PWA                 sur http://localhost:5173
#
# Ensuite, ouvre http://localhost:5173 dans ton navigateur (ou installe
# la PWA sur ton téléphone via "Ajouter à l'écran d'accueil").

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "Demarrage de l'assistant de trading (lecture seule)..." -ForegroundColor Green

# 1) Backend API (port 8010)
Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "cd '$root'; python -m uvicorn api.main:app --port 8010"
)

# 2) Frontend web/mobile (port 5173)
Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "cd '$root\web'; npm run dev"
)

Start-Sleep -Seconds 3
Write-Host "Backend : http://127.0.0.1:8010/api/health" -ForegroundColor Cyan
Write-Host "App     : http://localhost:5173" -ForegroundColor Cyan
Start-Process "http://localhost:5173"
