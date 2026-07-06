# Windows Dictionary Port Design

## Goal

Create an independent Windows version of the vocabulary notebook. The app must run without macOS
Swift tooling and should return Chinese meanings when looking up English words.

## Lookup Order

1. Local ECDICT SQLite database at `data/ecdict.db`
2. Local ECDICT CSV file at `data/ecdict.csv`
3. Bundled small CSV dictionary at `resources/mini_ecdict.csv`
4. Free Dictionary API fallback
5. Manual entry

## Launchers

- `start-windows.ps1` is the main PowerShell launcher.
- `start-windows.bat` is the ASCII batch launcher.
- `启动-Windows.bat` delegates to `start-windows.bat` so double-clicking works while `cmd.exe`
  avoids parsing non-ASCII script paths.

## GitHub Readiness

Commit source, tests, docs, scripts, launchers, and `resources/mini_ecdict.csv`.
Do not commit `.venv`, personal word data, or generated full ECDICT files.
