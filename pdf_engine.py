"""PDF Engine — Core PDF operations powered by PyMuPDF."""

import fitz  # PyMuPDF
import os
from pathlib import Path
from typing import Optional


def load_pdf(path: str, password: str = "") -> fitz.Document:
    """Load a PDF file. Returns a new Document object."""
    doc = fitz.open(path)
    if doc.is_encrypted:
        if not password:
            raise PermissionError("PDF is encrypted. Password required.")
        if not doc.authenticate(password):
            doc.close()
            raise PermissionError("Wrong password.")
    return doc


def merge_documents(docs_with_pages: list[tuple[fitz.Document, list[int]]]) -> fitz.Document:
    """Merge multiple documents (or subsets of pages) into a new document.

    Args:
        docs_with_pages: List of (document, page_indices) tuples.
                         page_indices is a list of 0-based page numbers to include.
    """
    merged = fitz.open()
    for doc, pages in docs_with_pages:
        for page_num in pages:
            merged.insert_pdf(doc, from_page=page_num, to_page=page_num)
    return merged


def delete_pages(doc: fitz.Document, page_indices: list[int]) -> fitz.Document:
    """Return a new document with specified pages removed."""
    keep = [i for i in range(len(doc)) if i not in page_indices]
    new_doc = fitz.open()
    for i in keep:
        new_doc.insert_pdf(doc, from_page=i, to_page=i)
    return new_doc


def extract_pages(doc: fitz.Document, page_indices: list[int]) -> fitz.Document:
    """Extract specified pages into a new document."""
    new_doc = fitz.open()
    for i in sorted(page_indices):
        new_doc.insert_pdf(doc, from_page=i, to_page=i)
    return new_doc


def reorder_pages(doc: fitz.Document, new_order: list[int]) -> fitz.Document:
    """Return a new document with pages in the specified order."""
    new_doc = fitz.open()
    for i in new_order:
        new_doc.insert_pdf(doc, from_page=i, to_page=i)
    return new_doc


def rotate_pages(doc: fitz.Document, page_indices: list[int], angle: int) -> fitz.Document:
    """Return a new document with specified pages rotated.

    Args:
        angle: Rotation angle in degrees (90, 180, 270).
    """
    new_doc = fitz.open()
    new_doc.insert_pdf(doc)
    for i in page_indices:
        page = new_doc[i]
        page.set_rotation((page.rotation + angle) % 360)
    return new_doc


def render_page_thumbnail(doc: fitz.Document, page_num: int,
                          max_width: int = 200, max_height: int = 280) -> bytes:
    """Render a page as PNG thumbnail bytes, fitting within max dimensions."""
    page = doc[page_num]
    rect = page.rect

    scale_w = max_width / rect.width
    scale_h = max_height / rect.height
    scale = min(scale_w, scale_h)

    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes("png")


def add_text_watermark(doc: fitz.Document, text: str,
                       font_size: float = 48,
                       opacity: float = 0.3,
                       angle: float = -45,
                       color: tuple = (0.5, 0.5, 0.5)) -> fitz.Document:
    """Add a diagonal text watermark to all pages. Returns new document."""
    new_doc = fitz.open()
    new_doc.insert_pdf(doc)

    for page in new_doc:
        rect = page.rect
        cx, cy = rect.width / 2, rect.height / 2

        # Create text writer for watermark
        tw = fitz.TextWriter(page.rect)
        font = fitz.Font("helv")

        # Calculate text position (centered)
        text_width = font.text_length(text, fontsize=font_size)
        x = cx - text_width / 2
        y = cy + font_size / 2

        tw.append((x, y), text, font=font, fontsize=font_size)

        # Apply with rotation and opacity
        tw.write_text(page, opacity=opacity, color=color,
                      morph=(fitz.Point(cx, cy), fitz.Matrix(angle)))

    return new_doc


