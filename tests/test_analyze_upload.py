from pathlib import Path

import pytest

pytest.importorskip("PIL")
from PIL import Image

from analyze_upload import analyze_image, summarize_analysis, validate_extension


def create_test_image(path: Path, format: str = "PNG") -> None:
    image = Image.new("RGB", (8, 6), color=(120, 45, 200))
    image.save(path, format=format)


def test_validate_extension_accepts_supported_types(tmp_path: Path) -> None:
    target = tmp_path / "sample.PNG"
    create_test_image(target, format="PNG")
    # Should not raise
    validate_extension(target)


def test_validate_extension_rejects_other_types(tmp_path: Path) -> None:
    target = tmp_path / "data.gif"
    target.write_bytes(b"GIF89a")
    with pytest.raises(ValueError):
        validate_extension(target)


def test_analyze_image_without_exif_produces_summary(tmp_path: Path) -> None:
    image_path = tmp_path / "plain.jpg"
    create_test_image(image_path, format="JPEG")

    result = analyze_image(image_path)

    assert result["file"] == str(image_path)
    assert "Format" in result["summary"]
    assert "No EXIF metadata found." in result["summary"]


def test_analyze_image_rejects_corrupted_files(tmp_path: Path) -> None:
    bogus = tmp_path / "fake.jpg"
    bogus.write_text("not really an image")

    with pytest.raises(ValueError):
        analyze_image(bogus)


@pytest.mark.parametrize(
    "metadata, expected",
    [
        (
            {
                "format": "JPEG",
                "mode": "RGB",
                "size": {"width": 8, "height": 6},
                "info": {"description": "Test image"},
                "exif": {"Make": "CameraCorp", "Model": "C1"},
            },
            "Image comments/description",
        ),
        (
            {
                "format": "PNG",
                "mode": "RGBA",
                "size": {"width": 10, "height": 10},
                "info": {},
                "exif": {},
            },
            "No EXIF metadata found.",
        ),
    ],
)
def test_summarize_analysis_handles_common_cases(metadata, expected) -> None:
    summary = summarize_analysis(metadata)
    assert expected in summary
