param(
    [string]$EvidenceDirectory = (Join-Path $PSScriptRoot ("..\Blackbox_Validation_" + (Get-Date -Format 'yyyyMMdd_HHmmss'))),
    [string]$PythonExecutable = 'py'
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') {
    throw 'Run this launcher in native Windows PowerShell. WSL alone cannot establish native Windows execution.'
}
$script = Join-Path $PSScriptRoot 'tools\validate_submission_runtime.py'
if ($PythonExecutable -eq 'py') {
    & $PythonExecutable -3.12 -B $script --require-windows --minutes 120 --output $EvidenceDirectory
} else {
    & $PythonExecutable -B $script --require-windows --minutes 120 --output $EvidenceDirectory
}
if ($LASTEXITCODE -ne 0) {
    throw "Submission runtime checks did not pass (exit $LASTEXITCODE). Inspect the external validation receipt."
}
Write-Host 'Native Windows and constrained Docker checks passed. Preserve the image ID and external validation receipt.'
