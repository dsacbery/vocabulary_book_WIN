from __future__ import annotations

import csv
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import quote

import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ECDICT_DB = PROJECT_ROOT / "data" / "ecdict.db"
DEFAULT_ECDICT_CSV = PROJECT_ROOT / "data" / "ecdict.csv"
DEFAULT_MINI_ECDICT_CSV = PROJECT_ROOT / "resources" / "mini_ecdict.csv"

ECDICT_SELECT_COLUMNS = "word, phonetic, definition, translation, pos"
WORD_STRIP_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class DictionaryEntry:
    word: str
    phonetic: str
    part_of_speech: str
    chinese_meaning: str
    example: str
    source: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _normalize_word(word: str) -> str:
    return " ".join(word.strip().lower().split())


def _strip_word(word: str) -> str:
    return WORD_STRIP_PATTERN.sub("", word.lower())


def _clean_multiline_text(text: str) -> str:
    text = text.replace("\\r\\n", "\n").replace("\\n", "\n")
    return "；".join(line.strip() for line in text.splitlines() if line.strip())


class LocalChineseDictionary:
    def __init__(
        self,
        csv_paths: list[str | Path] | None = None,
        db_path: str | Path | None = None,
    ):
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_ECDICT_DB
        if csv_paths is None:
            csv_paths = [DEFAULT_ECDICT_CSV, DEFAULT_MINI_ECDICT_CSV]
        self.csv_paths = [Path(path) for path in csv_paths]

    def lookup(self, word: str) -> DictionaryEntry | None:
        normalized = _normalize_word(word)
        if not normalized:
            return None

        entry = self._lookup_sqlite(normalized)
        if entry:
            return entry

        for csv_path in self.csv_paths:
            entry = self._lookup_csv(csv_path, normalized)
            if entry:
                return entry

        return None

    def _lookup_sqlite(self, word: str) -> DictionaryEntry | None:
        if not self.db_path.exists():
            return None

        try:
            with sqlite3.connect(self.db_path) as connection:
                connection.row_factory = sqlite3.Row
                row = connection.execute(
                    f"SELECT {ECDICT_SELECT_COLUMNS} FROM stardict WHERE lower(word) = ? LIMIT 1",
                    (word,),
                ).fetchone()
                if row is None:
                    row = connection.execute(
                        f"SELECT {ECDICT_SELECT_COLUMNS} FROM stardict WHERE sw = ? LIMIT 1",
                        (_strip_word(word),),
                    ).fetchone()
        except sqlite3.Error:
            return None

        if row is None:
            return None
        return self._entry_from_mapping(dict(row))

    def _lookup_csv(self, csv_path: Path, word: str) -> DictionaryEntry | None:
        if not csv_path.exists():
            return None

        stripped = _strip_word(word)
        try:
            with csv_path.open(newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    row_word = row.get("word", "")
                    if _normalize_word(row_word) == word or _strip_word(row_word) == stripped:
                        return self._entry_from_mapping(row)
        except (OSError, csv.Error, UnicodeDecodeError):
            return None

        return None

    @staticmethod
    def _entry_from_mapping(row: dict[str, str]) -> DictionaryEntry | None:
        translation = _clean_multiline_text(row.get("translation", ""))
        if not translation:
            return None

        word = _normalize_word(row.get("word", ""))
        if not word:
            return None

        return DictionaryEntry(
            word=word,
            phonetic=row.get("phonetic", "").strip(),
            part_of_speech=row.get("pos", "").strip(),
            chinese_meaning=translation,
            example=_clean_multiline_text(row.get("definition", "")),
            source="local_ecdict",
        )


class DictionaryService:
    def __init__(
        self,
        local_dictionary: LocalChineseDictionary | None = None,
        timeout: float = 5.0,
    ):
        self.local_dictionary = local_dictionary if local_dictionary else LocalChineseDictionary()
        self.timeout = timeout

    def lookup(self, word: str) -> DictionaryEntry:
        normalized_word = _normalize_word(word)
        if not normalized_word:
            return DictionaryEntry("", "", "", "", "", "manual")

        local_entry = self.local_dictionary.lookup(normalized_word)
        if local_entry:
            return local_entry

        free_entry = self._lookup_free_dictionary(normalized_word)
        if free_entry:
            return free_entry

        return DictionaryEntry(normalized_word, "", "", "", "", "manual")

    def _lookup_free_dictionary(self, word: str) -> DictionaryEntry | None:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(word, safe='')}"
        try:
            response = requests.get(url, timeout=self.timeout)
        except requests.RequestException:
            return None

        if response.status_code != 200:
            return None

        try:
            payload = response.json()
        except ValueError:
            return None

        if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
            return None

        entry = payload[0]
        phonetic = entry.get("phonetic") or self._first_phonetic(entry)
        meaning = self._first_meaning(entry)
        if meaning is None:
            return None

        part_of_speech = meaning.get("partOfSpeech", "")
        definition = self._first_definition(meaning)
        example = definition.get("example") or definition.get("definition", "")

        return DictionaryEntry(
            word=word,
            phonetic=phonetic,
            part_of_speech=part_of_speech,
            chinese_meaning="",
            example=example,
            source="free_dictionary_api",
        )

    @staticmethod
    def _first_phonetic(entry: dict) -> str:
        phonetics = entry.get("phonetics", [])
        if not isinstance(phonetics, list):
            return ""
        for phonetic in phonetics:
            if isinstance(phonetic, dict) and phonetic.get("text"):
                return phonetic["text"]
        return ""

    @staticmethod
    def _first_meaning(entry: dict) -> dict | None:
        meanings = entry.get("meanings", [])
        if not isinstance(meanings, list):
            return None
        for meaning in meanings:
            if isinstance(meaning, dict):
                return meaning
        return None

    @staticmethod
    def _first_definition(meaning: dict) -> dict:
        definitions = meaning.get("definitions", [])
        if not isinstance(definitions, list):
            return {}
        for definition in definitions:
            if isinstance(definition, dict):
                return definition
        return {}
