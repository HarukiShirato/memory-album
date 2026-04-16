#!/usr/bin/env python3
"""
Build a local photo album package:
1) scan photos from input directory
2) extract capture time from EXIF (fallback to file mtime)
3) copy and rename photos into organized folders
4) export metadata as CSV + JSON
5) generate a PDF album
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

EXIF_DATETIME_ORIGINAL = 36867
EXIF_DATETIME = 306
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


@dataclass
class PhotoRecord:
    original_path: str
    organized_path: str
    original_name: str
    renamed_name: str
    capture_time: str
    time_source: str
    year: int
    month: int
    day: int
    size_bytes: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Organize photos and generate a PDF album.")
    parser.add_argument(
        "--input",
        default="data/photos_raw",
        help="Input directory containing original photos.",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Output base directory.",
    )
    parser.add_argument(
        "--title",
        default="My Memory Album",
        help="Title printed in the PDF album.",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=4,
        choices=[1, 2, 4, 6],
        help="Photo count per PDF page.",
    )
    return parser.parse_args()


def discover_images(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        return []
    files = [
        p
        for p in input_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    files.sort(key=lambda p: str(p).lower())
    return files


def parse_exif_datetime(text: str) -> Optional[datetime]:
    # EXIF datetime format: YYYY:MM:DD HH:MM:SS
    try:
        return datetime.strptime(text, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def extract_capture_time(path: Path) -> tuple[datetime, str]:
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if exif:
                dt_original = exif.get(EXIF_DATETIME_ORIGINAL)
                if isinstance(dt_original, str):
                    parsed = parse_exif_datetime(dt_original)
                    if parsed:
                        return parsed, "exif:DateTimeOriginal"
                dt = exif.get(EXIF_DATETIME)
                if isinstance(dt, str):
                    parsed = parse_exif_datetime(dt)
                    if parsed:
                        return parsed, "exif:DateTime"
    except Exception:
        pass

    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts), "file:mtime"


def ensure_dirs(base_output: Path) -> dict[str, Path]:
    organized_dir = base_output / "organized"
    metadata_dir = base_output / "metadata"
    pdf_dir = base_output / "pdf"

    organized_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    return {
        "organized": organized_dir,
        "metadata": metadata_dir,
        "pdf": pdf_dir,
    }


def copy_and_organize(files: list[Path], organized_dir: Path) -> list[PhotoRecord]:
    items: list[tuple[Path, datetime, str]] = []
    for file_path in files:
        capture_dt, time_source = extract_capture_time(file_path)
        items.append((file_path, capture_dt, time_source))

    items.sort(key=lambda x: (x[1], x[0].name.lower()))
    records: list[PhotoRecord] = []
    collision_counter: dict[str, int] = {}

    for src, capture_dt, time_source in items:
        year_folder = organized_dir / f"{capture_dt.year:04d}" / f"{capture_dt.month:02d}"
        year_folder.mkdir(parents=True, exist_ok=True)

        base_name = capture_dt.strftime("%Y%m%d_%H%M%S")
        key = f"{year_folder}|{base_name}"
        collision_counter[key] = collision_counter.get(key, 0) + 1
        index = collision_counter[key]

        new_name = f"{base_name}_{index:03d}{src.suffix.lower()}"
        dst = year_folder / new_name

        # Keep source files untouched: copy bytes to organized directory.
        dst.write_bytes(src.read_bytes())

        records.append(
            PhotoRecord(
                original_path=str(src.resolve()),
                organized_path=str(dst.resolve()),
                original_name=src.name,
                renamed_name=new_name,
                capture_time=capture_dt.isoformat(timespec="seconds"),
                time_source=time_source,
                year=capture_dt.year,
                month=capture_dt.month,
                day=capture_dt.day,
                size_bytes=dst.stat().st_size,
            )
        )

    return records


def export_metadata(records: Iterable[PhotoRecord], metadata_dir: Path) -> tuple[Path, Path]:
    csv_path = metadata_dir / "metadata.csv"
    json_path = metadata_dir / "metadata.json"
    rows = [asdict(r) for r in records]

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(PhotoRecord.__annotations__.keys()))
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    return csv_path, json_path


def page_grid(per_page: int) -> tuple[int, int]:
    if per_page == 1:
        return 1, 1
    if per_page == 2:
        return 1, 2
    if per_page == 4:
        return 2, 2
    return 3, 2


def draw_cover(pdf: canvas.Canvas, title: str, total: int, built_at: str, page_w: float, page_h: float) -> None:
    pdf.setFont("Helvetica-Bold", 32)
    pdf.drawString(72, page_h - 150, title)
    pdf.setFont("Helvetica", 14)
    pdf.drawString(72, page_h - 190, f"Total photos: {total}")
    pdf.drawString(72, page_h - 215, f"Built at: {built_at}")
    pdf.drawString(72, page_h - 240, "Generated by scripts/build_album.py")
    pdf.showPage()


def draw_photo(
    pdf: canvas.Canvas,
    record: PhotoRecord,
    x: float,
    y: float,
    w: float,
    h: float,
) -> None:
    caption_h = 24
    image_h = h - caption_h

    try:
        with Image.open(record.organized_path) as src_img:
            img = ImageOps.exif_transpose(src_img).convert("RGB")
            img.thumbnail((int(w), int(image_h)))
            img_reader = ImageReader(img)

            draw_w = img.width
            draw_h = img.height
            draw_x = x + (w - draw_w) / 2
            draw_y = y + caption_h + (image_h - draw_h) / 2
            pdf.drawImage(img_reader, draw_x, draw_y, width=draw_w, height=draw_h, preserveAspectRatio=True, anchor="c")
    except Exception:
        pdf.rect(x + 8, y + caption_h + 8, w - 16, image_h - 16)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(x + 16, y + caption_h + image_h / 2, "Failed to render image")

    pdf.setFont("Helvetica", 9)
    label = f"{record.capture_time[:10]}  {record.renamed_name}"
    pdf.drawString(x + 4, y + 8, label[:100])


def generate_pdf(records: list[PhotoRecord], pdf_path: Path, title: str, per_page: int) -> None:
    page_w, page_h = A4
    pdf = canvas.Canvas(str(pdf_path), pagesize=A4)

    built_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    draw_cover(pdf, title, len(records), built_at, page_w, page_h)

    if not records:
        pdf.setFont("Helvetica", 14)
        pdf.drawString(72, page_h - 120, "No images found in input directory.")
        pdf.save()
        return

    cols, rows = page_grid(per_page)
    margin_x = 42
    margin_y = 42
    gap_x = 12
    gap_y = 16
    cell_w = (page_w - 2 * margin_x - (cols - 1) * gap_x) / cols
    cell_h = (page_h - 2 * margin_y - (rows - 1) * gap_y) / rows

    for i, record in enumerate(records):
        idx = i % per_page
        row = idx // cols
        col = idx % cols

        x = margin_x + col * (cell_w + gap_x)
        y = page_h - margin_y - (row + 1) * cell_h - row * gap_y
        draw_photo(pdf, record, x, y, cell_w, cell_h)

        if idx == per_page - 1 or i == len(records) - 1:
            pdf.showPage()

    pdf.save()


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()
    dirs = ensure_dirs(output_dir)

    files = discover_images(input_dir)
    records = copy_and_organize(files, dirs["organized"]) if files else []
    csv_path, json_path = export_metadata(records, dirs["metadata"])

    pdf_path = dirs["pdf"] / "album.pdf"
    generate_pdf(records, pdf_path, args.title, args.per_page)

    print(f"Input directory: {input_dir}")
    print(f"Found photos: {len(files)}")
    print(f"Organized photos: {len(records)}")
    print(f"Metadata CSV: {csv_path}")
    print(f"Metadata JSON: {json_path}")
    print(f"Album PDF: {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
