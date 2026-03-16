param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$python = Join-Path $PSScriptRoot "..\server\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "Missing Python interpreter at $python"
    exit 1
}

& $python @Args
exit $LASTEXITCODE
