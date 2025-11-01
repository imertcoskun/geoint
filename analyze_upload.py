"""Image upload validation and metadata analysis utility.

This script validates that an uploaded file is a supported image type and
extracts metadata, including EXIF GPS information when present, to summarize
its contents.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

from PIL import ExifTags, Image, UnidentifiedImageError

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def validate_extension(path: Path) -> None:
    """Ensure the file extension is one of the supported image formats."""
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(
            f"Unsupported file type '{path.suffix}'. Allowed extensions: {allowed}."
        )


def _decode_rational(rational: Iterable[Any]) -> float:
    """Convert EXIF rational tuples to a decimal value."""
    values = []
    for item in rational:
        if isinstance(item, tuple) and len(item) == 2:
            num, den = item
            values.append(num / den if den else 0)
        else:
            values.append(float(item))
    return sum(val / (60 ** idx) for idx, val in enumerate(values))


def _convert_gps_tags(gps_tags: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """Convert raw EXIF GPS tags to decimal latitude/longitude."""
    try:
        lat = _decode_rational(gps_tags["GPSLatitude"])
        lat_ref = gps_tags["GPSLatitudeRef"]
        lon = _decode_rational(gps_tags["GPSLongitude"])
        lon_ref = gps_tags["GPSLongitudeRef"]
    except KeyError:
        return None

    if isinstance(lat_ref, bytes):
        lat_ref = lat_ref.decode(errors="ignore")
    if isinstance(lon_ref, bytes):
        lon_ref = lon_ref.decode(errors="ignore")

    if lat_ref.upper().startswith("S"):
        lat *= -1
    if lon_ref.upper().startswith("W"):
        lon *= -1

    return lat, lon


def extract_metadata(path: Path) -> Dict[str, Any]:
    """Load the image and extract general and EXIF metadata."""
    try:
        with Image.open(path) as img:
            image_format = (img.format or "").upper()
            if image_format not in {"PNG", "JPEG"}:
                allowed = ", ".join(sorted(ext.upper() for ext in ALLOWED_EXTENSIONS))
                raise ValueError(
                    "File signature indicates unsupported format "
                    f"'{image_format}'. Allowed formats: {allowed}."
                )

            metadata: Dict[str, Any] = {
                "format": img.format,
                "mode": img.mode,
                "size": {"width": img.width, "height": img.height},
                "info": {},
            }

            # Basic image info (comments, ICC profiles, etc.)
            for key, value in img.info.items():
                if isinstance(value, bytes):
                    try:
                        metadata["info"][key] = value.decode("utf-8")
                    except UnicodeDecodeError:
                        metadata["info"][key] = value.hex()
                else:
                    metadata["info"][key] = value

            # EXIF data (including GPS tags)
            exif_raw = img.getexif()
            if exif_raw:
                exif: Dict[str, Any] = {}
                gps_data: Dict[str, Any] = {}
                for tag_id, value in exif_raw.items():
                    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag_name == "GPSInfo":
                        for gps_key, gps_value in value.items():
                            gps_tag = ExifTags.GPSTAGS.get(gps_key, gps_key)
                            gps_data[gps_tag] = gps_value
                    else:
                        if isinstance(value, bytes):
                            try:
                                exif[tag_name] = value.decode("utf-8")
                            except UnicodeDecodeError:
                                exif[tag_name] = value.hex()
                        else:
                            exif[tag_name] = value

                if gps_data:
                    exif["GPSInfo"] = gps_data
                    coords = _convert_gps_tags(gps_data)
                    if coords:
                        exif["GPSCoordinates"] = {
                            "latitude": coords[0],
                            "longitude": coords[1],
                        }
                if exif:
                    metadata["exif"] = exif
    except UnidentifiedImageError as exc:
        raise ValueError("File is not a valid PNG or JPEG image.") from exc

    return metadata


def summarize_analysis(metadata: Dict[str, Any]) -> str:
    """Create a human-readable summary from extracted metadata."""
    parts = []
    parts.append(
        f"Format: {metadata.get('format', 'unknown')}, mode: {metadata.get('mode', 'unknown')}, "
        f"size: {metadata.get('size', {})}"
    )

    info = metadata.get("info", {})
    if info:
        comments = [
            f"{key}: {value}"
            for key, value in info.items()
            if "comment" in key.lower() or key.lower() == "description"
        ]
        if comments:
            parts.append("Image comments/description -> " + "; ".join(comments))
        else:
            parts.append(
                "Image ancillary info -> "
                + "; ".join(f"{key}: {value}" for key, value in info.items())
            )

    exif = metadata.get("exif", {})
    if exif:
        notable_keys = [
            key
            for key in (
                "ImageDescription",
                "UserComment",
                "Artist",
                "Copyright",
                "DateTimeOriginal",
                "Make",
                "Model",
            )
            if key in exif
        ]
        for key in notable_keys:
            parts.append(f"EXIF {key}: {exif[key]}")

        gps_coords = exif.get("GPSCoordinates")
        if gps_coords:
            parts.append(
                "GPS coordinates detected -> "
                f"lat: {gps_coords['latitude']:.6f}, lon: {gps_coords['longitude']:.6f}"
            )
        elif "GPSInfo" in exif:
            parts.append("GPS metadata present but could not derive coordinates.")
    else:
        parts.append("No EXIF metadata found.")

    return "\n".join(parts)


def analyze_image(path: Path) -> Dict[str, Any]:
    """Perform validation, extract metadata, and build summary."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    validate_extension(path)
    metadata = extract_metadata(path)
    return {
        "file": str(path),
        "metadata": metadata,
        "summary": summarize_analysis(metadata),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze uploaded image metadata.")
    parser.add_argument("image_path", type=Path, help="Path to the uploaded image")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the full analysis in JSON instead of human-readable text.",
    )
    args = parser.parse_args()

    try:
        result = analyze_image(args.image_path)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
        return

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"Analysis summary for {result['file']}:")
        print(result["summary"])


if __name__ == "__main__":
    main()
