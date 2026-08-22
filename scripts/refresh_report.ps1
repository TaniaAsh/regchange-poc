# scripts/refresh_report.ps1
#
# One command for the live demo instead of three separate ones typed under
# pressure: downloads current impact-hypotheses, filters out the pre-fix
# orphan files (no -ART suffix), regenerates the HTML report, opens it.
#
# Usage:
#   .\scripts\refresh_report.ps1

$ErrorActionPreference = "Stop"

$storageAccount = "regchgst5q4n3y5rwo4dc"
$hypothesesDir = ".\hypotheses"
$reportOut = "out\compliance_review.html"

Write-Host "Downloading impact hypotheses..." -ForegroundColor Cyan
az storage blob download-batch `
  --account-name $storageAccount `
  --source impact-hypotheses `
  --destination $hypothesesDir `
  --auth-mode login `
  --overwrite | Out-Null

Write-Host "Removing pre-fix orphan files (no article suffix)..." -ForegroundColor Cyan
Get-ChildItem "$hypothesesDir\*.json" | Where-Object { $_.Name -notmatch 'ART' } | Remove-Item -ErrorAction SilentlyContinue

Write-Host "Regenerating report..." -ForegroundColor Cyan
python scripts/generate_report.py $hypothesesDir --out $reportOut

Write-Host "Opening report..." -ForegroundColor Green
Start-Process $reportOut
