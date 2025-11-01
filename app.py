"""Flask front-end for the image metadata analyzer."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, render_template, request
from flask.typing import ResponseReturnValue
from werkzeug.utils import secure_filename

from analyze_upload import analyze_image, validate_extension


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.post("/analyze")
    def analyze() -> ResponseReturnValue:
        file = request.files.get("image")
        if file is None or file.filename == "":
            return jsonify({"error": "No image file provided."}), 400

        filename = secure_filename(file.filename)
        extension = Path(filename).suffix
        try:
            # Reuse CLI validation logic (suffix check only cares about extension).
            validate_extension(Path(filename))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        temp_path: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
                file.save(tmp)
                temp_path = Path(tmp.name)

            result = analyze_image(temp_path)
        except (FileNotFoundError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

        result["file"] = filename
        return jsonify(result)

    return app


app = create_app()
