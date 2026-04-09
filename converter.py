from __future__ import annotations

import io
import math
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
    "preserve_images": True,
    "page_selection": "",
}


def _parse_page_selection(total_pages: int, page_selection: str | None) -> list[int]:
    if total_pages <= 0:
        return []

    if page_selection is None or not page_selection.strip():
        return list(range(total_pages))

    selected: list[int] = []
    seen: set[int] = set()

    tokens = [chunk.strip() for chunk in page_selection.split(",") if chunk.strip()]
    if not tokens:
        raise ValueError("Page selection is empty. Use values like 1-3,5,8.")

    for token in tokens:
        if "-" in token:
            parts = token.split("-", 1)
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                raise ValueError(f"Invalid range '{token}'. Use format like 2-6.")

            try:
                start_page = int(parts[0].strip())
                end_page = int(parts[1].strip())
            except ValueError as exc:
                raise ValueError(f"Invalid range '{token}'. Use numbers only.") from exc

            if start_page > end_page:
                raise ValueError(f"Invalid range '{token}'. Start must be <= end.")
            if start_page < 1 or end_page > total_pages:
                raise ValueError(f"Page range '{token}' is outside 1-{total_pages}.")

            for page_number in range(start_page, end_page + 1):
                page_index = page_number - 1
                if page_index not in seen:
                    seen.add(page_index)
                    selected.append(page_index)
            continue

        try:
            page_number = int(token)
        except ValueError as exc:
            raise ValueError(f"Invalid page '{token}'. Use numbers and ranges like 1-3,5.") from exc

        if page_number < 1 or page_number > total_pages:
            raise ValueError(f"Page '{token}' is outside 1-{total_pages}.")

        page_index = page_number - 1
        if page_index not in seen:
            seen.add(page_index)
            selected.append(page_index)

    if not selected:
        raise ValueError("No valid pages selected.")

    return selected


def suggested_output_name(input_name: str, mode: str) -> str:
    source = Path(input_name)
    suffix = "_bw" if mode == "bw" else "_print"
    return f"{source.stem}{suffix}.pdf"


