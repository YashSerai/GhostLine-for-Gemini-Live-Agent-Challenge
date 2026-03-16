param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$node = "C:\nvm4w\nodejs\node.exe"

if (-not (Test-Path $node)) {
    Write-Error "Missing Node executable at $node"
    exit 1
}

& $node @Args
exit $LASTEXITCODE
