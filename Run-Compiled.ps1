param([ValidateSet('conservative','coordinated')][string]$Mode = 'conservative')
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'tools\run_coordinated_compiled.py'
& py -3.12 -S -B $script --mode $Mode
exit $LASTEXITCODE
