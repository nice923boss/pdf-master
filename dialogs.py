"""Dialog windows for PDF Master advanced features."""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import fitz
from PIL import Image, ImageTk


class BaseDialog(tk.Toplevel):
    """Base class for modal dialogs."""

    def __init__(self, parent, title: str, width: int = 400, height: int = 300):
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)

        self.body_frame = ttk.Frame(self, padding=15)
        self.body_frame.pack(fill="both", expand=True)

        self.build_body(self.body_frame)
        self._build_buttons()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Escape>", lambda e: self._on_cancel())

    def build_body(self, parent):
        """Override to build dialog body."""
        pass

    def _build_buttons(self):
        btn_frame = ttk.Frame(self, padding=(15, 0, 15, 15))
        btn_frame.pack(fill="x")

        ttk.Button(btn_frame, text="\u53d6\u6d88", command=self._on_cancel).pack(side="right", padx=(5, 0))
        ttk.Button(btn_frame, text="\u78ba\u5b9a", command=self._on_ok).pack(side="right")

    def _on_ok(self):
        self.result = self.get_result()
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()

    def get_result(self):
        """Override to return dialog result."""
        return None


class WatermarkDialog(BaseDialog):
    """Dialog for text watermark settings."""

    def __init__(self, parent):
        super().__init__(parent, "\u52a0\u6d6e\u6c34\u5370", 420, 320)

    def build_body(self, parent):
        ttk.Label(parent, text="\u6d6e\u6c34\u5370\u6587\u5b57\uff1a").grid(row=0, column=0, sticky="w", pady=5)
        self.text_var = tk.StringVar(value="\u6a5f\u5bc6\u6587\u4ef6")
        ttk.Entry(parent, textvariable=self.text_var, width=30).grid(row=0, column=1, pady=5)

        ttk.Label(parent, text="\u5b57\u578b\u5927\u5c0f\uff1a").grid(row=1, column=0, sticky="w", pady=5)
        self.fontsize_var = tk.IntVar(value=48)
        ttk.Spinbox(parent, from_=12, to=120, textvariable=self.fontsize_var,
                     width=10).grid(row=1, column=1, sticky="w", pady=5)

        ttk.Label(parent, text="\u900f\u660e\u5ea6 (0-100%)\uff1a").grid(row=2, column=0, sticky="w", pady=5)
        self.opacity_var = tk.IntVar(value=30)
        ttk.Scale(parent, from_=5, to=100, variable=self.opacity_var,
                  orient="horizontal").grid(row=2, column=1, sticky="ew", pady=5)

        ttk.Label(parent, text="\u65cb\u8f49\u89d2\u5ea6\uff1a").grid(row=3, column=0, sticky="w", pady=5)
        self.angle_var = tk.IntVar(value=-45)
        ttk.Spinbox(parent, from_=-180, to=180, textvariable=self.angle_var,
                     width=10).grid(row=3, column=1, sticky="w", pady=5)

        ttk.Label(parent, text="\u984f\u8272\uff1a").grid(row=4, column=0, sticky="w", pady=5)
        self.color_var = tk.StringVar(value="\u7070\u8272")
        color_combo = ttk.Combobox(parent, textvariable=self.color_var, width=10,
                                    values=["\u7070\u8272", "\u7d05\u8272", "\u85cd\u8272", "\u9ed1\u8272"],
                                    state="readonly")
        color_combo.grid(row=4, column=1, sticky="w", pady=5)

        parent.columnconfigure(1, weight=1)

    def get_result(self):
        color_map = {
            "\u7070\u8272": (0.5, 0.5, 0.5),
            "\u7d05\u8272": (0.8, 0.2, 0.2),
            "\u85cd\u8272": (0.2, 0.2, 0.8),
            "\u9ed1\u8272": (0.2, 0.2, 0.2),
        }
        return {
            "text": self.text_var.get(),
            "font_size": self.fontsize_var.get(),
            "opacity": self.opacity_var.get() / 100.0,
            "angle": self.angle_var.get(),
            "color": color_map.get(self.color_var.get(), (0.5, 0.5, 0.5)),
        }


class EncryptDialog(BaseDialog):
    """Dialog for PDF encryption settings."""

    def __init__(self, parent):
        super().__init__(parent, "\u52a0\u5bc6 PDF", 380, 200)

    def build_body(self, parent):
        ttk.Label(parent, text="\u8a2d\u5b9a\u5bc6\u78bc\uff1a").grid(row=0, column=0, sticky="w", pady=8)
        self.pw_var = tk.StringVar()
        self.pw_entry = ttk.Entry(parent, textvariable=self.pw_var, show="*", width=25)
        self.pw_entry.grid(row=0, column=1, pady=8)

        ttk.Label(parent, text="\u78ba\u8a8d\u5bc6\u78bc\uff1a").grid(row=1, column=0, sticky="w", pady=8)
        self.pw2_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.pw2_var, show="*", width=25).grid(row=1, column=1, pady=8)

        self.error_label = ttk.Label(parent, text="", foreground="red")
        self.error_label.grid(row=2, column=0, columnspan=2, pady=5)

        self.pw_entry.focus_set()

    def _on_ok(self):
        if not self.pw_var.get():
            self.error_label.config(text="\u5bc6\u78bc\u4e0d\u53ef\u70ba\u7a7a")
            return
        if self.pw_var.get() != self.pw2_var.get():
            self.error_label.config(text="\u5169\u6b21\u5bc6\u78bc\u4e0d\u4e00\u81f4")
            return
        super()._on_ok()

    def get_result(self):
        return {"password": self.pw_var.get()}


class DecryptDialog(BaseDialog):
    """Dialog for PDF decryption."""

    def __init__(self, parent):
        super().__init__(parent, "\u89e3\u5bc6 PDF", 380, 160)

    def build_body(self, parent):
        ttk.Label(parent, text="\u8acb\u8f38\u5165\u5bc6\u78bc\uff1a").grid(row=0, column=0, sticky="w", pady=8)
        self.pw_var = tk.StringVar()
        self.pw_entry = ttk.Entry(parent, textvariable=self.pw_var, show="*", width=25)
        self.pw_entry.grid(row=0, column=1, pady=8)
        self.pw_entry.focus_set()
        self.pw_entry.bind("<Return>", lambda e: self._on_ok())

    def get_result(self):
        return {"password": self.pw_var.get()}


