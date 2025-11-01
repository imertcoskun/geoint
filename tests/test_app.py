import io

import pytest

pytest.importorskip("flask")
pytest.importorskip("PIL")

from PIL import Image

from app import create_app


def create_client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def make_image_bytes(format_: str = "PNG") -> io.BytesIO:
    image = Image.new("RGB", (10, 10), color=(200, 120, 40))
    buffer = io.BytesIO()
    image.save(buffer, format=format_)
    buffer.seek(0)
    return buffer


def test_index_page_renders_upload_form():
    client = create_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"GeoINT Metadata Analyzer" in response.data


def test_analyze_endpoint_returns_metadata_for_valid_image():
    client = create_client()
    data = {"image": (make_image_bytes("JPEG"), "sample.jpg")}
    response = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["file"] == "sample.jpg"
    assert payload["metadata"]["format"] == "JPEG"


def test_analyze_endpoint_rejects_invalid_extension():
    client = create_client()
    data = {"image": (io.BytesIO(b"bogus"), "sample.gif")}
    response = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    payload = response.get_json()
    assert "Unsupported file type" in payload["error"]
