$ErrorActionPreference = "Stop"

if (Test-Path "C:\nvm4w\nodejs\npm.cmd") {
    Write-Host "Using npm at C:\nvm4w\nodejs\npm.cmd"
    & 'C:\nvm4w\nodejs\npm.cmd' exec --yes '@mermaid-js/mermaid-cli' -- -i docs\ARCHITECTURE_DIAGRAM.mmd -o docs\ARCHITECTURE_DIAGRAM.png -w 2400 --backgroundColor white
} elseif (Test-Path "C:\Program Files\nodejs\npm.cmd") {
    Write-Host "Using npm at C:\Program Files\nodejs\npm.cmd"
    & 'C:\Program Files\nodejs\npm.cmd' exec --yes '@mermaid-js/mermaid-cli' -- -i docs\ARCHITECTURE_DIAGRAM.mmd -o docs\ARCHITECTURE_DIAGRAM.png -w 2400 --backgroundColor white
} else {
    throw "npm.cmd was not found. Install Node.js or update this script with the correct npm path."
}

if ($LASTEXITCODE -ne 0) {
    throw "Mermaid CLI render failed with exit code $LASTEXITCODE"
}

Write-Host "Rendered docs\\ARCHITECTURE_DIAGRAM.png"