def encrypt_pdf(doc: fitz.Document, user_password: str,
                owner_password: str = "") -> fitz.Document:
    """Encrypt a PDF with password protection. Returns new document bytes."""
    if not owner_password:
        owner_password = user_password

    new_doc = fitz.open()
    new_doc.insert_pdf(doc)

    # Set encryption
    perm = fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY | fitz.PDF_PERM_ANNOTATE
    new_doc.save(
        new_doc.name if new_doc.name else "temp_encrypted.pdf",
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw=user_password,
        owner_pw=owner_password,
        permissions=perm,
    )
    return new_doc


def save_encrypted(doc: fitz.Document, output_path: str,
                   user_password: str, owner_password: str = ""):
    """Save document with encryption to a file."""
    if not owner_password:
        owner_password = user_password

    perm = fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY | fitz.PDF_PERM_ANNOTATE
    doc.save(
        output_path,
        garbage=4,
        deflate=True,
        clean=True,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw=user_password,
        owner_pw=owner_password,
        permissions=perm,
    )


def compress_pdf(doc: fitz.Document) -> fitz.Document:
    """Compress a PDF by re-saving with garbage collection and deflation."""
    import tempfile

    tmp_path = os.path.join(tempfile.gettempdir(), "_pdf_master_compress.pdf")
    doc.save(tmp_path, garbage=4, deflate=True, clean=True)
    compressed = fitz.open(tmp_path)

    # Clean up temp file after loading
    try:
        os.remove(tmp_path)
    except OSError:
        pass

    return compressed


def pdf_to_images(doc: fitz.Document, page_indices: list[int],
                  output_dir: str, fmt: str = "png",
                  dpi: int = 150) -> list[str]:
    """Export pages as image files. Returns list of output file paths."""
    os.makedirs(output_dir, exist_ok=True)
    scale = dpi / 72
    mat = fitz.Matrix(scale, scale)

    paths = []
    for i in page_indices:
        page = doc[i]
        pix = page.get_pixmap(matrix=mat, alpha=False)
        filename = f"page_{i + 1:03d}.{fmt}"
        out_path = os.path.join(output_dir, filename)
        pix.save(out_path)
        paths.append(out_path)

    return paths


def images_to_pdf(image_paths: list[str]) -> fitz.Document:
    """Convert multiple images to a single PDF document."""
    doc = fitz.open()

    for img_path in image_paths:
        img_doc = fitz.open(img_path)
        # Get image dimensions
        pdfbytes = img_doc.convert_to_pdf()
        img_pdf = fitz.open("pdf", pdfbytes)
        doc.insert_pdf(img_pdf)
        img_doc.close()
        img_pdf.close()

    return doc


def crop_pages(doc: fitz.Document, page_indices: list[int],
               top: float = 0, bottom: float = 0,
               left: float = 0, right: float = 0) -> fitz.Document:
    """Crop specified pages by trimming margins (in points, 72 pts = 1 inch).

    Args:
        top, bottom, left, right: Margin to trim in points.
    """
    new_doc = fitz.open()
    new_doc.insert_pdf(doc)

    for i in page_indices:
        page = new_doc[i]
        rect = page.rect
        new_rect = fitz.Rect(
            rect.x0 + left,
            rect.y0 + top,
            rect.x1 - right,
            rect.y1 - bottom
        )
        page.set_cropbox(new_rect)

    return new_doc


def add_page_numbers(doc: fitz.Document,
                     position: str = "bottom-center",
                     start_num: int = 1,
                     fmt: str = "{n}",
                     font_size: float = 12,
                     margin: float = 36) -> fitz.Document:
    """Add page numbers to all pages. Returns new document.

    Args:
        position: "bottom-center", "bottom-left", "bottom-right",
                  "top-center", "top-left", "top-right"
        start_num: Starting page number.
        fmt: Format string. {n} = page number, {total} = total pages.
        font_size: Font size in points.
        margin: Distance from page edge in points.
    """
    new_doc = fitz.open()
    new_doc.insert_pdf(doc)
    total = len(new_doc)

    for i, page in enumerate(new_doc):
        rect = page.rect
        num_text = fmt.replace("{n}", str(i + start_num)).replace("{total}", str(total))

        # Calculate position
        text_width = fitz.get_text_length(num_text, fontname="helv", fontsize=font_size)

        if "center" in position:
            x = (rect.width - text_width) / 2
        elif "right" in position:
            x = rect.width - text_width - margin
        else:  # left
            x = margin

        if "top" in position:
            y = margin + font_size
        else:  # bottom
            y = rect.height - margin

        page.insert_text(
            fitz.Point(x, y),
            num_text,
            fontname="helv",
            fontsize=font_size,
            color=(0.3, 0.3, 0.3),
        )

    return new_doc


