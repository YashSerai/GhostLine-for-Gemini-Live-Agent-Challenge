# Codex Local Tooling

Use these repo-local wrappers when you want deterministic tool resolution inside this workspace.

Available commands:

- `./scripts/python.ps1`
- `./scripts/pip.ps1`
- `./scripts/node.ps1`
- `./scripts/npm.ps1`

Why these exist:

- Codex does not run inside your current interactive PowerShell session.
- Global `PATH` resolution can differ from what you see locally.
- Windows launcher shims like `uvicorn.exe` and `npm.cmd` are less reliable than explicit paths in this environment.

Examples:

```powershell
.\scripts\python.ps1 --version
.\scripts\python.ps1 -m pytest
.\scripts\pip.ps1 list
.\scripts\node.ps1 --version
.\scripts\npm.ps1 run build --prefix client
```

For backend commands, prefer the venv-backed wrappers over global `python` or `pip`.
