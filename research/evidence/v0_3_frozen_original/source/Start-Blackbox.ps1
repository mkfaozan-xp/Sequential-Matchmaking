param([ValidateRange(1,120)][int]$Minutes = 120)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$launcher = Get-Command py -ErrorAction SilentlyContinue
if ($launcher) {
    & py -3.12 -c "import sys; assert sys.version_info[:2] == (3,12)"
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12.x with the Python launcher, then run again. See WINDOWS_START.md.' }
    & py -3.12 scripts/run_budget.py --bootstrap --minutes $Minutes
} else {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) { throw 'Python 3.12.x is required. See WINDOWS_START.md.' }
    & python -c "import sys; assert sys.version_info[:2] == (3,12)"
    if ($LASTEXITCODE -ne 0) { throw 'The active Python must be 3.12.x. See WINDOWS_START.md.' }
    & python scripts/run_budget.py --bootstrap --minutes $Minutes
}
if ($LASTEXITCODE -ne 0) { throw 'Workflow incomplete. Inspect results/budget_run.json and the phase logs; no pass is implied.' }
Write-Host 'Workflow finished. Read results/REPORT.md and results/release_readiness.json.'
