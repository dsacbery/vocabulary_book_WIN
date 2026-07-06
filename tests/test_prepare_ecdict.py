import sqlite3

from scripts.prepare_ecdict import build_sqlite


def test_build_sqlite_closes_temp_database_before_replace(tmp_path):
    csv_path = tmp_path / "ecdict.csv"
    db_path = tmp_path / "ecdict.db"
    csv_path.write_text(
        "\n".join(
            [
                "word,phonetic,definition,translation,pos,collins,oxford,tag,bnc,frq,exchange,detail,audio",
                "benefit,'benifit,something that helps,n. 利益；好处,n,,,,0,0,,,",
            ]
        ),
        encoding="utf-8",
    )

    count = build_sqlite(csv_path, db_path)

    assert count == 1
    assert db_path.exists()
    assert not db_path.with_suffix(".tmp.db").exists()

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT word, sw, translation FROM stardict WHERE word = ?",
            ("benefit",),
        ).fetchone()

    assert row == ("benefit", "benefit", "n. 利益；好处")
