import io

from app import create_app
from services.dictionary import DictionaryEntry
from services.wordbook import CSV_FIELDS


class FakeDictionary:
    def lookup(self, word):
        return DictionaryEntry(
            word=word,
            phonetic="/test/",
            part_of_speech="noun",
            chinese_meaning="测试",
            example="test example",
            source="manual",
        )


def make_client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATA_PATH": tmp_path / "words.csv",
            "DICTIONARY_SERVICE": FakeDictionary(),
        }
    )
    return app.test_client()


def create_word(client):
    return client.post(
        "/api/words",
        json={
            "unit": 1,
            "word": "benefit",
            "phonetic": "",
            "part_of_speech": "noun",
            "chinese_meaning": "好处",
            "example": "public benefit",
            "source": "manual",
        },
    ).get_json()["word"]


def test_index_route_returns_html(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert b"Vocabulary" in response.data


def test_index_route_includes_quiz_mode_controls(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert b'id="mode-study"' in response.data
    assert b'id="mode-quiz"' in response.data
    assert b'id="quiz-panel"' in response.data
    assert b'id="quiz-answer"' in response.data
    assert b'id="quiz-submit"' in response.data


def test_lookup_add_list_and_duplicate_flow(tmp_path):
    client = make_client(tmp_path)

    lookup = client.post("/api/lookup", json={"word": "Test"})
    assert lookup.status_code == 200
    assert lookup.get_json()["entry"]["chinese_meaning"] == "测试"

    created = client.post(
        "/api/words",
        json={
            "unit": 1,
            "word": "Test",
            "phonetic": "/test/",
            "part_of_speech": "noun",
            "chinese_meaning": "测试",
            "example": "test example",
            "source": "manual",
        },
    )
    assert created.status_code == 201
    assert created.get_json()["word"]["word"] == "test"

    duplicate = client.post(
        "/api/words",
        json={
            "unit": 1,
            "word": "test",
            "phonetic": "",
            "part_of_speech": "",
            "chinese_meaning": "",
            "example": "",
            "source": "manual",
        },
    )
    assert duplicate.status_code == 409

    listed = client.get("/api/words?unit=1")
    assert listed.status_code == 200
    assert len(listed.get_json()["words"]) == 1


def test_lookup_rejects_non_string_word(tmp_path):
    client = make_client(tmp_path)

    response = client.post("/api/lookup", json={"word": 123})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_add_word_rejects_non_string_field(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/words",
        json={
            "unit": 1,
            "word": "valid",
            "phonetic": None,
            "part_of_speech": "noun",
            "chinese_meaning": "有效",
            "example": "valid example",
            "source": "manual",
        },
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_update_status_delete_and_search(tmp_path):
    client = make_client(tmp_path)
    created = create_word(client)

    status_response = client.patch(f"/api/words/{created['id']}/status", json={"status": "known"})
    assert status_response.status_code == 200
    assert status_response.get_json()["word"]["status"] == "known"

    search_response = client.get("/api/words?unit=1&q=ben")
    assert search_response.status_code == 200
    assert search_response.get_json()["words"][0]["word"] == "benefit"

    delete_response = client.delete(f"/api/words/{created['id']}")
    assert delete_response.status_code == 200
    assert delete_response.get_json()["deleted"] is True


def test_update_word_rejects_non_string_field(tmp_path):
    client = make_client(tmp_path)
    created = create_word(client)

    response = client.patch(f"/api/words/{created['id']}", json={"example": None})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_update_status_rejects_json_array_without_resetting_status(tmp_path):
    client = make_client(tmp_path)
    created = create_word(client)
    known = client.patch(f"/api/words/{created['id']}/status", json={"status": "known"})
    assert known.status_code == 200

    response = client.patch(f"/api/words/{created['id']}/status", json=[])

    assert response.status_code == 400
    listed = client.get("/api/words?unit=1")
    assert listed.get_json()["words"][0]["status"] == "known"


def test_update_status_rejects_missing_status(tmp_path):
    client = make_client(tmp_path)
    created = create_word(client)

    response = client.patch(f"/api/words/{created['id']}/status", json={})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_update_status_rejects_non_string_status(tmp_path):
    client = make_client(tmp_path)
    created = create_word(client)

    response = client.patch(f"/api/words/{created['id']}/status", json={"status": 123})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_export_returns_csv_attachment_with_header(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/export")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]
    assert ",".join(CSV_FIELDS).encode() in response.data


def test_export_recreates_missing_csv(tmp_path):
    data_path = tmp_path / "words.csv"
    client = make_client(tmp_path)
    data_path.unlink()

    response = client.get("/api/export")

    assert response.status_code == 200
    assert ",".join(CSV_FIELDS).encode() in response.data
    assert data_path.exists()


def test_import_without_file_returns_400(tmp_path):
    client = make_client(tmp_path)

    response = client.post("/api/import", data={})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_import_with_malformed_csv_header_returns_400_json(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/import",
        data={"file": (io.BytesIO(b"wrong,header\n1,2\n"), "words.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_import_rejects_sanitized_empty_upload_filename(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/import",
        data={"file": (io.BytesIO(b"id,unit\n"), "...")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_delete_unknown_id_returns_false(tmp_path):
    client = make_client(tmp_path)

    response = client.delete("/api/words/missing-id")

    assert response.status_code == 200
    assert response.get_json()["deleted"] is False