SYMBOL_KINDS = ("check", "cross", "box", "circle", "star", "arrow", "underline")


def _draw_symbol_on_page(page: fitz.Page, kind: str, rect: fitz.Rect,
                          color: tuple[float, float, float],
                          stroke: float, fill_box: bool = False):
    """Render one vector symbol inside rect using PyMuPDF drawing API.

    Vector drawing keeps edges crisp at any PDF viewer zoom.
    """
    shape = page.new_shape()
    x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    w = x1 - x0
    h = y1 - y0

    if kind == "check":
        # Two line segments forming a checkmark — open path (no closure)
        p1 = fitz.Point(x0 + w * 0.15, y0 + h * 0.55)
        p2 = fitz.Point(x0 + w * 0.40, y0 + h * 0.85)
        p3 = fitz.Point(x0 + w * 0.90, y0 + h * 0.15)
        shape.draw_polyline([p1, p2, p3])
        shape.finish(color=color, width=stroke, lineCap=1, closePath=False)

    elif kind == "cross":
        # Two diagonals — disconnected paths, no closure
        shape.draw_line(fitz.Point(x0 + w * 0.15, y0 + h * 0.15),
                        fitz.Point(x0 + w * 0.85, y0 + h * 0.85))
        shape.draw_line(fitz.Point(x0 + w * 0.85, y0 + h * 0.15),
                        fitz.Point(x0 + w * 0.15, y0 + h * 0.85))
        shape.finish(color=color, width=stroke, lineCap=1, closePath=False)

    elif kind == "box":
        shape.draw_rect(rect)
        if fill_box:
            shape.finish(color=color, width=stroke, fill=color)
        else:
            shape.finish(color=color, width=stroke, fill=None)

    elif kind == "circle":
        shape.draw_oval(rect)
        shape.finish(color=color, width=stroke, fill=None)

    elif kind == "star":
        # 5-point star: outer radius = half of smaller side, inner = 0.4 * outer
        import math
        r_out = min(w, h) / 2
        r_in = r_out * 0.4
        pts = []
        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            r = r_out if i % 2 == 0 else r_in
            pts.append(fitz.Point(cx + r * math.cos(angle),
                                  cy + r * math.sin(angle)))
        shape.draw_polyline(pts + [pts[0]])
        shape.finish(color=color, width=stroke, fill=None, closePath=True)

    elif kind == "arrow":
        # Horizontal arrow, left → right. Shaft + two arrowhead lines as
        # disconnected segments in one shape; closePath=False prevents
        # connecting the head segments into a closed triangle.
        y_mid = cy
        shaft_start = fitz.Point(x0 + w * 0.05, y_mid)
        head_tip = fitz.Point(x1 - w * 0.02, y_mid)
        head_top = fitz.Point(x1 - w * 0.22, y_mid - h * 0.32)
        head_bot = fitz.Point(x1 - w * 0.22, y_mid + h * 0.32)
        shape.draw_line(shaft_start, head_tip)
        shape.draw_line(head_top, head_tip)
        shape.draw_line(head_bot, head_tip)
        shape.finish(color=color, width=stroke, lineCap=1, closePath=False)

    elif kind == "underline":
        y_bottom = y1 - h * 0.1
        shape.draw_line(fitz.Point(x0, y_bottom), fitz.Point(x1, y_bottom))
        shape.finish(color=color, width=stroke, lineCap=1, closePath=False)

    else:
        shape.commit()
        raise ValueError(f"Unknown symbol kind: {kind!r}")

    shape.commit()


