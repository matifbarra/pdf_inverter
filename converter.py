from __future__ import annotations

import io
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from PIL import Image


DEFAULT_SETTINGS = {
    "mode": "smart",
    "dpi": 450,
    "bg_value_threshold": 60,
    "light_value_threshold": 205,
    "neutral_color_threshold": 20,
    "bw_threshold": 150,
    "jpeg_quality": 85,
}


def suggested_output_name(input_name: str, mode: str) -> str:
    source = Path(input_name)
    suffix = "_bw" if mode == "bw" else "_print"
    return f"{source.stem}{suffix}.pdf"


def selective_invert(
    img: Image.Image,
    bg_value_threshold: int = 60,
    light_value_threshold: int = 205,
    neutral_color_threshold: int = 20,
    mode: str = "smart",
    bw_threshold: int = 150,
) -> Image.Image:
    rgb = np.asarray(img.convert("RGB"), dtype=np.uint8)

    r = rgb[:, :, 0].astype(np.float32)
    g = rgb[:, :, 1].astype(np.float32)
    b = rgb[:, :, 2].astype(np.float32)

    luminance = (0.2126 * r) + (0.7152 * g) + (0.0722 * b)
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    channel_range = maxc - minc

    neutral = channel_range <= neutral_color_threshold
    dark_neutral = neutral & (luminance <= bg_value_threshold)
    light_neutral = neutral & (luminance >= light_value_threshold)

    inverted = 255 - rgb
    out = rgb.copy()
    out[neutral] = inverted[neutral]

    if mode == "smart":
        out[dark_neutral] = [255, 255, 255]
        out[light_neutral] = [0, 0, 0]
        return Image.fromarray(out)

    if mode == "bw":
        inverted_luminance = 255.0 - luminance
        bw = np.where(neutral & (inverted_luminance <= bw_threshold), 0, 255).astype(np.uint8)
        return Image.fromarray(bw, mode="L").convert("1", dither=Image.Dither.NONE)

    raise ValueError(f"Unsupported mode: {mode}")


def process_pdf_bytes(
    pdf_bytes: bytes,
    dpi: int,
    bg_value_threshold: int,
    light_value_threshold: int,
    neutral_color_threshold: int,
    mode: str,
    bw_threshold: int,
    jpeg_quality: int,
) -> bytes:
    src_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    out_doc = fitz.open()

    try:
        scale = dpi / 72.0
        matrix = fitz.Matrix(scale, scale)

        for page_index in range(len(src_doc)):
            page = src_doc.load_page(page_index)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            processed = selective_invert(
                img,
                bg_value_threshold=bg_value_threshold,
                light_value_threshold=light_value_threshold,
                neutral_color_threshold=neutral_color_threshold,
                mode=mode,
                bw_threshold=bw_threshold,
            )

            width_points = processed.width * 72.0 / dpi
            height_points = processed.height * 72.0 / dpi
            out_page = out_doc.new_page(width=width_points, height=height_points)

            with io.BytesIO() as buffer:
                img_to_save = processed.convert("RGB") if processed.mode != "RGB" else processed
                img_to_save.save(buffer, format="JPEG", quality=jpeg_quality, optimize=True)
                out_page.insert_image(out_page.rect, stream=buffer.getvalue())

        return out_doc.tobytes(deflate=True, garbage=4)
    finally:
        out_doc.close()
        src_doc.close()


def preview_first_page(
    pdf_bytes: bytes,
    dpi: int,
    bg_value_threshold: int,
    light_value_threshold: int,
    neutral_color_threshold: int,
    mode: str,
    bw_threshold: int,
) -> Image.Image:
    src_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if len(src_doc) == 0:
            raise ValueError("The PDF does not contain any pages.")

        preview_dpi = min(dpi, 140)
        scale = preview_dpi / 72.0
        matrix = fitz.Matrix(scale, scale)

        page = src_doc.load_page(0)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        processed = selective_invert(
            img,
            bg_value_threshold=bg_value_threshold,
            light_value_threshold=light_value_threshold,
            neutral_color_threshold=neutral_color_threshold,
            mode=mode,
            bw_threshold=bw_threshold,
        )

        preview = processed.copy()
        preview.thumbnail((1100, 1400), Image.Resampling.LANCZOS)
        return preview
    finally:
        src_doc.close()