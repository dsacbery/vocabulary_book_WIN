from __future__ import annotations

import argparse
import csv
import sqlite3
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_URL = "https://raw.githubusercontent.com/skywind3000/ECDICT/master/ecdict.csv"
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "ecdict.csv"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "ecdict.db"


def strip_word(word: str) -> str:
    return "".join(ch for ch in word.lower() if ch.isalnum())


def download_csv(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading ECDICT CSV from {url}")
    print(f"Writing {target}")
    with urllib.request.urlopen(url, timeout=60) as response:
        with target.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)


def build_sqlite(csv_path: Path, db_path: Path) -> int:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    temp_db = db_path.with_suffix(".tmp.db")
    temp_db.unlink(missing_ok=True)

    count = 0
    connection = sqlite3.connect(temp_db)
    try:
        connection.execute(
            """
            CREATE TABLE stardict (
                word TEXT PRIMARY KEY,
                sw TEXT NOT NULL,
                phonetic TEXT,
                definition TEXT,
                translation TEXT,
                pos TEXT
            )
            """
        )
        connection.execute("CREATE INDEX idx_stardict_sw ON stardict(sw)")

        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                word = (row.get("word") or "").strip()
                if not word:
                    continue
                connection.execute(
                    """
                    INSERT OR REPLACE INTO stardict
                    (word, sw, phonetic, definition, translation, pos)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        word,
                        strip_word(word),
                        row.get("phonetic", ""),
                        row.get("definition", ""),
                        row.get("translation", ""),
                        row.get("pos", ""),
                    ],
                )
                count += 1
                if count % 10000 == 0:
                    print(f"Imported {count} rows...")
        connection.commit()
    finally:
        connection.close()

    temp_db.replace(db_path)
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download ECDICT and build data/ecdict.db for fast local Chinese lookup."
    )
    parser.add_argument("--url", default=DEFAULT_CSV_URL, help="ECDICT CSV download URL.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH, help="Output/input CSV path.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Output SQLite DB path.")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Build SQLite from the existing CSV without downloading it first.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_path = args.csv.resolve()
    db_path = args.db.resolve()

    if not args.skip_download:
        download_csv(args.url, csv_path)

    count = build_sqlite(csv_path, db_path)
    print(f"Built {db_path} with {count} entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
