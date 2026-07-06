from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from services.dictionary import DictionaryService
from services.wordbook import DuplicateWordError, InvalidWordError, Wordbook


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "words.csv"
EDITABLE_WORD_FIELDS = {"phonetic", "part_of_speech", "chinese_meaning", "example", "source"}


def json_error(message: str, status: int):
    response = jsonify({"error": message})
    response.status_code = status
    return response


def json_payload() -> dict | None:
    payload = request.get_json(silent=True)
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        return None
    return payload


def get_string_field(payload: dict, field: str, default: str = "") -> str:
    value = payload.get(field, default)
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string.")
    return value


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        DATA_PATH=DEFAULT_DATA_PATH,
        DICTIONARY_SERVICE=DictionaryService(),
        UPLOAD_FOLDER=PROJECT_ROOT / "data" / "imports",
    )
    if config:
        app.config.update(config)

    data_path = Path(app.config["DATA_PATH"])
    wordbook = Wordbook(data_path)
    dictionary = app.config["DICTIONARY_SERVICE"]

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/words")
    def list_words():
        unit = request.args.get("unit", "1")
        query = request.args.get("q", "")
        all_units = request.args.get("all_units") == "1"
        try:
            words = wordbook.search(unit=unit, query=query, all_units=all_units)
        except ValueError as exc:
            return json_error(str(exc), 400)
        return jsonify({"words": words})

    @app.post("/api/lookup")
    def lookup_word():
        payload = json_payload()
        if payload is None:
            return json_error("JSON payload must be an object.", 400)
        try:
            word = get_string_field(payload, "word")
            from services.wordbook import normalize_word

            normalized = normalize_word(word)
        except (InvalidWordError, ValueError) as exc:
            return json_error(str(exc), 400)
        entry = dictionary.lookup(normalized)
        return jsonify({"entry": entry.to_dict()})

    @app.post("/api/words")
    def add_word():
        payload = json_payload()
        if payload is None:
            return json_error("JSON payload must be an object.", 400)
        try:
            word = wordbook.add_word(
                unit=payload.get("unit", 1),
                word=get_string_field(payload, "word"),
                phonetic=get_string_field(payload, "phonetic"),
                part_of_speech=get_string_field(payload, "part_of_speech"),
                chinese_meaning=get_string_field(payload, "chinese_meaning"),
                example=get_string_field(payload, "example"),
                source=get_string_field(payload, "source", "manual"),
            )
        except DuplicateWordError as exc:
            return json_error(str(exc), 409)
        except (InvalidWordError, ValueError) as exc:
            return json_error(str(exc), 400)
        return jsonify({"word": word}), 201

    @app.patch("/api/words/<word_id>")
    def update_word(word_id: str):
        payload = json_payload()
        if payload is None:
            return json_error("JSON payload must be an object.", 400)
        try:
            for field in EDITABLE_WORD_FIELDS:
                if field in payload:
                    get_string_field(payload, field)
        except ValueError as exc:
            return json_error(str(exc), 400)
        try:
            word = wordbook.update_word(word_id, payload)
        except KeyError as exc:
            return json_error(str(exc), 404)
        return jsonify({"word": word})

    @app.patch("/api/words/<word_id>/status")
    def update_status(word_id: str):
        payload = json_payload()
        if payload is None:
            return json_error("JSON payload must be an object.", 400)
        if "status" not in payload:
            return json_error("status is required.", 400)
        try:
            word = wordbook.update_status(word_id, get_string_field(payload, "status"))
        except ValueError as exc:
            return json_error(str(exc), 400)
        except KeyError as exc:
            return json_error(str(exc), 404)
        return jsonify({"word": word})

    @app.delete("/api/words/<word_id>")
    def delete_word(word_id: str):
        return jsonify({"deleted": wordbook.delete_word(word_id)})

    @app.get("/api/export")
    def export_csv():
        wordbook.ensure_csv()
        return send_file(data_path, as_attachment=True, download_name="words.csv", mimetype="text/csv")

    @app.post("/api/import")
    def import_csv():
        if "file" not in request.files:
            return json_error("No file uploaded.", 400)
        uploaded = request.files["file"]
        filename = secure_filename(uploaded.filename or "import.csv")
        if not filename:
            return json_error("Invalid upload filename.", 400)
        upload_folder = Path(app.config["UPLOAD_FOLDER"])
        upload_folder.mkdir(parents=True, exist_ok=True)
        target = upload_folder / filename
        uploaded.save(target)
        try:
            report = wordbook.import_csv(target)
        except ValueError as exc:
            return json_error(str(exc), 400)
        return jsonify(report)

    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=int(os.environ.get("VOCABULARY_PORT", "5000")))
