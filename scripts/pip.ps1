param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$pip = Join-Path $PSScriptRoot "..\server\.venv\Scripts\pip.exe"

if (-not (Test-Path $pip)) {
    Write-Error "Missing pip executable at $pip"
    exit 1
}

& $pip @Args
exit $LASTEXITCODE
