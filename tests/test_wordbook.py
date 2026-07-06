import pytest

from services.wordbook import (
    CSV_FIELDS,
    DuplicateWordError,
    InvalidWordError,
    Wordbook,
)


def test_wordbook_creates_csv_with_header(tmp_path):
    path = tmp_path / "words.csv"
    book = Wordbook(path)

    assert path.exists()
    assert path.read_text(encoding="utf-8").splitlines()[0] == ",".join(CSV_FIELDS)
    assert book.list_words(unit=1) == []


def test_add_word_normalizes_and_rejects_duplicate_in_same_unit(tmp_path):
    book = Wordbook(tmp_path / "words.csv")

    first = book.add_word(
        unit=1,
        word=" Abandon ",
        phonetic="əˈband(ə)n",
        part_of_speech="verb",
        chinese_meaning="抛弃；放弃",
        example="to abandon one's post",
        source="local_ecdict",
    )

    assert first["word"] == "abandon"
    assert first["unit"] == "1"
    assert first["status"] == "new"

    with pytest.raises(DuplicateWordError):
        book.add_word(
            unit=1,
            word="abandon",
            phonetic="",
            part_of_speech="verb",
            chinese_meaning="放弃",
            example="",
            source="manual",
        )


def test_same_word_allowed_across_different_units(tmp_path):
    book = Wordbook(tmp_path / "words.csv")
    book.add_word(1, "adapt", "", "verb", "适应", "", "manual")
    book.add_word(2, "adapt", "", "verb", "适应", "", "manual")

    assert len(book.list_words(unit=1)) == 1
    assert len(book.list_words(unit=2)) == 1


def test_invalid_unit_and_word_are_rejected(tmp_path):
    book = Wordbook(tmp_path / "words.csv")

    with pytest.raises(ValueError):
        book.add_word(21, "valid", "", "noun", "有效", "", "manual")

    with pytest.raises(InvalidWordError):
        book.add_word(1, "中文", "", "noun", "中文", "", "manual")


def test_unit_string_digits_work_but_bool_and_float_are_rejected(tmp_path):
    book = Wordbook(tmp_path / "words.csv")

    word = book.add_word("1", "valid", "", "adjective", "有效", "", "manual")
    assert word["unit"] == "1"

    with pytest.raises(ValueError):
        book.add_word(True, "truth", "", "noun", "真相", "", "manual")

    with pytest.raises(ValueError):
        book.add_word(1.9, "decimal", "", "noun", "小数", "", "manual")


def test_update_delete_search_and_status(tmp_path):
    book = Wordbook(tmp_path / "words.csv")
    word = book.add_word(1, "analysis", "", "noun", "分析", "data analysis", "manual")

    updated = book.update_word(
        word["id"],
        {
            "chinese_meaning": "分析；解析",
            "example": "analysis of data",
        },
    )
    assert updated["chinese_meaning"] == "分析；解析"
    assert updated["example"] == "analysis of data"

    status_word = book.update_status(word["id"], "known")
    assert status_word["status"] == "known"

    with pytest.raises(ValueError):
        book.update_status(word["id"], "invalid")

    results = book.search(unit=1, query="anal")
    assert [item["word"] for item in results] == ["analysis"]

    assert book.delete_word(word["id"]) is True
    assert book.delete_word("missing-id") is False
    assert book.list_words(unit=1) == []


def test_write_rows_uses_same_directory_atomic_replace(tmp_path, monkeypatch):
    book = Wordbook(tmp_path / "words.csv")
    seen_replace = []
    original_replace = type(book.csv_path).replace

    def spy_replace(self, target):
        seen_replace.append((self.parent, target))
        return original_replace(self, target)

    monkeypatch.setattr(type(book.csv_path), "replace", spy_replace)

    book.add_word(1, "atomic", "", "adjective", "原子的", "", "manual")

    assert seen_replace
    assert seen_replace[-1] == (tmp_path, book.csv_path)


