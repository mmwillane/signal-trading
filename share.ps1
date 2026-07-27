# Lance l'assistant en MODE PARTAGE : une seule URL, accessible depuis
# d'autres appareils (téléphones, PC d'amis) sur le même réseau Wi-Fi.
#
# Usage :  ./share.ps1
#
# 1) build le frontend, 2) le backend le sert + l'API sur le port 8010,
# 3) écoute sur toutes les interfaces (0.0.0.0) et affiche l'adresse à
#    partager.
#
# NOTE : par défaut, seuls les appareils du MÊME réseau Wi-Fi peuvent y
# accéder (c'est le plus sûr). Pour partager sur Internet, voir le README
# (section « Partager »), options tunnel ou hébergement.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "1/2  Build du frontend..." -ForegroundColor Cyan
npm --prefix "$root\web" run build
if ($LASTEXITCODE -ne 0) { Write-Host "Echec du build." -ForegroundColor Red; exit 1 }

# Adresse IP locale (pour la donner aux amis sur le meme Wi-Fi).
$ip = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
    Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "2/2  Demarrage du service (port 8010)..." -ForegroundColor Cyan
Write-Host ""
Write-Host "  Sur CE PC        : http://localhost:8010" -ForegroundColor Green
if ($ip) {
    Write-Host "  Amis (meme Wi-Fi): http://$($ip):8010" -ForegroundColor Green
    Write-Host ""
    Write-Host "  -> Donne cette derniere adresse a tes amis connectes au meme Wi-Fi." -ForegroundColor Yellow
    Write-Host "     (Ton pare-feu Windows peut demander d'autoriser Python : accepte.)" -ForegroundColor Yellow
}
Write-Host ""

Set-Location $root
python -m uvicorn api.main:app --host 0.0.0.0 --port 8010