def add_symbols(doc: fitz.Document,
                placements: list[dict]) -> fitz.Document:
    """Stamp vector symbols onto pages.

    Each placement dict:
        page_idx:   int, 0-based page index
        kind:       one of SYMBOL_KINDS
        x_ratio, y_ratio, w_ratio, h_ratio: page-relative bounding box (0..1)
        color:      (r, g, b) with each component in 0..1
        stroke:     line width in PDF points (typically 1.0 - 4.0)
        fill_box:   optional bool, only honored for kind="box"
    """
    new_doc = fitz.open()
    new_doc.insert_pdf(doc)

    for p in placements:
        i = p["page_idx"]
        if i < 0 or i >= len(new_doc):
            continue
        page = new_doc[i]
        rect = page.rect
        x0 = rect.x0 + p["x_ratio"] * rect.width
        y0 = rect.y0 + p["y_ratio"] * rect.height
        x1 = x0 + p["w_ratio"] * rect.width
        y1 = y0 + p["h_ratio"] * rect.height
        _draw_symbol_on_page(
            page, p["kind"], fitz.Rect(x0, y0, x1, y1),
            color=p.get("color", (0.85, 0.15, 0.15)),
            stroke=p.get("stroke", 2.0),
            fill_box=p.get("fill_box", False),
        )

    return new_doc


def add_signature(doc: fitz.Document,
                  png_path: str,
                  page_indices: list[int],
                  x_ratio: float,
                  y_ratio: float,
                  width_ratio: float,
                  height_ratio: float) -> fitz.Document:
    """Stamp a (transparent) PNG signature onto specified pages.

    Position and size are stored as ratios (0..1) relative to each page's
    dimensions, so a single placement maps cleanly across pages of
    different sizes.

    Args:
        doc: Source document.
        png_path: Path to signature PNG (alpha channel preserved).
        page_indices: Page indices (0-based) to stamp.
        x_ratio, y_ratio: Top-left corner of signature, as fraction of
                         page width/height.
        width_ratio, height_ratio: Signature box size, as fraction of
                         page width/height.
    """
    new_doc = fitz.open()
    new_doc.insert_pdf(doc)

    for i in page_indices:
        page = new_doc[i]
        rect = page.rect
        x0 = rect.x0 + x_ratio * rect.width
        y0 = rect.y0 + y_ratio * rect.height
        x1 = x0 + width_ratio * rect.width
        y1 = y0 + height_ratio * rect.height
        placement = fitz.Rect(x0, y0, x1, y1)
        page.insert_image(
            placement,
            filename=png_path,
            keep_proportion=True,
            overlay=True,
        )

    return new_doc


def save_pdf(doc: fitz.Document, output_path: str,
             garbage: int = 4, deflate: bool = True):
    """Save document to file.

    garbage=4 merges duplicate streams and clean=True drops resources a page
    never draws; without both, page-by-page insert_pdf copies a shared
    /Resources dict (every image in the source) into every output page.
    """
    doc.save(output_path, garbage=garbage, deflate=deflate, clean=True)


def get_page_info(doc: fitz.Document, page_num: int) -> dict:
    """Get information about a specific page."""
    page = doc[page_num]
    rect = page.rect
    return {
        "width": rect.width,
        "height": rect.height,
        "width_mm": rect.width * 25.4 / 72,
        "height_mm": rect.height * 25.4 / 72,
        "rotation": page.rotation,
    }


def get_doc_info(doc: fitz.Document) -> dict:
    """Get document metadata."""
    meta = doc.metadata or {}
    return {
        "page_count": len(doc),
        "title": meta.get("title", ""),
        "author": meta.get("author", ""),
        "subject": meta.get("subject", ""),
        "creator": meta.get("creator", ""),
        "producer": meta.get("producer", ""),
        "is_encrypted": doc.is_encrypted,
        "file_size": os.path.getsize(doc.name) if doc.name and os.path.exists(doc.name) else 0,
    }
