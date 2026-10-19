param([ValidateRange(1,120)][int]$Minutes = 120, [string]$Python = '', [switch]$HostOnly)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$candidates = @()
if ($Python) { $candidates += @{Command=$Python; Prefix=@()} }
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($version in @('-3.12','-3.13','-3.14','-3')) { $candidates += @{Command='py'; Prefix=@($version)} }
}
if (-not $Python -and (Get-Command python -ErrorAction SilentlyContinue)) { $candidates += @{Command='python'; Prefix=@()} }
$chosen = $null
foreach ($candidate in $candidates) {
    $command = $candidate.Command
    $prefix = $candidate.Prefix
    $probeCode = 1
    $savedErrorAction = $ErrorActionPreference
    try {
        # Windows PowerShell 5.1 can promote native stderr to an error record.
        # A missing Python version is a probe failure, not a workflow failure.
        $ErrorActionPreference = 'Continue'
        & $command @prefix -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,12) else 1)' 2>$null
        $probeCode = $LASTEXITCODE
    } catch { $probeCode = 1 }
    finally { $ErrorActionPreference = $savedErrorAction }
    if ($probeCode -eq 0) { $chosen=$candidate; break }
}
if (-not $chosen) { throw 'Python 3.12+ required. Use -Python with an explicit executable. See WINDOWS_START.md.' }
$command = $chosen.Command
$prefix = $chosen.Prefix
$arguments = @('scripts/run_research.py','--bootstrap','--minutes',"$Minutes",'--skip-training')
if ($HostOnly) { $arguments += '--skip-docker' }
& $command @prefix @arguments
if ($LASTEXITCODE -ne 0) { throw 'Workflow incomplete. Inspect results/budget_run.json and phase logs. No pass is implied.' }
Write-Host 'Workflow completed. Read results/REPORT.md and results/release_readiness.json; completion is not promotion.'
