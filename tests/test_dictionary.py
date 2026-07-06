import csv
import sqlite3
from types import SimpleNamespace

import requests

from services.dictionary import DictionaryEntry, DictionaryService, LocalChineseDictionary


ECDICT_FIELDS = [
    "word",
    "phonetic",
    "definition",
    "translation",
    "pos",
    "collins",
    "oxford",
    "tag",
    "bnc",
    "frq",
    "exchange",
    "detail",
    "audio",
]


def write_ecdict_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ECDICT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in ECDICT_FIELDS})


def test_local_dictionary_reads_chinese_meaning_from_ecdict_csv(tmp_path):
    csv_path = tmp_path / "ecdict.csv"
    write_ecdict_csv(
        csv_path,
        [
            {
                "word": "benefit",
                "phonetic": "'benifit",
                "definition": "something that helps",
                "translation": "n. 利益；好处\nv. 有益于",
                "pos": "n/v",
            }
        ],
    )
    dictionary = LocalChineseDictionary(csv_paths=[csv_path], db_path=tmp_path / "missing.db")

    entry = dictionary.lookup("Benefit")

    assert entry == DictionaryEntry(
        word="benefit",
        phonetic="'benifit",
        part_of_speech="n/v",
        chinese_meaning="n. 利益；好处；v. 有益于",
        example="something that helps",
        source="local_ecdict",
    )


def test_local_dictionary_cleans_literal_backslash_newlines_from_ecdict(tmp_path):
    csv_path = tmp_path / "ecdict.csv"
    write_ecdict_csv(
        csv_path,
        [
            {
                "word": "benefit",
                "phonetic": "'benifit",
                "definition": "noun\\nverb",
                "translation": "n. 利益\\nvt. 有益于\\nvi. 受益",
                "pos": "",
            }
        ],
    )
    dictionary = LocalChineseDictionary(csv_paths=[csv_path], db_path=tmp_path / "missing.db")

    entry = dictionary.lookup("benefit")

    assert entry.chinese_meaning == "n. 利益；vt. 有益于；vi. 受益"
    assert entry.example == "noun；verb"


def test_local_dictionary_reads_chinese_meaning_from_ecdict_sqlite(tmp_path):
    db_path = tmp_path / "ecdict.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE stardict (word TEXT, sw TEXT, phonetic TEXT, definition TEXT, translation TEXT, pos TEXT)"
    )
    connection.execute(
        "INSERT INTO stardict VALUES (?, ?, ?, ?, ?, ?)",
        ("adapt", "adapt", "ə'dæpt", "to change for a new situation", "v. 适应；改编", "v"),
    )
    connection.commit()
    connection.close()
    dictionary = LocalChineseDictionary(csv_paths=[], db_path=db_path)

    entry = dictionary.lookup("adapt")

    assert entry.chinese_meaning == "v. 适应；改编"
    assert entry.part_of_speech == "v"
    assert entry.source == "local_ecdict"


def test_dictionary_service_prefers_local_chinese_dictionary(monkeypatch, tmp_path):
    csv_path = tmp_path / "mini.csv"
    write_ecdict_csv(
        csv_path,
        [
            {
                "word": "abandon",
                "phonetic": "ə'bændən",
                "definition": "to leave behind",
                "translation": "v. 抛弃；放弃",
                "pos": "v",
            }
        ],
    )
    service = DictionaryService(
        local_dictionary=LocalChineseDictionary(csv_paths=[csv_path], db_path=tmp_path / "missing.db")
    )

    def fail_online_lookup(word):
        raise AssertionError("online fallback should not run when local ECDICT has the word")

    monkeypatch.setattr(service, "_lookup_free_dictionary", fail_online_lookup)

    entry = service.lookup("abandon")

    assert entry.chinese_meaning == "v. 抛弃；放弃"
    assert entry.source == "local_ecdict"


