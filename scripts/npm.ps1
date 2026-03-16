param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$npm = "C:\nvm4w\nodejs\npm.cmd"

if (-not (Test-Path $npm)) {
    Write-Error "Missing npm executable at $npm"
    exit 1
}

& $npm @Args
exit $LASTEXITCODE
