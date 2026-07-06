from __future__ import annotations

import csv
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


CSV_FIELDS = [
    "id",
    "unit",
    "word",
    "phonetic",
    "part_of_speech",
    "chinese_meaning",
    "example",
    "source",
    "status",
    "created_at",
    "updated_at",
]

VALID_STATUSES = {"new", "known", "review_later"}
WORD_PATTERN = re.compile(r"^[A-Za-z][A-Za-z' -]*$")


class DuplicateWordError(ValueError):
    """Raised when a word already exists in the selected unit."""


class InvalidWordError(ValueError):
    """Raised when the entered word is empty or not English-like text."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat()


def normalize_word(word: str) -> str:
    normalized = " ".join(word.strip().lower().split())
    if not normalized or not WORD_PATTERN.match(normalized):
        raise InvalidWordError("Please enter an English word.")
    return normalized


def validate_unit(unit: int | str) -> int:
    if isinstance(unit, bool):
        raise ValueError("Unit must be a number from 1 to 20.")
    if isinstance(unit, int):
        value = unit
    elif isinstance(unit, str) and unit.isdigit():
        value = int(unit)
    else:
        raise ValueError("Unit must be a number from 1 to 20.")
    if value < 1 or value > 20:
        raise ValueError("Unit must be between 1 and 20.")
    return value


class Wordbook:
    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.ensure_csv()

    def ensure_csv(self) -> None:
        if not self.csv_path.exists():
            with self.csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
                writer.writeheader()
            return

        with self.csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader, None)
        if header != CSV_FIELDS:
            raise ValueError(
                f"CSV header mismatch in {self.csv_path}. Expected {CSV_FIELDS}, got {header}."
            )

    def _read_rows(self) -> list[dict[str, str]]:
        self.ensure_csv()
        with self.csv_path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def _write_rows(self, rows: Iterable[dict[str, str]]) -> None:
        temp_path = self.csv_path.with_name(f".{self.csv_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
                writer.writeheader()
                for row in rows:
                    writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})
            temp_path.replace(self.csv_path)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    def list_words(self, unit: int | str | None = None) -> list[dict[str, str]]:
        rows = self._read_rows()
        if unit is None:
            return rows
        selected_unit = str(validate_unit(unit))
        return [row for row in rows if row["unit"] == selected_unit]

    def add_word(
        self,
        unit: int | str,
        word: str,
        phonetic: str,
        part_of_speech: str,
        chinese_meaning: str,
        example: str,
        source: str,
    ) -> dict[str, str]:
        selected_unit = validate_unit(unit)
        normalized_word = normalize_word(word)
        rows = self._read_rows()
        if any(row["unit"] == str(selected_unit) and row["word"] == normalized_word for row in rows):
            raise DuplicateWordError(f"{normalized_word} already exists in Unit {selected_unit}.")

        now = utc_now_iso()
        row = {
            "id": str(uuid.uuid4()),
            "unit": str(selected_unit),
            "word": normalized_word,
            "phonetic": phonetic.strip(),
            "part_of_speech": part_of_speech.strip(),
            "chinese_meaning": chinese_meaning.strip(),
            "example": example.strip(),
            "source": source.strip() or "manual",
            "status": "new",
            "created_at": now,
            "updated_at": now,
        }
        rows.append(row)
        self._write_rows(rows)
        return row

    def update_word(self, word_id: str, changes: dict[str, str]) -> dict[str, str]:
        rows = self._read_rows()
        allowed = {"phonetic", "part_of_speech", "chinese_meaning", "example", "source"}
        for row in rows:
            if row["id"] == word_id:
                for key, value in changes.items():
                    if key in allowed:
                        row[key] = value.strip()
                row["updated_at"] = utc_now_iso()
                self._write_rows(rows)
                return row
        raise KeyError(f"Word id not found: {word_id}")

    def update_status(self, word_id: str, status: str) -> dict[str, str]:
        if status not in VALID_STATUSES:
            raise ValueError("Invalid status.")
        rows = self._read_rows()
        for row in rows:
            if row["id"] == word_id:
                row["status"] = status
                row["updated_at"] = utc_now_iso()
                self._write_rows(rows)
                return row
        raise KeyError(f"Word id not found: {word_id}")

    def delete_word(self, word_id: str) -> bool:
        rows = self._read_rows()
        kept = [row for row in rows if row["id"] != word_id]
        if len(kept) == len(rows):
            return False
        self._write_rows(kept)
        return True

    def search(self, unit: int | str | None, query: str, all_units: bool = False) -> list[dict[str, str]]:
        normalized_query = query.strip().lower()
        rows = self.list_words(None if all_units else unit)
        if not normalized_query:
            return rows
        return [
            row
            for row in rows
            if normalized_query in row["word"].lower()
            or normalized_query in row["chinese_meaning"].lower()
            or normalized_query in row["part_of_speech"].lower()
        ]

    def import_csv(self, import_path: str | Path) -> dict[str, int]:
        imported = 0
        skipped = 0
        existing = self._read_rows()
        keys = {(row["unit"], row["word"]) for row in existing}
        ids = {row["id"] for row in existing if row["id"]}

        with Path(import_path).open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != CSV_FIELDS:
                raise ValueError(
                    f"CSV header mismatch in {import_path}. Expected {CSV_FIELDS}, got {reader.fieldnames}."
                )

            for row in reader:
                if None in row or any(row.get(field) is None for field in CSV_FIELDS):
                    skipped += 1
                    continue

                try:
                    selected_unit = str(validate_unit(row.get("unit", "")))
                    normalized_word = normalize_word(row.get("word", ""))
                except (ValueError, InvalidWordError):
                    skipped += 1
                    continue

                row_id = row.get("id", "").strip()
                if row_id and row_id in ids:
                    skipped += 1
                    continue

                key = (selected_unit, normalized_word)
                if key in keys:
                    skipped += 1
                    continue

                status = row.get("status", "new").strip()
                if status not in VALID_STATUSES:
                    skipped += 1
                    continue

                now = utc_now_iso()
                next_id = row_id or str(uuid.uuid4())
                existing.append(
                    {
                        "id": next_id,
                        "unit": selected_unit,
                        "word": normalized_word,
                        "phonetic": row.get("phonetic", "").strip(),
                        "part_of_speech": row.get("part_of_speech", "").strip(),
                        "chinese_meaning": row.get("chinese_meaning", "").strip(),
                        "example": row.get("example", "").strip(),
                        "source": row.get("source", "manual").strip() or "manual",
                        "status": status,
                        "created_at": row.get("created_at") or now,
                        "updated_at": row.get("updated_at") or now,
                    }
                )
                keys.add(key)
                ids.add(next_id)
                imported += 1

        self._write_rows(existing)
        return {"imported": imported, "skipped": skipped}
