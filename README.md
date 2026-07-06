# Vocabulary Book for Windows

A Windows-ready local web vocabulary book based on the original macOS project. It keeps the Flask web interface, CSV wordbook storage, import/export, flashcards, and quizzes, while replacing the macOS Dictionary dependency with a Windows-friendly lookup flow.

Lookup priority:

1. `data/ecdict.db`
2. `data/ecdict.csv`
3. `resources/mini_ecdict.csv`
4. Free Dictionary API for English definitions, phonetics, and examples
5. Manual entry when no source can resolve the word

## Quick Start

Run these commands in PowerShell on a Windows 10/11 machine:

```powershell
git clone https://github.com/dsacbery/vocabulary_book_WIN.git
cd vocabulary_book_WIN
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the app:

```powershell
.\.venv\Scripts\python.exe app.py
```

Then open:

```text
http://127.0.0.1:5000
```

You can also double-click `start-windows.bat` or `启动-Windows.bat` after the virtual environment and dependencies have been installed.

Quick lookup check:

```powershell
@'
from app import create_app

app = create_app({"TESTING": True})
client = app.test_client()
response = client.post("/api/lookup", json={"word": "benefit"})
entry = response.get_json()["entry"]

print(response.status_code)
print(entry["source"])
print(entry["chinese_meaning"])
'@ | .\.venv\Scripts\python.exe -
```

Expected result: status code `200`, source `local_ecdict`, and a Chinese meaning for `benefit`.

## Requirements

- Windows 10/11
- Python 3.10 or newer
- Internet access for first-time dependency installation
- Internet access for the optional full ECDICT download

## Setup

If you already cloned the repository, create the virtual environment and install dependencies:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If PowerShell blocks script activation, run this in the same PowerShell window:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Activation is optional because the commands above call the virtual environment Python directly.

## Run

Double-click either launcher after setup:

```text
start-windows.bat
启动-Windows.bat
```

If your Windows code page has trouble with Chinese file names, use `start-windows.bat`.

Manual startup:

```powershell
.\.venv\Scripts\python.exe app.py
```

Then open:

```text
http://127.0.0.1:5000
```

The launcher opens the first available local port from `5000` through `5010`.

## Full Chinese Dictionary

The repository includes a small dictionary at `resources/mini_ecdict.csv` so the app works immediately after setup. For daily use, prepare the full ECDICT local database:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_ecdict.py
```

This creates ignored local files:

```text
data/ecdict.csv
data/ecdict.db
```

These files are intentionally not committed because they are large. ECDICT source: [skywind3000/ECDICT](https://github.com/skywind3000/ECDICT)

## Data

Personal vocabulary data is stored in:

```text
data/words.csv
```

This file is created automatically and ignored by Git.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Repository Notes

Commit source files, tests, launchers, docs, scripts, and `resources/mini_ecdict.csv`.

Do not commit:

- `.venv/`
- `data/words.csv`
- `data/imports/`
- `data/ecdict.csv`
- `data/ecdict.db`

---

# Vocabulary Book Windows 版中文说明

这是基于原 macOS 项目改造的 Windows 独立版本地网页生词本。它保留了 Flask 本地网页、CSV 生词本、导入导出、学习卡片和测验功能，并把原先依赖 macOS 自带词典的查词逻辑改成了 Windows 可用的混合查询模式。

查词优先级：

1. `data/ecdict.db`
2. `data/ecdict.csv`
3. `resources/mini_ecdict.csv`
4. Free Dictionary API，用于补充英文释义、音标和例句
5. 所有来源都查不到时，进入手动录入

## 快速开始

在 Windows 10/11 的 PowerShell 中运行：

```powershell
git clone https://github.com/dsacbery/vocabulary_book_WIN.git
cd vocabulary_book_WIN
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

启动项目：

```powershell
.\.venv\Scripts\python.exe app.py
```

然后打开：

```text
http://127.0.0.1:5000
```

安装好虚拟环境和依赖后，也可以直接双击 `start-windows.bat` 或 `启动-Windows.bat` 启动。

快速查词检查：

```powershell
@'
from app import create_app

app = create_app({"TESTING": True})
client = app.test_client()
response = client.post("/api/lookup", json={"word": "benefit"})
entry = response.get_json()["entry"]

print(response.status_code)
print(entry["source"])
print(entry["chinese_meaning"])
'@ | .\.venv\Scripts\python.exe -
```

预期结果：状态码为 `200`，来源为 `local_ecdict`，并且 `benefit` 能返回中文释义。

## 环境要求

- Windows 10/11
- Python 3.10 或更新版本
- 首次安装依赖时需要联网
- 如需下载完整 ECDICT 词库，也需要联网

## 安装

如果你已经克隆了仓库，可以这样创建虚拟环境并安装依赖：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

如果 PowerShell 阻止激活脚本，可以在当前 PowerShell 窗口运行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

本 README 中的命令直接调用 `.venv` 里的 Python，因此不激活虚拟环境也可以运行。

## 运行

安装完成后，双击以下任一启动脚本：

```text
start-windows.bat
启动-Windows.bat
```

如果你的 Windows 代码页对中文文件名兼容不好，建议使用 `start-windows.bat`。

手动启动：

```powershell
.\.venv\Scripts\python.exe app.py
```

然后打开：

```text
http://127.0.0.1:5000
```

启动脚本会在本机 `5000` 到 `5010` 之间寻找可用端口。

## 完整中文词库

仓库内置了一个小词库 `resources/mini_ecdict.csv`，因此项目安装后可以立即完成基本查词。日常使用建议准备完整 ECDICT 本地数据库：

```powershell
.\.venv\Scripts\python.exe scripts\prepare_ecdict.py
```

该命令会生成以下被 Git 忽略的本地文件：

```text
data/ecdict.csv
data/ecdict.db
```

这些文件体积较大，所以不会上传到仓库。ECDICT 来源：[skywind3000/ECDICT](https://github.com/skywind3000/ECDICT)

## 数据文件

个人生词数据保存在：

```text
data/words.csv
```

该文件会自动创建，并且不会被 Git 提交。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 仓库维护说明

应该提交源码、测试、启动脚本、文档、脚本和 `resources/mini_ecdict.csv`。

不要提交：

- `.venv/`
- `data/words.csv`
- `data/imports/`
- `data/ecdict.csv`
- `data/ecdict.db`