class CropDialog(BaseDialog):
    """Dialog for page cropping settings."""

    def __init__(self, parent):
        super().__init__(parent, "\u88c1\u5207\u9801\u9762", 400, 280)

    def build_body(self, parent):
        ttk.Label(parent, text="\u88c1\u5207\u908a\u8ddd\uff08\u55ae\u4f4d\uff1amm\uff09\uff1a",
                  font=("", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        labels = [("\u4e0a\u908a", "top"), ("\u4e0b\u908a", "bottom"),
                  ("\u5de6\u908a", "left"), ("\u53f3\u908a", "right")]
        self.vars = {}

        for i, (label, key) in enumerate(labels):
            ttk.Label(parent, text=f"{label}\uff1a").grid(row=i + 1, column=0, sticky="w", pady=5)
            var = tk.DoubleVar(value=0.0)
            self.vars[key] = var
            ttk.Spinbox(parent, from_=0, to=200, textvariable=var,
                         increment=1.0, width=10).grid(row=i + 1, column=1, sticky="w", pady=5)

        ttk.Label(parent, text="\u63d0\u793a\uff1a1mm \u2248 2.83 \u9ede",
                  foreground="gray").grid(row=6, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def get_result(self):
        mm_to_pt = 72.0 / 25.4
        return {
            "top": self.vars["top"].get() * mm_to_pt,
            "bottom": self.vars["bottom"].get() * mm_to_pt,
            "left": self.vars["left"].get() * mm_to_pt,
            "right": self.vars["right"].get() * mm_to_pt,
        }


class PageNumberDialog(BaseDialog):
    """Dialog for page numbering settings."""

    def __init__(self, parent):
        super().__init__(parent, "\u52a0\u9801\u78bc", 420, 300)

    def build_body(self, parent):
        ttk.Label(parent, text="\u4f4d\u7f6e\uff1a").grid(row=0, column=0, sticky="w", pady=5)
        self.pos_var = tk.StringVar(value="\u4e0b\u65b9\u7f6e\u4e2d")
        positions = ["\u4e0b\u65b9\u7f6e\u4e2d", "\u4e0b\u65b9\u7f6e\u5de6", "\u4e0b\u65b9\u7f6e\u53f3",
                     "\u4e0a\u65b9\u7f6e\u4e2d", "\u4e0a\u65b9\u7f6e\u5de6", "\u4e0a\u65b9\u7f6e\u53f3"]
        ttk.Combobox(parent, textvariable=self.pos_var, values=positions,
                     state="readonly", width=15).grid(row=0, column=1, sticky="w", pady=5)

        ttk.Label(parent, text="\u8d77\u59cb\u9801\u78bc\uff1a").grid(row=1, column=0, sticky="w", pady=5)
        self.start_var = tk.IntVar(value=1)
        ttk.Spinbox(parent, from_=0, to=9999, textvariable=self.start_var,
                     width=10).grid(row=1, column=1, sticky="w", pady=5)

        ttk.Label(parent, text="\u683c\u5f0f\uff1a").grid(row=2, column=0, sticky="w", pady=5)
        self.fmt_var = tk.StringVar(value="{n}")
        formats = ["{n}", "\u7b2c {n} \u9801", "{n} / {total}", "- {n} -", "Page {n}"]
        ttk.Combobox(parent, textvariable=self.fmt_var, values=formats,
                     width=15).grid(row=2, column=1, sticky="w", pady=5)

        ttk.Label(parent, text="\u5b57\u578b\u5927\u5c0f\uff1a").grid(row=3, column=0, sticky="w", pady=5)
        self.fontsize_var = tk.IntVar(value=12)
        ttk.Spinbox(parent, from_=8, to=36, textvariable=self.fontsize_var,
                     width=10).grid(row=3, column=1, sticky="w", pady=5)

        ttk.Label(parent, text="\u908a\u8ddd (mm)\uff1a").grid(row=4, column=0, sticky="w", pady=5)
        self.margin_var = tk.DoubleVar(value=12.7)
        ttk.Spinbox(parent, from_=5, to=50, textvariable=self.margin_var,
                     increment=1.0, width=10).grid(row=4, column=1, sticky="w", pady=5)

    def get_result(self):
        pos_map = {
            "\u4e0b\u65b9\u7f6e\u4e2d": "bottom-center",
            "\u4e0b\u65b9\u7f6e\u5de6": "bottom-left",
            "\u4e0b\u65b9\u7f6e\u53f3": "bottom-right",
            "\u4e0a\u65b9\u7f6e\u4e2d": "top-center",
            "\u4e0a\u65b9\u7f6e\u5de6": "top-left",
            "\u4e0a\u65b9\u7f6e\u53f3": "top-right",
        }
        mm_to_pt = 72.0 / 25.4
        return {
            "position": pos_map.get(self.pos_var.get(), "bottom-center"),
            "start_num": self.start_var.get(),
            "fmt": self.fmt_var.get(),
            "font_size": self.fontsize_var.get(),
            "margin": self.margin_var.get() * mm_to_pt,
        }


class ImageExportDialog(BaseDialog):
    """Dialog for PDF-to-image export settings."""

    def __init__(self, parent):
        super().__init__(parent, "PDF \u8f49\u5716\u7247", 380, 200)

    def build_body(self, parent):
        ttk.Label(parent, text="\u8f38\u51fa\u683c\u5f0f\uff1a").grid(row=0, column=0, sticky="w", pady=8)
        self.fmt_var = tk.StringVar(value="png")
        ttk.Combobox(parent, textvariable=self.fmt_var,
                     values=["png", "jpg"], state="readonly",
                     width=10).grid(row=0, column=1, sticky="w", pady=8)

        ttk.Label(parent, text="DPI\uff1a").grid(row=1, column=0, sticky="w", pady=8)
        self.dpi_var = tk.IntVar(value=150)
        ttk.Combobox(parent, textvariable=self.dpi_var,
                     values=[72, 96, 150, 200, 300], width=10).grid(row=1, column=1, sticky="w", pady=8)

    def get_result(self):
        return {
            "fmt": self.fmt_var.get(),
            "dpi": self.dpi_var.get(),
        }


# ── Reusable zoomable preview widget ────────────────────────────────────

class ZoomablePreviewCanvas(ttk.Frame):
    """Zoomable + scrollable PDF page preview with overlay hook.

    Users (parent dialogs) get:
      - A zoom toolbar (-, +, fit) and a live percentage label.
      - Scrollbars auto-activate when the page overflows the viewport.
      - Ctrl + MouseWheel zooms around the cursor.
      - A `redraw_overlay` callback invoked after every page redraw so
        parents can paint signatures / symbols / handles on top.
      - Coordinate helpers: canvas <-> page-ratio (0..1), independent
        of zoom and scroll state.
    """

    MIN_ZOOM = 0.25
    MAX_ZOOM = 8.0
    ZOOM_STEP = 1.25

    def __init__(self, parent, viewport_w: int = 600, viewport_h: int = 680,
                 redraw_overlay=None):
        super().__init__(parent)
        self._viewport_w = viewport_w
        self._viewport_h = viewport_h
        self._redraw_overlay = redraw_overlay

        self._doc: fitz.Document | None = None
        self._page_idx = 0
        self._base_scale = 1.0  # fits viewport
        self._zoom = 1.0        # user multiplier on top of base
        self._page_photo: ImageTk.PhotoImage | None = None
        self._page_w_px = 0
        self._page_h_px = 0
        self._margin = 20

        self._build()

    def _build(self):
        tb = ttk.Frame(self)
        tb.pack(fill="x")

        ttk.Button(tb, text="\u2212", width=3, command=self.zoom_out).pack(side="left")
        ttk.Button(tb, text="+", width=3, command=self.zoom_in).pack(side="left", padx=(2, 6))
        ttk.Button(tb, text="\u9069\u5408\u8996\u7a97",  # 適合視窗
                   command=self.zoom_fit).pack(side="left", padx=2)

        self._zoom_var = tk.StringVar(value="100%")
        ttk.Label(tb, textvariable=self._zoom_var, width=6,
                  foreground="#555").pack(side="left", padx=8)

        ttk.Label(tb, text="Ctrl + \u6efb\u8f2a = \u7e2e\u653e",  # Ctrl+滾輪=縮放
                  foreground="#999").pack(side="right")

        cframe = ttk.Frame(self, relief="sunken", borderwidth=1)
        cframe.pack(fill="both", expand=True, pady=(4, 0))

        self.canvas = tk.Canvas(
            cframe, width=self._viewport_w, height=self._viewport_h,
            bg="#e8e8e8", highlightthickness=0,
        )
        self._vbar = ttk.Scrollbar(cframe, orient="vertical",
                                   command=self.canvas.yview)
        self._hbar = ttk.Scrollbar(cframe, orient="horizontal",
                                   command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self._vbar.set,
                              xscrollcommand=self._hbar.set)

        self._vbar.pack(side="right", fill="y")
        self._hbar.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Control-MouseWheel>", self._on_ctrl_wheel)

    # ── Public API ───────────────────────────────────────────────────

    def set_page(self, doc: fitz.Document, page_idx: int,
                 preserve_zoom: bool = False):
        self._doc = doc
        self._page_idx = page_idx
        page = doc[page_idx]
        rect = page.rect

        avail_w = self._viewport_w - 2 * self._margin
        avail_h = self._viewport_h - 2 * self._margin
        self._base_scale = min(avail_w / rect.width, avail_h / rect.height)

        if not preserve_zoom:
            self._zoom = 1.0

        self._rerender()

    @property
    def page_idx(self) -> int:
        return self._page_idx

    def canvas_to_ratio(self, widget_x: float, widget_y: float):
        """Widget-local (event) coords to page ratio. Returns None if no page."""
        if self._page_w_px <= 0:
            return None
        cx = self.canvas.canvasx(widget_x)
        cy = self.canvas.canvasy(widget_y)
        rx = (cx - self._margin) / self._page_w_px
        ry = (cy - self._margin) / self._page_h_px
        return (rx, ry)

    def ratio_to_canvas(self, rx: float, ry: float):
        """Page ratio to canvas-space coords (independent of scroll)."""
        cx = self._margin + rx * self._page_w_px
        cy = self._margin + ry * self._page_h_px
        return (cx, cy)

    def event_to_canvas(self, widget_x: float, widget_y: float):
        """Widget-local (event) coords to canvas-space coords (scroll-aware)."""
        return (self.canvas.canvasx(widget_x), self.canvas.canvasy(widget_y))

    def page_px_size(self) -> tuple[int, int]:
        return (self._page_w_px, self._page_h_px)

    def pts_to_px(self, pts: float) -> float:
        """Convert a length in PDF points to current canvas pixels."""
        return pts * self._base_scale * self._zoom

    def redraw(self):
        """External trigger for a full redraw (e.g. after overlay state change)."""
        self._redraw()

    def zoom_in(self):
        self._apply_zoom(self._zoom * self.ZOOM_STEP)

    def zoom_out(self):
        self._apply_zoom(self._zoom / self.ZOOM_STEP)

    def zoom_fit(self):
        self._apply_zoom(1.0)

    # ── Internals ────────────────────────────────────────────────────

    def _rerender(self):
        if self._doc is None:
            return
        page = self._doc[self._page_idx]
        effective = self._base_scale * self._zoom
        mat = fitz.Matrix(effective, effective)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        self._page_photo = ImageTk.PhotoImage(img)
        self._page_w_px = pix.width
        self._page_h_px = pix.height

        sr_w = self._page_w_px + 2 * self._margin
        sr_h = self._page_h_px + 2 * self._margin
        self.canvas.configure(scrollregion=(0, 0, sr_w, sr_h))

        self._zoom_var.set(f"{int(round(self._zoom * 100))}%")
        self._redraw()

    def _redraw(self):
        self.canvas.delete("all")
        if self._page_photo is None:
            return
        x0 = self._margin
        y0 = self._margin
        x1 = x0 + self._page_w_px
        y1 = y0 + self._page_h_px

        self.canvas.create_rectangle(x0 + 4, y0 + 4, x1 + 4, y1 + 4,
                                     fill="#bbb", outline="")
        self.canvas.create_image(x0, y0, image=self._page_photo, anchor="nw")
        self.canvas.create_rectangle(x0, y0, x1, y1, outline="#888", width=1)

        if self._redraw_overlay:
            self._redraw_overlay()

    def _apply_zoom(self, new_zoom: float, center_widget=None):
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, new_zoom))
        if abs(new_zoom - self._zoom) < 0.001:
            return

        # Remember cursor location in page ratios to keep it stationary
        ratio = None
        if center_widget is not None:
            ratio = self.canvas_to_ratio(*center_widget)

        self._zoom = new_zoom
        self._rerender()

        if ratio is not None and 0 <= ratio[0] <= 1 and 0 <= ratio[1] <= 1:
            # Scroll so that ratio maps back under cursor's widget position
            new_cx, new_cy = self.ratio_to_canvas(*ratio)
            target_x = new_cx - center_widget[0]
            target_y = new_cy - center_widget[1]
            sr = self.canvas.cget("scrollregion").split()
            if len(sr) == 4:
                sr_w = float(sr[2])
                sr_h = float(sr[3])
                if sr_w > 0:
                    self.canvas.xview_moveto(max(0.0, target_x / sr_w))
                if sr_h > 0:
                    self.canvas.yview_moveto(max(0.0, target_y / sr_h))

    def _on_wheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def _on_ctrl_wheel(self, event):
        direction = 1 if event.delta > 0 else -1
        factor = self.ZOOM_STEP if direction > 0 else 1.0 / self.ZOOM_STEP
        self._apply_zoom(self._zoom * factor, center_widget=(event.x, event.y))


# ── Signature Dialog ────────────────────────────────────────────────────

class SignatureDialog(tk.Toplevel):
    """Interactive signature placement dialog with zoom + pan preview.

    Signature box is stored as page ratios (0..1) so position maps
    cleanly across pages of different sizes and is unaffected by zoom.
    """

    HANDLE = 7  # half-size of corner grab handles in canvas pixels

    def __init__(self, parent, doc: fitz.Document, selected_indices: set):
        super().__init__(parent)
        self.title("\u8cbc\u4e0a\u7c3d\u540d")  # 貼上簽名
        self.result = None
        self.transient(parent)
        self.grab_set()

        self._doc = doc
        self._total = len(doc)
        self._selected_indices = sorted(selected_indices) if selected_indices else []

        # Signature state (canonical: page ratios)
        self._png_path: str | None = None
        self._png_image: Image.Image | None = None       # original PIL image
        self._sig_photo: ImageTk.PhotoImage | None = None  # cached scaled tk image
        self._sig_ratio: list[float] | None = None  # [x_r, y_r, w_r, h_r]
        self._sig_aspect: float = 1.0  # width / height

        # Cached canvas-space box after each overlay redraw (for hit-testing)
        self._sig_canvas_box: tuple[float, float, float, float] | None = None

        # Drag state
        self._drag_mode: str | None = None
        self._drag_anchor_cx: float = 0.0
        self._drag_anchor_cy: float = 0.0
        self._drag_ratio_start: list[float] | None = None

        initial_page = self._selected_indices[0] if self._selected_indices else 0

        # Window sizing
        width = 1080
        height = 860
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")
        self.resizable(True, True)
        self.minsize(900, 700)

        self._build_ui()
        self._preview.set_page(doc, initial_page)
        self._update_page_label()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _build_ui(self):
        # Top: PNG picker
        top = ttk.Frame(self, padding=(15, 12, 15, 5))
        top.pack(fill="x")

        ttk.Label(top, text="\u7c3d\u540d\u5716\u6a94\uff1a").pack(side="left")  # 簽名圖檔：
        self._path_var = tk.StringVar(value="\uff08\u5c1a\u672a\u9078\u64c7\uff09")
        ttk.Label(top, textvariable=self._path_var, foreground="#555",
                  width=50, anchor="w").pack(side="left", padx=6)
        ttk.Button(top, text="\u9078\u64c7 PNG...",
                   command=self._pick_png).pack(side="left")

        # Middle: preview + side panel
        mid = ttk.Frame(self, padding=(15, 5, 15, 5))
        mid.pack(fill="both", expand=True)

        self._preview = ZoomablePreviewCanvas(
            mid, viewport_w=680, viewport_h=720,
            redraw_overlay=self._redraw_signature,
        )
        self._preview.pack(side="left", fill="both", expand=True)

        # Bind drag events on the inner canvas
        c = self._preview.canvas
        c.bind("<Button-1>", self._on_press)
        c.bind("<B1-Motion>", self._on_drag)
        c.bind("<ButtonRelease-1>", self._on_release)
        c.bind("<Motion>", self._on_hover)

        # Side panel
        side = ttk.Frame(mid, padding=(15, 0, 0, 0))
        side.pack(side="left", fill="y")

        ttk.Label(side, text="\u5957\u7528\u7bc4\u570d\uff1a",
                  font=("", 10, "bold")).pack(anchor="w", pady=(0, 4))

        self._scope_var = tk.StringVar(
            value="selected" if self._selected_indices else "current"
        )
        ttk.Radiobutton(side, text="\u76ee\u524d\u9810\u89bd\u9801",
                        variable=self._scope_var, value="current"
                        ).pack(anchor="w", pady=2)
        sel_text = (
            f"\u5df2\u9078 {len(self._selected_indices)} \u9801"
            if self._selected_indices else "\u5df2\u9078 (\u7121)"
        )
        rb = ttk.Radiobutton(side, text=sel_text,
                             variable=self._scope_var, value="selected")
        rb.pack(anchor="w", pady=2)
        if not self._selected_indices:
            rb.configure(state="disabled")
        ttk.Radiobutton(side, text=f"\u5168\u90e8 {self._total} \u9801",
                        variable=self._scope_var, value="all"
                        ).pack(anchor="w", pady=2)

        ttk.Separator(side, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(side, text="\u9810\u89bd\u9801\u9762\uff1a",
                  font=("", 10, "bold")).pack(anchor="w", pady=(0, 4))
        nav = ttk.Frame(side)
        nav.pack(anchor="w", pady=2)
        ttk.Button(nav, text="\u25c0", width=3,
                   command=self._prev_page).pack(side="left")
        self._page_label_var = tk.StringVar(value="P 1 / 1")
        ttk.Label(nav, textvariable=self._page_label_var, width=10,
                  anchor="center").pack(side="left", padx=4)
        ttk.Button(nav, text="\u25b6", width=3,
                   command=self._next_page).pack(side="left")

        ttk.Separator(side, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(
            side,
            text=(
                "\u62d6\u66f3\u7c3d\u540d\u6846\u79fb\u52d5\n"  # 拖曳簽名框移動
                "\u62d6\u89d2\u843d\u8abf\u6574\u5927\u5c0f\n"  # 拖角落調整大小
                "Ctrl + \u6efb\u8f2a \u7e2e\u653e\u9801\u9762\n"  # Ctrl+滾輪縮放頁面
                "\u6362\u9801\u5f8c\u4f4d\u7f6e\u4f9d\u6bd4\u4f8b\u4fdd\u7559"  # 換頁後位置依比例保留
            ),
            foreground="#666",
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        # Bottom: buttons
        bottom = ttk.Frame(self, padding=(15, 5, 15, 12))
        bottom.pack(fill="x")
        ttk.Button(bottom, text="\u53d6\u6d88",
                   command=self._on_cancel).pack(side="right", padx=(5, 0))
        ttk.Button(bottom, text="\u78ba\u5b9a",
                   command=self._on_ok).pack(side="right")

    # ── Overlay drawing ──────────────────────────────────────────────

    def _redraw_signature(self):
        """Called by ZoomablePreviewCanvas after each page redraw."""
        self._sig_canvas_box = None
        if self._sig_ratio is None or self._png_image is None:
            return

        x_r, y_r, w_r, h_r = self._sig_ratio
        page_w_px, page_h_px = self._preview.page_px_size()
        if page_w_px == 0:
            return

        sx0, sy0 = self._preview.ratio_to_canvas(x_r, y_r)
        w_px = max(int(w_r * page_w_px), 1)
        h_px = max(int(h_r * page_h_px), 1)
        sx1, sy1 = sx0 + w_px, sy0 + h_px

        # Rescale PNG to current pixel size
        scaled = self._png_image.resize((w_px, h_px), Image.LANCZOS)
        self._sig_photo = ImageTk.PhotoImage(scaled)

        c = self._preview.canvas
        c.create_image(sx0, sy0, image=self._sig_photo, anchor="nw")
        c.create_rectangle(sx0, sy0, sx1, sy1,
                           outline="#1e66f5", width=2, dash=(4, 3))
        self._draw_handle(sx0, sy0)
        self._draw_handle(sx1, sy0)
        self._draw_handle(sx0, sy1)
        self._draw_handle(sx1, sy1)

        self._sig_canvas_box = (sx0, sy0, sx1, sy1)

    def _draw_handle(self, x: float, y: float):
        h = self.HANDLE
        self._preview.canvas.create_rectangle(
            x - h, y - h, x + h, y + h,
            fill="white", outline="#1e66f5", width=2,
        )

    # ── PNG picker ────────────────────────────────────────────────────

    def _pick_png(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="\u9078\u64c7\u7c3d\u540d PNG",
            filetypes=[("PNG", "*.png"), ("\u6240\u6709\u6a94\u6848", "*.*")],
        )
        if not path:
            return

        try:
            img = Image.open(path)
        except Exception as e:
            messagebox.showerror(
                "\u932f\u8aa4",
                f"\u7121\u6cd5\u8b80\u53d6\u5716\u7247\uff1a\n{e}",
                parent=self,
            )
            return

        self._png_path = path
        self._png_image = img.convert("RGBA")
        self._sig_aspect = img.width / img.height if img.height else 1.0
        self._path_var.set(os.path.basename(path))

        # Default: 35% width, lower-right (in page ratios)
        w_r = 0.35
        h_r = w_r * (img.height / img.width) if img.width else 0.15
        if h_r > 0.4:
            h_r = 0.25
            w_r = h_r * (img.width / img.height) if img.height else 0.35
        x_r = min(0.6, 1.0 - w_r)
        y_r = min(0.75, 1.0 - h_r)
        self._sig_ratio = [x_r, y_r, w_r, h_r]

        self._preview.redraw()

    # ── Page navigation ───────────────────────────────────────────────

    def _prev_page(self):
        if self._preview.page_idx > 0:
            self._preview.set_page(self._doc, self._preview.page_idx - 1)
            self._update_page_label()

    def _next_page(self):
        if self._preview.page_idx < self._total - 1:
            self._preview.set_page(self._doc, self._preview.page_idx + 1)
            self._update_page_label()

    def _update_page_label(self):
        self._page_label_var.set(f"P {self._preview.page_idx + 1} / {self._total}")

    # ── Drag interactions ────────────────────────────────────────────

    def _hit_test(self, cx: float, cy: float) -> str | None:
        if self._sig_canvas_box is None:
            return None
        x0, y0, x1, y1 = self._sig_canvas_box
        h = self.HANDLE + 2
        if abs(cx - x0) <= h and abs(cy - y0) <= h:
            return "nw"
        if abs(cx - x1) <= h and abs(cy - y0) <= h:
            return "ne"
        if abs(cx - x0) <= h and abs(cy - y1) <= h:
            return "sw"
        if abs(cx - x1) <= h and abs(cy - y1) <= h:
            return "se"
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            return "move"
        return None

    def _on_hover(self, event):
        cx, cy = self._preview.event_to_canvas(event.x, event.y)
        mode = self._hit_test(cx, cy)
        cursors = {
            "move": "fleur",
            "nw": "size_nw_se", "se": "size_nw_se",
            "ne": "size_ne_sw", "sw": "size_ne_sw",
        }
        self._preview.canvas.configure(cursor=cursors.get(mode, ""))

    def _on_press(self, event):
        cx, cy = self._preview.event_to_canvas(event.x, event.y)
        mode = self._hit_test(cx, cy)
        if mode is None:
            self._drag_mode = None
            return
        self._drag_mode = mode
        self._drag_anchor_cx = cx
        self._drag_anchor_cy = cy
        self._drag_ratio_start = list(self._sig_ratio) if self._sig_ratio else None

    def _on_drag(self, event):
        if self._drag_mode is None or self._drag_ratio_start is None:
            return
        page_w, page_h = self._preview.page_px_size()
        if page_w == 0:
            return

        cx, cy = self._preview.event_to_canvas(event.x, event.y)
        d_cx = cx - self._drag_anchor_cx
        d_cy = cy - self._drag_anchor_cy
        dx_r = d_cx / page_w
        dy_r = d_cy / page_h

        x_r, y_r, w_r, h_r = self._drag_ratio_start

        if self._drag_mode == "move":
            new_x = max(0.0, min(1.0 - w_r, x_r + dx_r))
            new_y = max(0.0, min(1.0 - h_r, y_r + dy_r))
            self._sig_ratio = [new_x, new_y, w_r, h_r]
        else:
            # Resize preserving aspect ratio via width; anchor on opposite corner
            min_w_r = 20.0 / page_w  # ensure at least ~20 px wide
            if self._drag_mode == "se":
                ax_r, ay_r = x_r, y_r
                new_w = max(w_r + dx_r, min_w_r)
                new_h = new_w * h_r / w_r
                if ax_r + new_w > 1.0:
                    new_w = 1.0 - ax_r
                    new_h = new_w * h_r / w_r
                if ay_r + new_h > 1.0:
                    new_h = 1.0 - ay_r
                    new_w = new_h * w_r / h_r
                self._sig_ratio = [ax_r, ay_r, new_w, new_h]
            elif self._drag_mode == "nw":
                ax_r, ay_r = x_r + w_r, y_r + h_r
                new_w = max(w_r - dx_r, min_w_r)
                new_h = new_w * h_r / w_r
                if ax_r - new_w < 0.0:
                    new_w = ax_r
                    new_h = new_w * h_r / w_r
                if ay_r - new_h < 0.0:
                    new_h = ay_r
                    new_w = new_h * w_r / h_r
                self._sig_ratio = [ax_r - new_w, ay_r - new_h, new_w, new_h]
            elif self._drag_mode == "ne":
                ax_r, ay_r = x_r, y_r + h_r
                new_w = max(w_r + dx_r, min_w_r)
                new_h = new_w * h_r / w_r
                if ax_r + new_w > 1.0:
                    new_w = 1.0 - ax_r
                    new_h = new_w * h_r / w_r
                if ay_r - new_h < 0.0:
                    new_h = ay_r
                    new_w = new_h * w_r / h_r
                self._sig_ratio = [ax_r, ay_r - new_h, new_w, new_h]
            elif self._drag_mode == "sw":
                ax_r, ay_r = x_r + w_r, y_r
                new_w = max(w_r - dx_r, min_w_r)
                new_h = new_w * h_r / w_r
                if ax_r - new_w < 0.0:
                    new_w = ax_r
                    new_h = new_w * h_r / w_r
                if ay_r + new_h > 1.0:
                    new_h = 1.0 - ay_r
                    new_w = new_h * w_r / h_r
                self._sig_ratio = [ax_r - new_w, ay_r, new_w, new_h]

        self._preview.redraw()

    def _on_release(self, event):
        self._drag_mode = None

    # ── OK / Cancel ───────────────────────────────────────────────────

    def _on_ok(self):
        if self._png_path is None or self._sig_ratio is None:
            messagebox.showinfo(
                "\u63d0\u793a",
                "\u8acb\u5148\u9078\u64c7\u7c3d\u540d PNG",
                parent=self,
            )
            return

        x_r, y_r, w_r, h_r = self._sig_ratio

        scope = self._scope_var.get()
        if scope == "current":
            page_indices = [self._preview.page_idx]
        elif scope == "selected":
            page_indices = list(self._selected_indices)
        else:
            page_indices = list(range(self._total))

        self.result = {
            "png_path": self._png_path,
            "page_indices": page_indices,
            "x_ratio": x_r,
            "y_ratio": y_r,
            "width_ratio": w_r,
            "height_ratio": h_r,
        }
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


# ── Symbol Dialog ───────────────────────────────────────────────────────

# Symbol kind -> display label (Traditional Chinese)
SYMBOL_LABELS = [
    ("check",     "\u6253\u52fe \u2713"),       # 打勾 ✓
    ("cross",     "\u53c9\u53c9 \u2717"),       # 叉叉 ✗
    ("box",       "\u65b9\u6846 \u25a1"),       # 方框 □
    ("circle",    "\u5713\u5708 \u25cb"),       # 圓圈 ○
    ("star",      "\u661f\u661f \u2606"),       # 星星 ☆
    ("arrow",     "\u7bad\u982d \u2192"),       # 箭頭 →
    ("underline", "\u5e95\u7dda \u2500"),       # 底線 ─
]

# Color presets: (label, (r, g, b) in 0..1)
SYMBOL_COLORS = [
    ("\u7d05",  (0.85, 0.15, 0.15)),  # 紅
    ("\u9ed1",  (0.05, 0.05, 0.05)),  # 黑
    ("\u85cd",  (0.10, 0.35, 0.85)),  # 藍
    ("\u7da0",  (0.10, 0.65, 0.20)),  # 綠
]


class SymbolDialog(tk.Toplevel):
    """Continuous multi-symbol placement dialog (Acrobat-like).

    Behaviour:
      - Click empty area  → drop a new symbol of the current tool
      - Click on an existing symbol → select it
      - Drag a selected symbol → move it (ratio coords, page-relative)
      - Delete key → delete selected symbol
      - Result: list of placement dicts compatible with pdf_engine.add_symbols
    """

    HANDLE = 6

    # Default symbol size as page ratio (square box for most kinds)
    DEFAULT_SIZE_RATIO = 0.045

    def __init__(self, parent, doc: fitz.Document, selected_indices: set):
        super().__init__(parent)
        self.title("\u6dfb\u52a0\u7b26\u865f")  # 添加符號
        self.result: list[dict] | None = None
        self.transient(parent)
        self.grab_set()

        self._doc = doc
        self._total = len(doc)
        self._selected_indices = sorted(selected_indices) if selected_indices else []

        # All placements across all pages
        self._placements: list[dict] = []
        # Index of the currently selected placement, or None
        self._selected: int | None = None

        # Drag state
        self._drag_active = False
        self._drag_anchor_cx = 0.0
        self._drag_anchor_cy = 0.0
        self._drag_ratio_start: tuple[float, float] | None = None  # (x_r, y_r)

        # Cached canvas-space boxes per visible placement: {idx: (x0,y0,x1,y1)}
        self._visible_boxes: dict[int, tuple[float, float, float, float]] = {}

        initial_page = self._selected_indices[0] if self._selected_indices else 0

        width = 1180
        height = 880
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")
        self.resizable(True, True)
        self.minsize(980, 720)

        self._build_ui()
        self._preview.set_page(doc, initial_page)
        self._update_page_label()
        self._update_count_label()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Escape>", lambda e: self._on_cancel())
        self.bind("<Delete>", lambda e: self._delete_selected())
        self.bind("<BackSpace>", lambda e: self._delete_selected())

    # ── UI ───────────────────────────────────────────────────────────

    def _build_ui(self):
        # Hint banner at top
        hint = ttk.Frame(self, padding=(15, 10, 15, 0))
        hint.pack(fill="x")
        ttk.Label(
            hint,
            text=(
                "\u9ede\u64ca\u9810\u89bd\u5340\u7a7a\u767d\u8655\u653e\u4e0b\u7b26\u865f\u3001"  # 點擊預覽區空白處放下符號、
                "\u9ede\u64ca\u73fe\u6709\u7b26\u865f\u53ef\u9078\u53d6\u3001"  # 點擊現有符號可選取、
                "\u62d6\u66f3\u9078\u53d6\u4e2d\u7684\u7b26\u865f\u53ef\u79fb\u52d5\u3001"  # 拖曳選取中的符號可移動、
                "Delete \u522a\u9664\u9078\u53d6\u3002"  # Delete 刪除選取。
            ),
            foreground="#444",
        ).pack(side="left")

        # Main row: tool palette (left) | preview (center) | side panel (right)
        mid = ttk.Frame(self, padding=(15, 8, 15, 8))
        mid.pack(fill="both", expand=True)

        # ── Tool palette (left) ────────────────────────────────────
        tool = ttk.LabelFrame(mid, text="\u5de5\u5177", padding=10)  # 工具
        tool.pack(side="left", fill="y", padx=(0, 10))

        ttk.Label(tool, text="\u7b26\u865f\u985e\u578b\uff1a",  # 符號類型：
                  font=("", 9, "bold")).pack(anchor="w", pady=(0, 4))
        self._kind_var = tk.StringVar(value="check")
        for kind, label in SYMBOL_LABELS:
            ttk.Radiobutton(tool, text=label, variable=self._kind_var,
                            value=kind).pack(anchor="w", pady=1)

        ttk.Separator(tool, orient="horizontal").pack(fill="x", pady=8)

        ttk.Label(tool, text="\u984f\u8272\uff1a",  # 顏色：
                  font=("", 9, "bold")).pack(anchor="w", pady=(0, 4))
        self._color_var = tk.StringVar(value=SYMBOL_COLORS[0][0])
        color_row = ttk.Frame(tool)
        color_row.pack(anchor="w")
        for label, _rgb in SYMBOL_COLORS:
            ttk.Radiobutton(color_row, text=label, variable=self._color_var,
                            value=label).pack(side="left", padx=2)

        ttk.Separator(tool, orient="horizontal").pack(fill="x", pady=8)

        ttk.Label(tool, text="\u7dda\u5bec (PDF pt)\uff1a",  # 線寬 (PDF pt)：
                  font=("", 9, "bold")).pack(anchor="w", pady=(0, 4))
        self._stroke_var = tk.DoubleVar(value=2.0)
        ttk.Spinbox(tool, from_=0.5, to=8.0, increment=0.5,
                    textvariable=self._stroke_var, width=8).pack(anchor="w")

        ttk.Label(tool, text="\u7b26\u865f\u5927\u5c0f (%)\uff1a",  # 符號大小 (%)：
                  font=("", 9, "bold")).pack(anchor="w", pady=(8, 4))
        self._size_var = tk.DoubleVar(value=self.DEFAULT_SIZE_RATIO * 100)
        ttk.Spinbox(tool, from_=1.0, to=30.0, increment=0.5,
                    textvariable=self._size_var, width=8).pack(anchor="w")

        self._fill_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(tool, text="\u586b\u6eff (\u50c5\u65b9\u6846)",  # 填滿 (僅方框)
                        variable=self._fill_var).pack(anchor="w", pady=(8, 0))

        ttk.Separator(tool, orient="horizontal").pack(fill="x", pady=8)

        ttk.Button(tool, text="\u522a\u9664\u9078\u53d6",  # 刪除選取
                   command=self._delete_selected).pack(fill="x", pady=2)
        ttk.Button(tool, text="\u6e05\u9664\u672c\u9801",  # 清除本頁
                   command=self._clear_current_page).pack(fill="x", pady=2)
        ttk.Button(tool, text="\u6e05\u9664\u5168\u90e8",  # 清除全部
                   command=self._clear_all).pack(fill="x", pady=2)

        # ── Preview canvas (center) ────────────────────────────────
        self._preview = ZoomablePreviewCanvas(
            mid, viewport_w=720, viewport_h=740,
            redraw_overlay=self._redraw_symbols,
        )
        self._preview.pack(side="left", fill="both", expand=True)

        c = self._preview.canvas
        c.bind("<Button-1>", self._on_press)
        c.bind("<B1-Motion>", self._on_drag)
        c.bind("<ButtonRelease-1>", self._on_release)
        c.bind("<Motion>", self._on_hover)

        # ── Side panel (right) ─────────────────────────────────────
        side = ttk.Frame(mid, padding=(10, 0, 0, 0))
        side.pack(side="left", fill="y")

        ttk.Label(side, text="\u9810\u89bd\u9801\u9762\uff1a",  # 預覽頁面：
                  font=("", 10, "bold")).pack(anchor="w", pady=(0, 4))
        nav = ttk.Frame(side)
        nav.pack(anchor="w", pady=2)
        ttk.Button(nav, text="\u25c0", width=3,
                   command=self._prev_page).pack(side="left")
        self._page_label_var = tk.StringVar(value="P 1 / 1")
        ttk.Label(nav, textvariable=self._page_label_var, width=10,
                  anchor="center").pack(side="left", padx=4)
        ttk.Button(nav, text="\u25b6", width=3,
                   command=self._next_page).pack(side="left")

        ttk.Separator(side, orient="horizontal").pack(fill="x", pady=10)

        self._count_var = tk.StringVar(value="\u672c\u9801 0 \u500b / \u5408\u8a08 0 \u500b")
        ttk.Label(side, textvariable=self._count_var,
                  foreground="#555").pack(anchor="w")

        ttk.Separator(side, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(
            side,
            text=(
                "Ctrl + \u6efb\u8f2a \u7e2e\u653e\u9801\u9762\n"  # Ctrl+滾輪縮放頁面
                "\u7b26\u865f\u4ee5\u5411\u91cf\u5beb\u5165\uff0c\n"  # 符號以向量寫入，
                "\u5728 PDF \u4e2d\u653e\u5927\u4ecd\u4fdd\u6e05\u6670\u3002"  # 在 PDF 中放大仍保清晰。
            ),
            foreground="#666",
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        # ── Bottom buttons ─────────────────────────────────────────
        bottom = ttk.Frame(self, padding=(15, 5, 15, 12))
        bottom.pack(fill="x")
        ttk.Button(bottom, text="\u53d6\u6d88",
                   command=self._on_cancel).pack(side="right", padx=(5, 0))
        ttk.Button(bottom, text="\u5957\u7528\u4e26\u5beb\u5165",  # 套用並寫入
                   command=self._on_ok).pack(side="right")

    # ── Helpers ──────────────────────────────────────────────────────

    def _current_color_rgb(self) -> tuple[float, float, float]:
        label = self._color_var.get()
        for lbl, rgb in SYMBOL_COLORS:
            if lbl == label:
                return rgb
        return SYMBOL_COLORS[0][1]

    def _color_label_from_rgb(self, rgb) -> str:
        for lbl, c in SYMBOL_COLORS:
            if c == tuple(rgb):
                return lbl
        return SYMBOL_COLORS[0][0]

    def _rgb_to_hex(self, rgb) -> str:
        r, g, b = rgb
        return "#{:02x}{:02x}{:02x}".format(
            int(round(r * 255)), int(round(g * 255)), int(round(b * 255))
        )

    def _update_page_label(self):
        self._page_label_var.set(f"P {self._preview.page_idx + 1} / {self._total}")

    def _update_count_label(self):
        cur = self._preview.page_idx
        on_page = sum(1 for p in self._placements if p["page_idx"] == cur)
        total = len(self._placements)
        self._count_var.set(
            f"\u672c\u9801 {on_page} \u500b / \u5408\u8a08 {total} \u500b"
        )

    # ── Page nav ─────────────────────────────────────────────────────

    def _prev_page(self):
        if self._preview.page_idx > 0:
            self._preview.set_page(self._doc, self._preview.page_idx - 1)
            self._selected = None
            self._update_page_label()
            self._update_count_label()

    def _next_page(self):
        if self._preview.page_idx < self._total - 1:
            self._preview.set_page(self._doc, self._preview.page_idx + 1)
            self._selected = None
            self._update_page_label()
            self._update_count_label()

    # ── Overlay drawing ──────────────────────────────────────────────

    def _redraw_symbols(self):
        """Called by ZoomablePreviewCanvas after each page redraw."""
        self._visible_boxes.clear()
        cur_page = self._preview.page_idx
        page_w_px, page_h_px = self._preview.page_px_size()
        if page_w_px == 0:
            return

        c = self._preview.canvas
        for idx, p in enumerate(self._placements):
            if p["page_idx"] != cur_page:
                continue
            x0, y0 = self._preview.ratio_to_canvas(p["x_ratio"], p["y_ratio"])
            w_px = max(p["w_ratio"] * page_w_px, 4)
            h_px = max(p["h_ratio"] * page_h_px, 4)
            x1 = x0 + w_px
            y1 = y0 + h_px
            self._visible_boxes[idx] = (x0, y0, x1, y1)

            # Stroke width on canvas: scale stroke (in pts) using preview scale
            stroke_px = max(self._preview.pts_to_px(p["stroke"]), 1.0)
            self._draw_canvas_symbol(
                c, p["kind"], (x0, y0, x1, y1),
                color_hex=self._rgb_to_hex(p["color"]),
                stroke_px=stroke_px,
                fill_box=p.get("fill_box", False),
            )

            if idx == self._selected:
                # Selection outline + handles
                c.create_rectangle(x0 - 2, y0 - 2, x1 + 2, y1 + 2,
                                    outline="#1e66f5", width=2, dash=(4, 3))
                self._draw_handle(x0 - 2, y0 - 2)
                self._draw_handle(x1 + 2, y0 - 2)
                self._draw_handle(x0 - 2, y1 + 2)
                self._draw_handle(x1 + 2, y1 + 2)

    def _draw_handle(self, x: float, y: float):
        h = self.HANDLE
        self._preview.canvas.create_rectangle(
            x - h, y - h, x + h, y + h,
            fill="white", outline="#1e66f5", width=1,
        )

    @staticmethod
    def _draw_canvas_symbol(c: tk.Canvas, kind: str,
                             box: tuple[float, float, float, float],
                             color_hex: str, stroke_px: float,
                             fill_box: bool = False):
        """Approximate the PDF-rendered symbol on the tk canvas for preview."""
        x0, y0, x1, y1 = box
        w = x1 - x0
        h = y1 - y0
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        sw = max(int(round(stroke_px)), 1)

        if kind == "check":
            c.create_line(
                x0 + w * 0.15, y0 + h * 0.55,
                x0 + w * 0.40, y0 + h * 0.85,
                x0 + w * 0.90, y0 + h * 0.15,
                fill=color_hex, width=sw, capstyle="round", joinstyle="round",
            )
        elif kind == "cross":
            c.create_line(x0 + w * 0.15, y0 + h * 0.15,
                          x1 - w * 0.15, y1 - h * 0.15,
                          fill=color_hex, width=sw, capstyle="round")
            c.create_line(x1 - w * 0.15, y0 + h * 0.15,
                          x0 + w * 0.15, y1 - h * 0.15,
                          fill=color_hex, width=sw, capstyle="round")
        elif kind == "box":
            if fill_box:
                c.create_rectangle(x0, y0, x1, y1,
                                    outline=color_hex, fill=color_hex, width=sw)
            else:
                c.create_rectangle(x0, y0, x1, y1,
                                    outline=color_hex, fill="", width=sw)
        elif kind == "circle":
            c.create_oval(x0, y0, x1, y1,
                          outline=color_hex, fill="", width=sw)
        elif kind == "star":
            import math
            r_out = min(w, h) / 2
            r_in = r_out * 0.4
            pts = []
            for i in range(10):
                angle = -math.pi / 2 + i * math.pi / 5
                r = r_out if i % 2 == 0 else r_in
                pts.append(cx + r * math.cos(angle))
                pts.append(cy + r * math.sin(angle))
            c.create_polygon(pts, outline=color_hex, fill="",
                             width=sw, joinstyle="round")
        elif kind == "arrow":
            y_mid = cy
            c.create_line(x0 + w * 0.05, y_mid, x0 + w * 0.78, y_mid,
                          fill=color_hex, width=sw, capstyle="round")
            c.create_line(x1 - w * 0.22, y_mid - h * 0.32,
                          x1 - w * 0.02, y_mid,
                          fill=color_hex, width=sw,
                          capstyle="round", joinstyle="round")
            c.create_line(x1 - w * 0.22, y_mid + h * 0.32,
                          x1 - w * 0.02, y_mid,
                          fill=color_hex, width=sw,
                          capstyle="round", joinstyle="round")
        elif kind == "underline":
            y_bottom = y1 - h * 0.1
            c.create_line(x0, y_bottom, x1, y_bottom,
                          fill=color_hex, width=sw, capstyle="round")

    # ── Hit testing & cursor ─────────────────────────────────────────

    def _hit_test(self, cx: float, cy: float) -> int | None:
        # Iterate top-most first (last drawn = on top)
        for idx in reversed(list(self._visible_boxes.keys())):
            x0, y0, x1, y1 = self._visible_boxes[idx]
            pad = 4
            if x0 - pad <= cx <= x1 + pad and y0 - pad <= cy <= y1 + pad:
                return idx
        return None

    def _on_hover(self, event):
        cx, cy = self._preview.event_to_canvas(event.x, event.y)
        hit = self._hit_test(cx, cy)
        if hit is not None and hit == self._selected:
            self._preview.canvas.configure(cursor="fleur")
        elif hit is not None:
            self._preview.canvas.configure(cursor="hand2")
        else:
            self._preview.canvas.configure(cursor="crosshair")

    # ── Click / drag ─────────────────────────────────────────────────

    def _on_press(self, event):
        # Bring focus to the dialog so Delete key works
        self.focus_set()

        cx, cy = self._preview.event_to_canvas(event.x, event.y)
        hit = self._hit_test(cx, cy)

        if hit is not None:
            # Select (and prepare to drag)
            self._selected = hit
            p = self._placements[hit]
            self._drag_active = True
            self._drag_anchor_cx = cx
            self._drag_anchor_cy = cy
            self._drag_ratio_start = (p["x_ratio"], p["y_ratio"])
            self._preview.redraw()
            return

        # Empty space → add a new symbol of the current tool, centred at click
        ratio = self._preview.canvas_to_ratio(event.x, event.y)
        if ratio is None:
            return
        rx, ry = ratio
        if not (0 <= rx <= 1 and 0 <= ry <= 1):
            return

        # Compute symbol size in ratios — use page width as the basis so the
        # symbol stays roughly square in pixel terms (not in ratio terms,
        # because pages are typically taller than wide).
        size_pct = max(0.5, min(50.0, self._size_var.get())) / 100.0
        page_w_px, page_h_px = self._preview.page_px_size()
        if page_w_px == 0 or page_h_px == 0:
            return
        w_r = size_pct
        h_r = size_pct * (page_w_px / page_h_px)

        # Centre on cursor, then clamp inside page
        x_r = max(0.0, min(1.0 - w_r, rx - w_r / 2))
        y_r = max(0.0, min(1.0 - h_r, ry - h_r / 2))

        kind = self._kind_var.get()
        placement = {
            "page_idx": self._preview.page_idx,
            "kind": kind,
            "x_ratio": x_r,
            "y_ratio": y_r,
            "w_ratio": w_r,
            "h_ratio": h_r,
            "color": self._current_color_rgb(),
            "stroke": float(self._stroke_var.get()),
            "fill_box": bool(self._fill_var.get()) and kind == "box",
        }
        self._placements.append(placement)
        self._selected = len(self._placements) - 1
        self._drag_active = False
        self._drag_ratio_start = None
        self._preview.redraw()
        self._update_count_label()

    def _on_drag(self, event):
        if not self._drag_active or self._selected is None:
            return
        if self._drag_ratio_start is None:
            return
        page_w, page_h = self._preview.page_px_size()
        if page_w == 0:
            return
        cx, cy = self._preview.event_to_canvas(event.x, event.y)
        d_cx = cx - self._drag_anchor_cx
        d_cy = cy - self._drag_anchor_cy
        dx_r = d_cx / page_w
        dy_r = d_cy / page_h

        x0_r, y0_r = self._drag_ratio_start
        p = self._placements[self._selected]
        new_x = max(0.0, min(1.0 - p["w_ratio"], x0_r + dx_r))
        new_y = max(0.0, min(1.0 - p["h_ratio"], y0_r + dy_r))
        p["x_ratio"] = new_x
        p["y_ratio"] = new_y
        self._preview.redraw()

    def _on_release(self, event):
        self._drag_active = False

    # ── Edits ────────────────────────────────────────────────────────

    def _delete_selected(self):
        if self._selected is None:
            return
        if 0 <= self._selected < len(self._placements):
            del self._placements[self._selected]
        self._selected = None
        self._preview.redraw()
        self._update_count_label()

    def _clear_current_page(self):
        cur = self._preview.page_idx
        before = len(self._placements)
        self._placements = [p for p in self._placements if p["page_idx"] != cur]
        if before != len(self._placements):
            self._selected = None
            self._preview.redraw()
            self._update_count_label()

    def _clear_all(self):
        if not self._placements:
            return
        if not messagebox.askyesno(
            "\u78ba\u8a8d",  # 確認
            "\u78ba\u5b9a\u8981\u6e05\u9664\u5168\u90e8\u7b26\u865f\u55ce\uff1f",  # 確定要清除全部符號嗎？
            parent=self,
        ):
            return
        self._placements.clear()
        self._selected = None
        self._preview.redraw()
        self._update_count_label()

    # ── OK / Cancel ───────────────────────────────────────────────────

    def _on_ok(self):
        if not self._placements:
            messagebox.showinfo(
                "\u63d0\u793a",  # 提示
                "\u5c1a\u672a\u653e\u4e0b\u4efb\u4f55\u7b26\u865f\u3002",  # 尚未放下任何符號。
                parent=self,
            )
            return
        # Return a deep-ish copy to decouple from internal state
        self.result = [dict(p) for p in self._placements]
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()