def _dilate_mask(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    expanded = mask.astype(bool)
    for _ in range(max(0, iterations)):
        padded = np.pad(expanded, 1, mode="constant", constant_values=False)
        expanded = (
            padded[1:-1, 1:-1]
            | padded[:-2, 1:-1]
            | padded[2:, 1:-1]
            | padded[1:-1, :-2]
            | padded[1:-1, 2:]
            | padded[:-2, :-2]
            | padded[:-2, 2:]
            | padded[2:, :-2]
            | padded[2:, 2:]
        )
    return expanded


def selective_invert(
    img: Image.Image,
    bg_value_threshold: int = 60,
    light_value_threshold: int = 205,
    neutral_color_threshold: int = 20,
    mode: str = "smart",
    bw_threshold: int = 150,
    preserve_mask: np.ndarray | None = None,
) -> Image.Image:
    rgb = np.asarray(img.convert("RGB"), dtype=np.uint8)

    r = rgb[:, :, 0].astype(np.float32)
    g = rgb[:, :, 1].astype(np.float32)
    b = rgb[:, :, 2].astype(np.float32)

    luminance = (0.2126 * r) + (0.7152 * g) + (0.0722 * b)
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    channel_range = maxc - minc
    saturation = channel_range / np.maximum(maxc, 1.0)

    neutral = channel_range <= neutral_color_threshold
    dark_neutral = neutral & (luminance <= bg_value_threshold)
    light_neutral = neutral & (luminance >= light_value_threshold)

    # Detect dark colored highlight blobs and include nearby strokes so background and
    # letters are transformed together.
    dark_colored = (saturation >= 0.10) & (luminance <= 140.0)
    highlight_region = _dilate_mask(dark_colored, iterations=2)
    colored_region = highlight_region & (saturation >= 0.06) & (channel_range >= 6.0)

    inverted = 255 - rgb
    out = rgb.copy()
    out[neutral] = inverted[neutral]
    out[colored_region] = inverted[colored_region]

    if mode == "smart":
        out[dark_neutral] = [255, 255, 255]
        out[light_neutral] = [0, 0, 0]

        # Slightly lift inverted dark fills so they print closer to white paper.
        lift = np.clip(0.12 + ((140.0 - luminance) / 140.0) * 0.28, 0.0, 0.35)
        out_float = out.astype(np.float32)
        for channel_index in range(3):
            channel = out_float[:, :, channel_index]
            channel[dark_colored] = channel[dark_colored] + (255.0 - channel[dark_colored]) * lift[dark_colored]
        out = np.clip(out_float, 0.0, 255.0).astype(np.uint8)

        if preserve_mask is not None:
            out[preserve_mask] = rgb[preserve_mask]
        return Image.fromarray(out)

    if mode == "bw":
        inverted_luminance = 255.0 - luminance
        bw = np.where(neutral & (inverted_luminance <= bw_threshold), 0, 255).astype(np.uint8)
        bw_rgb = np.stack([bw, bw, bw], axis=-1)
        if preserve_mask is not None:
            bw_rgb[preserve_mask] = rgb[preserve_mask]
        return Image.fromarray(bw_rgb, mode="RGB")

    raise ValueError(f"Unsupported mode: {mode}")


def _image_mask_from_page(page: fitz.Page, pix_width: int, pix_height: int) -> np.ndarray:
    mask = np.zeros((pix_height, pix_width), dtype=bool)
    page_rect = page.rect

    if page_rect.width <= 0 or page_rect.height <= 0:
        return mask

    scale_x = pix_width / float(page_rect.width)
    scale_y = pix_height / float(page_rect.height)

    page_dict = page.get_text("dict")
    for block in page_dict.get("blocks", []):
        if block.get("type") != 1:
            continue

        bbox = block.get("bbox")
        if not bbox or len(bbox) != 4:
            continue

        x0, y0, x1, y1 = bbox
        left = max(0, min(pix_width, int(math.floor(x0 * scale_x))))
        top = max(0, min(pix_height, int(math.floor(y0 * scale_y))))
        right = max(0, min(pix_width, int(math.ceil(x1 * scale_x))))
        bottom = max(0, min(pix_height, int(math.ceil(y1 * scale_y))))

        if right > left and bottom > top:
            mask[top:bottom, left:right] = True

    return mask


def process_pdf_bytes(
    pdf_bytes: bytes,
    dpi: int,
    bg_value_threshold: int,
    light_value_threshold: int,
    neutral_color_threshold: int,
    mode: str,
    bw_threshold: int,
    jpeg_quality: int,
    preserve_images: bool = True,
    page_selection: str | None = None,
) -> bytes:
    src_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    out_doc = fitz.open()

    try:
        scale = dpi / 72.0
        matrix = fitz.Matrix(scale, scale)
        selected_pages = _parse_page_selection(len(src_doc), page_selection)

        for page_index in selected_pages:
            page = src_doc.load_page(page_index)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            preserve_mask = _image_mask_from_page(page, pix.width, pix.height) if preserve_images else None

            processed = selective_invert(
                img,
                bg_value_threshold=bg_value_threshold,
                light_value_threshold=light_value_threshold,
                neutral_color_threshold=neutral_color_threshold,
                mode=mode,
                bw_threshold=bw_threshold,
                preserve_mask=preserve_mask,
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
    preserve_images: bool = True,
    page_selection: str | None = None,
) -> Image.Image:
    src_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if len(src_doc) == 0:
            raise ValueError("The PDF does not contain any pages.")

        preview_dpi = min(dpi, 140)
        scale = preview_dpi / 72.0
        matrix = fitz.Matrix(scale, scale)
        selected_pages = _parse_page_selection(len(src_doc), page_selection)
        first_page_index = selected_pages[0]

        page = src_doc.load_page(first_page_index)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        preserve_mask = _image_mask_from_page(page, pix.width, pix.height) if preserve_images else None

        processed = selective_invert(
            img,
            bg_value_threshold=bg_value_threshold,
            light_value_threshold=light_value_threshold,
            neutral_color_threshold=neutral_color_threshold,
            mode=mode,
            bw_threshold=bw_threshold,
            preserve_mask=preserve_mask,
        )

        preview = processed.copy()
        preview.thumbnail((1100, 1400), Image.Resampling.LANCZOS)
        return preview
    finally:
        src_doc.close()