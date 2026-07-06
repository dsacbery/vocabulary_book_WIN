# Vocabulary Book for Windows

Windows 独立版的本地网页生词本。它保留 Flask 本地网页、CSV 生词本、导入导出、学习卡片和测验功能，并把查词逻辑改成 Windows 可用的混合模式：

1. 优先查 `data/ecdict.db`
2. 其次查 `data/ecdict.csv`
3. 再查内置小词库 `resources/mini_ecdict.csv`
4. 查不到时使用 Free Dictionary API 补英文释义、音标和例句
5. 所有来源都失败时进入手动录入

## Requirements

- Windows 10/11
- Python 3.10 or newer
- Internet access for first-time dependency installation and optional full dictionary download

## Setup

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Run

Double-click:

```text
启动-Windows.bat
```

If your Windows code page has trouble with Chinese file names, double-click:

```text
start-windows.bat
```

Manual startup:

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Full Chinese Dictionary

The bundled dictionary is intentionally small. For daily use, prepare the full ECDICT local database:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts\prepare_ecdict.py
```

This creates ignored local files:

```text
data/ecdict.csv
data/ecdict.db
```

ECDICT source: [skywind3000/ECDICT](https://github.com/skywind3000/ECDICT)

## Data

Personal word data is stored in:

```text
data/words.csv
```

This file is created automatically and ignored by Git.

## Test

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

## GitHub Upload Notes

Commit source, tests, launchers, docs, scripts, and `resources/mini_ecdict.csv`.

Do not commit:

- `.venv/`
- `data/words.csv`
- `data/imports/`
- `data/ecdict.csv`
- `data/ecdict.db`