def test_import_rows_skips_duplicates_and_invalid_rows(tmp_path):
    book = Wordbook(tmp_path / "words.csv")
    import_path = tmp_path / "import.csv"
    import_path.write_text(
        "\n".join(
            [
                ",".join(CSV_FIELDS),
                "row-1,1,benefit,,noun,好处,public benefit,manual,new,2026-07-06T00:00:00,2026-07-06T00:00:00",
                "row-2,1,benefit,,noun,益处,benefit from,manual,new,2026-07-06T00:00:00,2026-07-06T00:00:00",
                "row-3,30,broken,,noun,坏的,,manual,new,2026-07-06T00:00:00,2026-07-06T00:00:00",
            ]
        ),
        encoding="utf-8",
    )

    report = book.import_csv(import_path)

    assert report == {"imported": 1, "skipped": 2}
    assert [item["word"] for item in book.list_words(unit=1)] == ["benefit"]


def test_import_csv_with_wrong_header_raises_value_error(tmp_path):
    book = Wordbook(tmp_path / "words.csv")
    import_path = tmp_path / "wrong-header.csv"
    import_path.write_text(
        "id,unit,word\nrow-1,1,brief\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        book.import_csv(import_path)


def test_import_malformed_row_with_missing_trailing_field_is_skipped(tmp_path):
    book = Wordbook(tmp_path / "words.csv")
    import_path = tmp_path / "missing-trailing-field.csv"
    import_path.write_text(
        "\n".join(
            [
                ",".join(CSV_FIELDS),
                "row-1,1,brief,,adjective,短暂的,brief note,manual,new,2026-07-06T00:00:00",
            ]
        ),
        encoding="utf-8",
    )

    report = book.import_csv(import_path)

    assert report == {"imported": 0, "skipped": 1}
    assert book.list_words(unit=1) == []


def test_import_malformed_row_with_extra_trailing_field_is_skipped(tmp_path):
    book = Wordbook(tmp_path / "words.csv")
    import_path = tmp_path / "extra-trailing-field.csv"
    import_path.write_text(
        "\n".join(
            [
                ",".join(CSV_FIELDS),
                "row-1,1,brief,,adjective,短暂的,brief note,manual,new,2026-07-06T00:00:00,2026-07-06T00:00:00,extra",
            ]
        ),
        encoding="utf-8",
    )

    report = book.import_csv(import_path)

    assert report == {"imported": 0, "skipped": 1}
    assert book.list_words(unit=1) == []


def test_import_row_with_invalid_status_is_skipped(tmp_path):
    book = Wordbook(tmp_path / "words.csv")
    import_path = tmp_path / "invalid-status.csv"
    import_path.write_text(
        "\n".join(
            [
                ",".join(CSV_FIELDS),
                "row-1,1,brief,,adjective,短暂的,brief note,manual,archived,2026-07-06T00:00:00,2026-07-06T00:00:00",
            ]
        ),
        encoding="utf-8",
    )

    report = book.import_csv(import_path)

    assert report == {"imported": 0, "skipped": 1}
    assert book.list_words(unit=1) == []


def test_import_row_with_duplicate_id_is_skipped(tmp_path):
    book = Wordbook(tmp_path / "words.csv")
    book.add_word(1, "anchor", "", "noun", "锚", "", "manual")
    existing_id = book.list_words(unit=1)[0]["id"]
    import_path = tmp_path / "duplicate-id.csv"
    import_path.write_text(
        "\n".join(
            [
                ",".join(CSV_FIELDS),
                f"{existing_id},1,brief,,adjective,短暂的,brief note,manual,new,2026-07-06T00:00:00,2026-07-06T00:00:00",
                "new-row,1,brief,,adjective,短暂的,brief note,manual,new,2026-07-06T00:00:00,2026-07-06T00:00:00",
                "new-row,2,careful,,adjective,仔细的,careful work,manual,new,2026-07-06T00:00:00,2026-07-06T00:00:00",
            ]
        ),
        encoding="utf-8",
    )

    report = book.import_csv(import_path)

    assert report == {"imported": 1, "skipped": 2}
    assert [item["word"] for item in book.list_words(unit=1)] == ["anchor", "brief"]
    assert book.list_words(unit=2) == []