def test_dictionary_service_falls_back_to_free_dictionary(monkeypatch, tmp_path):
    service = DictionaryService(
        local_dictionary=LocalChineseDictionary(csv_paths=[], db_path=tmp_path / "missing.db")
    )
    monkeypatch.setattr(
        service,
        "_lookup_free_dictionary",
        lambda word: DictionaryEntry(
            word=word,
            phonetic="/test/",
            part_of_speech="noun",
            chinese_meaning="",
            example="A term used in a test.",
            source="free_dictionary_api",
        ),
    )

    entry = service.lookup("missing")

    assert entry == DictionaryEntry(
        word="missing",
        phonetic="/test/",
        part_of_speech="noun",
        chinese_meaning="",
        example="A term used in a test.",
        source="free_dictionary_api",
    )


def test_dictionary_service_returns_manual_entry_when_all_sources_fail(monkeypatch, tmp_path):
    service = DictionaryService(
        local_dictionary=LocalChineseDictionary(csv_paths=[], db_path=tmp_path / "missing.db")
    )
    monkeypatch.setattr(service, "_lookup_free_dictionary", lambda word: None)

    entry = service.lookup("unknownword")

    assert entry == DictionaryEntry("unknownword", "", "", "", "", "manual")


def test_lookup_empty_word_returns_manual_entry_without_sources(monkeypatch, tmp_path):
    service = DictionaryService(
        local_dictionary=LocalChineseDictionary(csv_paths=[], db_path=tmp_path / "missing.db")
    )

    def fail_lookup(word):
        raise AssertionError(f"lookup source should not be called for {word!r}")

    monkeypatch.setattr(service.local_dictionary, "lookup", fail_lookup)
    monkeypatch.setattr(service, "_lookup_free_dictionary", fail_lookup)

    entry = service.lookup("   ")

    assert entry == DictionaryEntry("", "", "", "", "", "manual")


def test_lookup_free_dictionary_success_encodes_slash_and_passes_timeout(monkeypatch, tmp_path):
    service = DictionaryService(
        local_dictionary=LocalChineseDictionary(csv_paths=[], db_path=tmp_path / "missing.db"),
        timeout=2.5,
    )
    calls = []

    class Response:
        status_code = 200

        def json(self):
            return [
                {
                    "phonetics": [{"text": "/teks/"}],
                    "meanings": [
                        {
                            "partOfSpeech": "noun",
                            "definitions": [
                                {
                                    "definition": "A term used in a test.",
                                    "example": "Use a term in context.",
                                }
                            ],
                        }
                    ],
                }
            ]

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return Response()

    monkeypatch.setattr("services.dictionary.requests.get", fake_get)

    entry = service._lookup_free_dictionary("term/with slash")

    assert calls == [
        ("https://api.dictionaryapi.dev/api/v2/entries/en/term%2Fwith%20slash", 2.5)
    ]
    assert entry == DictionaryEntry(
        word="term/with slash",
        phonetic="/teks/",
        part_of_speech="noun",
        chinese_meaning="",
        example="Use a term in context.",
        source="free_dictionary_api",
    )


def test_lookup_free_dictionary_network_exception_returns_none(monkeypatch, tmp_path):
    service = DictionaryService(
        local_dictionary=LocalChineseDictionary(csv_paths=[], db_path=tmp_path / "missing.db")
    )

    def raise_timeout(url, timeout):
        raise requests.Timeout("network unavailable")

    monkeypatch.setattr("services.dictionary.requests.get", raise_timeout)

    assert service._lookup_free_dictionary("benefit") is None


def test_lookup_free_dictionary_non_200_returns_none(monkeypatch, tmp_path):
    service = DictionaryService(
        local_dictionary=LocalChineseDictionary(csv_paths=[], db_path=tmp_path / "missing.db")
    )

    monkeypatch.setattr(
        "services.dictionary.requests.get",
        lambda url, timeout: SimpleNamespace(status_code=404),
    )

    assert service._lookup_free_dictionary("missing") is None


def test_lookup_free_dictionary_malformed_json_returns_none(monkeypatch, tmp_path):
    service = DictionaryService(
        local_dictionary=LocalChineseDictionary(csv_paths=[], db_path=tmp_path / "missing.db")
    )

    class Response:
        status_code = 200

        def json(self):
            raise ValueError("bad json")

    monkeypatch.setattr("services.dictionary.requests.get", lambda url, timeout: Response())

    assert service._lookup_free_dictionary("broken") is None
