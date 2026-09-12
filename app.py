"""PDF Master — Full-featured PDF management tool."""

import sys
import os
import logging

# Guard stdout for pythonw.exe
if sys.stdout is None:
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log")
    sys.stdout = open(log_path, "w", encoding="utf-8")
    sys.stderr = sys.stdout

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image, ImageTk
from io import BytesIO
import fitz
import threading
import copy

import pdf_engine
from thumbnail_cache import ThumbnailCache, ThumbnailRenderer
from dialogs import (WatermarkDialog, EncryptDialog, DecryptDialog,
                     CropDialog, PageNumberDialog, ImageExportDialog,
                     SignatureDialog, SymbolDialog)

# ── Data Model ──────────────────────────────────────────────────────────

class PageItem:
    """Represents a single page in the working set."""

    def __init__(self, doc: fitz.Document, doc_id: int,
                 page_num: int, source_file: str):
        self.doc = doc
        self.doc_id = doc_id
        self.page_num = page_num
        self.source_file = source_file
        self.rotation_extra = 0  # additional rotation applied by user

    @property
    def label(self) -> str:
        basename = os.path.basename(self.source_file)
        return f"{basename} - P{self.page_num + 1}"


# ── Main Application ────────────────────────────────────────────────────

class PDFMasterApp:
    THUMB_W = 160
    THUMB_H = 220
    CELL_W = 185
    CELL_H = 270
    COLS = 4
    IMG_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif", ".webp")

    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("PDF \u5927\u5e2b")
        self.root.geometry("1100x750")
        self.root.minsize(800, 500)

        self.pages: list[PageItem] = []
        self.selected: set[int] = set()  # indices into self.pages
        self.loaded_docs: dict[int, fitz.Document] = {}
        self._next_doc_id = 0
        self._source_files: list[str] = []

        self.cache = ThumbnailCache()
        self.renderer = ThumbnailRenderer(self.cache)
        self._photo_refs: list[ImageTk.PhotoImage] = []

        self._drag_start_idx: int | None = None
        self._drag_target_idx: int | None = None

        self._build_ui()
        self._bind_shortcuts()
        self._bind_dnd()

    # ── UI Construction ──────────────────────────────────────────────

    def _build_ui(self):
        # Main toolbar
        tb = ttk.Frame(self.root, padding=5)
        tb.pack(fill="x")

        buttons_top = [
            ("\u958b\u555f\u6a94\u6848", self._on_open),
            ("\u52a0\u5165\u6a94\u6848", self._on_add),
            ("\u5132\u5b58", self._on_save),
            ("\u53e6\u5b58\u65b0\u6a94", self._on_save_as),
            None,  # separator
            ("\u2b86 \u65cb\u8f49", lambda: self._on_rotate(-90)),
            ("\u65cb\u8f49 \u2b87", lambda: self._on_rotate(90)),
            ("\u522a\u9664", self._on_delete),
            ("\u63d0\u53d6", self._on_extract),
            ("\u5168\u9078", self._on_select_all),
        ]
        for item in buttons_top:
            if item is None:
                ttk.Separator(tb, orient="vertical").pack(side="left", fill="y", padx=5)
            else:
                text, cmd = item
                ttk.Button(tb, text=text, command=cmd).pack(side="left", padx=2)

        # Main area: file list + thumbnail grid
        paned = ttk.PanedWindow(self.root, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=5)

        # Left panel: file list
        left = ttk.Frame(paned, width=200)
        paned.add(left, weight=0)

        ttk.Label(left, text="\u5df2\u8f09\u5165\u6a94\u6848", font=("", 10, "bold")).pack(
            anchor="w", padx=5, pady=(5, 2))
        self.file_listbox = tk.Listbox(left, selectmode="extended", width=28)
        self.file_listbox.pack(fill="both", expand=True, padx=5, pady=5)

        file_btn_frame = ttk.Frame(left)
        file_btn_frame.pack(fill="x", padx=5, pady=(0, 5))
        ttk.Button(file_btn_frame, text="\u79fb\u9664\u6a94\u6848", command=self._on_remove_file).pack(fill="x")

        # Right panel: thumbnail canvas
        right = ttk.Frame(paned)
        paned.add(right, weight=1)

        self.canvas = tk.Canvas(right, bg="#f0f0f0", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(right, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Control-Button-1>", self._on_canvas_ctrl_click)
        self.canvas.bind("<Shift-Button-1>", self._on_canvas_shift_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_drop)
        self.canvas.bind("<Button-3>", self._on_right_click)

        # Mouse wheel scrolling
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

        # Advanced toolbar
        tb2 = ttk.Frame(self.root, padding=5)
        tb2.pack(fill="x")

        buttons_adv = [
            ("\u52a0\u6d6e\u6c34\u5370", self._on_watermark),
            ("\u7c3d\u540d", self._on_signature),
            ("\u7b26\u865f", self._on_add_symbols),
            ("\u52a0\u5bc6", self._on_encrypt),
            ("\u89e3\u5bc6", self._on_decrypt),
            ("\u58d3\u7e2e", self._on_compress),
            None,
            ("\u8f49\u5716\u7247", self._on_to_images),
            ("\u5716\u8f49PDF", self._on_images_to_pdf),
            ("\u88c1\u5207", self._on_crop),
            ("\u52a0\u9801\u78bc", self._on_page_numbers),
        ]
        for item in buttons_adv:
            if item is None:
                ttk.Separator(tb2, orient="vertical").pack(side="left", fill="y", padx=5)
            else:
                text, cmd = item
                ttk.Button(tb2, text=text, command=cmd).pack(side="left", padx=2)

        # Status bar
        status = ttk.Frame(self.root, padding=(10, 3))
        status.pack(fill="x")

        self.status_var = tk.StringVar(value="\u62d6\u653e PDF \u6a94\u6848\u5230\u6b64\u8655\u958b\u59cb")
        ttk.Label(status, textvariable=self.status_var).pack(side="left")
        ttk.Label(status, text="\u88fd\u4f5c\u8005\uff1a\u9ec3\u653f\u6587",
                  foreground="gray").pack(side="right")

        # Drop hint overlay
        self._drop_hint_id = None

    def _bind_shortcuts(self):
        self.root.bind("<Delete>", lambda e: self._on_delete())
        self.root.bind("<Control-a>", lambda e: self._on_select_all())
        self.root.bind("<Control-s>", lambda e: self._on_save())
        self.root.bind("<Control-o>", lambda e: self._on_open())
        self.root.bind("<Control-z>", lambda e: self._on_undo())

    def _bind_dnd(self):
        self.canvas.drop_target_register(DND_FILES)
        self.canvas.dnd_bind("<<Drop>>", self._on_dnd_drop)
        self.canvas.dnd_bind("<<DragEnter>>", self._on_dnd_enter)
        self.canvas.dnd_bind("<<DragLeave>>", self._on_dnd_leave)

    # ── Undo support (simple snapshot) ───────────────────────────────

    def _save_undo(self):
        """Save current page order for undo."""
        self._undo_pages = list(self.pages)
        self._undo_selected = set(self.selected)

    def _on_undo(self):
        if hasattr(self, '_undo_pages') and self._undo_pages is not None:
            self.pages = self._undo_pages
            self.selected = self._undo_selected
            self._undo_pages = None
            self._refresh_thumbnails()

    # ── File Operations ──────────────────────────────────────────────

    def _load_file(self, path: str, password: str = ""):
        """Load a PDF or image file and add its pages to the working set.

        Image files are auto-converted to a single-page PDF: every downstream
        op (save, watermark, signature, etc.) calls insert_pdf, which rejects
        non-PDF documents with "source or target not a PDF".
        """
        ext = os.path.splitext(path)[1].lower()
        is_image = ext in self.IMG_EXTENSIONS

        if is_image:
            try:
                doc = pdf_engine.images_to_pdf([path])
            except Exception as e:
                messagebox.showerror(
                    "\u932f\u8aa4",  # \u932f\u8aa4
                    f"\u7121\u6cd5\u8f09\u5165\u5716\u7247\uff1a\n{e}",  # \u7121\u6cd5\u8f09\u5165\u5716\u7247\uff1a
                )
                return
        else:
            try:
                doc = pdf_engine.load_pdf(path, password)
            except PermissionError:
                # Ask for password
                from dialogs import DecryptDialog
                dlg = DecryptDialog(self.root)
                self.root.wait_window(dlg)
                if dlg.result is None:
                    return
                try:
                    doc = pdf_engine.load_pdf(path, dlg.result["password"])
                except PermissionError:
                    messagebox.showerror("\u932f\u8aa4", "\u5bc6\u78bc\u932f\u8aa4\uff0c\u7121\u6cd5\u958b\u555f\u6a94\u6848")
                    return
            except Exception as e:
                messagebox.showerror("\u932f\u8aa4", f"\u7121\u6cd5\u958b\u555f\u6a94\u6848\uff1a\n{e}")
                return

        doc_id = self._next_doc_id
        self._next_doc_id += 1
        self.loaded_docs[doc_id] = doc
        self._source_files.append(path)

        # Add pages
        for i in range(len(doc)):
            self.pages.append(PageItem(doc, doc_id, i, path))

        # Update file list
        self.file_listbox.insert("end", os.path.basename(path))
        self._refresh_thumbnails()
        self._update_status()

    def _on_open(self):
        paths = filedialog.askopenfilenames(
            title="\u958b\u555f\u6a94\u6848",  # \u958b\u555f\u6a94\u6848
            filetypes=[
                ("PDF \u8207\u5716\u7247", "*.pdf *.png *.jpg *.jpeg *.bmp *.tiff *.tif *.gif *.webp"),  # PDF \u8207\u5716\u7247
                ("PDF", "*.pdf"),
                ("\u5716\u7247", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.gif *.webp"),  # \u5716\u7247
                ("\u6240\u6709\u6a94\u6848", "*.*"),  # \u6240\u6709\u6a94\u6848
            ],
        )
        if not paths:
            return
        # Clear current
        self._save_undo()
        self.pages.clear()
        self.selected.clear()
        self.file_listbox.delete(0, "end")
        self.loaded_docs.clear()
        self._source_files.clear()
        self.cache.clear()

        for p in paths:
            self._load_file(p)

    def _on_add(self):
        paths = filedialog.askopenfilenames(
            title="\u52a0\u5165\u6a94\u6848",  # \u52a0\u5165\u6a94\u6848
            filetypes=[
                ("PDF \u8207\u5716\u7247", "*.pdf *.png *.jpg *.jpeg *.bmp *.tiff *.tif *.gif *.webp"),  # PDF \u8207\u5716\u7247
                ("PDF", "*.pdf"),
                ("\u5716\u7247", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.gif *.webp"),  # \u5716\u7247
                ("\u6240\u6709\u6a94\u6848", "*.*"),  # \u6240\u6709\u6a94\u6848
            ],
        )
        if not paths:
            return
        self._save_undo()
        for p in paths:
            self._load_file(p)

    def _on_remove_file(self):
        sel = self.file_listbox.curselection()
        if not sel:
            return
        self._save_undo()
        for idx in reversed(sel):
            if idx < len(self._source_files):
                src = self._source_files[idx]
                self.pages = [p for p in self.pages if p.source_file != src]
                self._source_files.pop(idx)
                self.file_listbox.delete(idx)
        self.selected.clear()
        self._refresh_thumbnails()
        self._update_status()

    def _on_save(self):
        if not self.pages:
            return
        if len(self._source_files) == 1:
            self._do_save(self._source_files[0])
        else:
            self._on_save_as()

    def _on_save_as(self):
        if not self.pages:
            return
        path = filedialog.asksaveasfilename(
            title="\u53e6\u5b58\u65b0\u6a94",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")]
        )
        if path:
            self._do_save(path)

    def _do_save(self, path: str):
        # Always write to a sibling temp file first. This avoids PyMuPDF's
        # "cannot remove file ... Permission denied" when the target path is
        # the same file that's currently open in self.loaded_docs (Windows
        # won't let us delete a file that still has an open handle).
        try:
            merged = fitz.open()
            for page_item in self.pages:
                merged.insert_pdf(page_item.doc,
                                  from_page=page_item.page_num,
                                  to_page=page_item.page_num)
                if page_item.rotation_extra:
                    p = merged[-1]
                    p.set_rotation((p.rotation + page_item.rotation_extra) % 360)

            tmp_path = f"{path}.saving-{os.getpid()}.tmp"
            pdf_engine.save_pdf(merged, tmp_path)
            merged.close()
        except Exception as e:
            messagebox.showerror("\u5132\u5b58\u5931\u6557", str(e))  # 儲存失敗
            return

        # Detect if we're overwriting a file that is currently loaded, and if
        # so, release all doc handles pointing at it BEFORE replacing, then
        # reload after. Normalise paths for robust comparison on Windows.
        target_norm = os.path.normcase(os.path.abspath(path))
        is_overwriting_loaded = any(
            os.path.normcase(os.path.abspath(s)) == target_norm
            for s in self._source_files
        )

        # Snapshot current page order / rotations so we can rebuild the exact
        # working set from the fresh saved file.
        if is_overwriting_loaded:
            # After save, every page in self.pages is now represented
            # sequentially in the saved file — so we only need to reopen path
            # and map pages 0..N-1 to it. Rotations were already baked in.
            self._release_all_docs()

        try:
            os.replace(tmp_path, path)
        except Exception as e:
            # Best-effort cleanup of temp file
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            messagebox.showerror(
                "\u5132\u5b58\u5931\u6557",  # 儲存失敗
                f"\u7121\u6cd5\u8986\u5beb\u539f\u6a94\uff1a\n{e}",  # 無法覆寫原檔：
            )
            return

        if is_overwriting_loaded:
            # Rebuild working set from the freshly saved file
            self._reload_single_file(path)

        self.status_var.set(f"\u5df2\u5132\u5b58\uff1a{os.path.basename(path)}")
        messagebox.showinfo(
            "\u5b8c\u6210", f"\u5df2\u5132\u5b58\u81f3\uff1a\n{path}"  # 完成 / 已儲存至：
        )

    def _release_all_docs(self):
        """Close every open fitz.Document and clear page/file state.

        Must be called before overwriting any file whose handle we hold,
        because Windows rejects deletion of files with live handles.
        """
        for doc in list(self.loaded_docs.values()):
            try:
                doc.close()
            except Exception:
                pass
        self.loaded_docs.clear()
        self.pages.clear()
        self._source_files.clear()
        self.selected.clear()
        self.file_listbox.delete(0, "end")

    def _reload_single_file(self, path: str):
        """Reload a single PDF as the current working set."""
        self._load_file(path)
        self._refresh_thumbnails()
        self._update_status()

    # ── Drag & Drop (External Files) ─────────────────────────────────

    def _on_dnd_enter(self, event):
        self.canvas.configure(bg="#d0e8ff")

    def _on_dnd_leave(self, event):
        self.canvas.configure(bg="#f0f0f0")

    def _on_dnd_drop(self, event):
        self.canvas.configure(bg="#f0f0f0")
        # Parse dropped file paths (handles spaces in braces)
        raw = event.data
        paths = self._parse_dnd_paths(raw)

        self._save_undo()
        for p in paths:
            p = p.strip()
            ext = os.path.splitext(p)[1].lower()
            if ext == ".pdf" or ext in self.IMG_EXTENSIONS:
                self._load_file(p)
        self._refresh_thumbnails()
        self._update_status()

    def _parse_dnd_paths(self, raw: str) -> list[str]:
        """Parse DnD file paths — handles {path with spaces} format."""
        paths = []
        i = 0
        while i < len(raw):
            if raw[i] == '{':
                end = raw.index('}', i)
                paths.append(raw[i + 1:end])
                i = end + 2
            elif raw[i] == ' ':
                i += 1
            else:
                end = raw.find(' ', i)
                if end == -1:
                    end = len(raw)
                paths.append(raw[i:end])
                i = end + 1
        return paths

    # ── Page Operations ──────────────────────────────────────────────

    def _on_rotate(self, angle: int):
        if not self.selected:
            messagebox.showinfo("\u63d0\u793a", "\u8acb\u5148\u9078\u53d6\u8981\u65cb\u8f49\u7684\u9801\u9762")
            return
        self._save_undo()
        for idx in self.selected:
            self.pages[idx].rotation_extra = (self.pages[idx].rotation_extra + angle) % 360
            self.cache.invalidate_page(self.pages[idx].doc_id, self.pages[idx].page_num)
        self._refresh_thumbnails()

    def _on_delete(self):
        if not self.selected:
            return
        self._save_undo()
        self.pages = [p for i, p in enumerate(self.pages) if i not in self.selected]
        self.selected.clear()
        self._refresh_thumbnails()
        self._update_status()

    def _on_extract(self):
        if not self.selected:
            messagebox.showinfo("\u63d0\u793a", "\u8acb\u5148\u9078\u53d6\u8981\u63d0\u53d6\u7684\u9801\u9762")
            return
        path = filedialog.asksaveasfilename(
            title="\u63d0\u53d6\u9801\u9762\u53e6\u5b58\u70ba",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")]
        )
        if not path:
            return

        merged = fitz.open()
        for idx in sorted(self.selected):
            pi = self.pages[idx]
            merged.insert_pdf(pi.doc, from_page=pi.page_num, to_page=pi.page_num)
            if pi.rotation_extra:
                p = merged[-1]
                p.set_rotation((p.rotation + pi.rotation_extra) % 360)
        pdf_engine.save_pdf(merged, path)
        merged.close()
        messagebox.showinfo("\u5b8c\u6210", f"\u5df2\u63d0\u53d6 {len(self.selected)} \u9801\u81f3\uff1a\n{path}")

    def _on_select_all(self):
        self.selected = set(range(len(self.pages)))
        self._refresh_thumbnails()
        self._update_status()

    # ── Advanced Operations ──────────────────────────────────────────

    def _get_working_doc(self) -> fitz.Document | None:
        """Build a merged document from current pages."""
        if not self.pages:
            messagebox.showinfo("\u63d0\u793a", "\u8acb\u5148\u8f09\u5165 PDF \u6a94\u6848")
            return None
        merged = fitz.open()
        for pi in self.pages:
            merged.insert_pdf(pi.doc, from_page=pi.page_num, to_page=pi.page_num)
            if pi.rotation_extra:
                p = merged[-1]
                p.set_rotation((p.rotation + pi.rotation_extra) % 360)
        return merged

    def _replace_with_doc(self, new_doc: fitz.Document, label: str = "processed"):
        """Replace all pages with a new document."""
        doc_id = self._next_doc_id
        self._next_doc_id += 1
        self.loaded_docs[doc_id] = new_doc

        self.pages.clear()
        self.selected.clear()
        for i in range(len(new_doc)):
            self.pages.append(PageItem(new_doc, doc_id, i, label))

        self.cache.clear()
        self._refresh_thumbnails()
        self._update_status()

    def _on_watermark(self):
        if not self.pages:
            return
        dlg = WatermarkDialog(self.root)
        self.root.wait_window(dlg)
        if dlg.result is None:
            return
        self._save_undo()
        doc = self._get_working_doc()
        result = pdf_engine.add_text_watermark(
            doc,
            text=dlg.result["text"],
            font_size=dlg.result["font_size"],
            opacity=dlg.result["opacity"],
            angle=dlg.result["angle"],
            color=dlg.result["color"],
        )
        doc.close()
        self._replace_with_doc(result, "watermarked")
        self.status_var.set("\u5df2\u52a0\u6d6e\u6c34\u5370")

    def _on_signature(self):
        if not self.pages:
            messagebox.showinfo("\u63d0\u793a", "\u8acb\u5148\u8f09\u5165 PDF \u6a94\u6848")
            return

        # Build a working doc so the dialog can preview any page
        working = self._get_working_doc()
        if working is None:
            return

        # Translate current page-selection indices (which match working doc)
        dlg = SignatureDialog(self.root, working, set(self.selected))
        self.root.wait_window(dlg)

        if dlg.result is None:
            working.close()
            return

        self._save_undo()
        try:
            result = pdf_engine.add_signature(
                working,
                png_path=dlg.result["png_path"],
                page_indices=dlg.result["page_indices"],
                x_ratio=dlg.result["x_ratio"],
                y_ratio=dlg.result["y_ratio"],
                width_ratio=dlg.result["width_ratio"],
                height_ratio=dlg.result["height_ratio"],
            )
        except Exception as e:
            working.close()
            messagebox.showerror("\u7c3d\u540d\u5931\u6557", str(e))
            return

        working.close()
        self._replace_with_doc(result, "signed")
        self.status_var.set(
            f"\u5df2\u5728 {len(dlg.result['page_indices'])} \u9801\u52a0\u5165\u7c3d\u540d"
        )

    def _on_add_symbols(self):
        if not self.pages:
            messagebox.showinfo("\u63d0\u793a", "\u8acb\u5148\u8f09\u5165 PDF \u6a94\u6848")
            return

        working = self._get_working_doc()
        if working is None:
            return

        dlg = SymbolDialog(self.root, working, set(self.selected))
        self.root.wait_window(dlg)

        if dlg.result is None:
            working.close()
            return

        self._save_undo()
        try:
            result = pdf_engine.add_symbols(working, placements=dlg.result)
        except Exception as e:
            working.close()
            messagebox.showerror(
                "\u7b26\u865f\u5beb\u5165\u5931\u6557", str(e)  # 符號寫入失敗
            )
            return

        working.close()
        self._replace_with_doc(result, "symbols")
        # Count distinct affected pages
        affected = len({p["page_idx"] for p in dlg.result})
        self.status_var.set(
            f"\u5df2\u5728 {affected} \u9801\u52a0\u5165 {len(dlg.result)} \u500b\u7b26\u865f"
            # 已在 N 頁加入 M 個符號
        )

    def _on_encrypt(self):
        if not self.pages:
            return
        dlg = EncryptDialog(self.root)
        self.root.wait_window(dlg)
        if dlg.result is None:
            return

        path = filedialog.asksaveasfilename(
            title="\u5132\u5b58\u52a0\u5bc6 PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")]
        )
        if not path:
            return

        doc = self._get_working_doc()
        try:
            pdf_engine.save_encrypted(doc, path, dlg.result["password"])
            doc.close()
            messagebox.showinfo("\u5b8c\u6210", f"\u5df2\u52a0\u5bc6\u5132\u5b58\u81f3\uff1a\n{path}")
        except Exception as e:
            messagebox.showerror("\u52a0\u5bc6\u5931\u6557", str(e))

    def _on_decrypt(self):
        path = filedialog.askopenfilename(
            title="\u9078\u64c7\u52a0\u5bc6\u7684 PDF",
            filetypes=[("PDF", "*.pdf")]
        )
        if not path:
            return
        dlg = DecryptDialog(self.root)
        self.root.wait_window(dlg)
        if dlg.result is None:
            return
        self._save_undo()
        self._load_file(path, dlg.result["password"])

    def _on_compress(self):
        if not self.pages:
            return
        doc = self._get_working_doc()
        original_size = sum(
            os.path.getsize(f) for f in set(self._source_files) if os.path.exists(f)
        )
        self._save_undo()
        compressed = pdf_engine.compress_pdf(doc)
        doc.close()
        self._replace_with_doc(compressed, "compressed")

        # Save to get new size
        import tempfile
        tmp = os.path.join(tempfile.gettempdir(), "_pdf_master_size_check.pdf")
        pdf_engine.save_pdf(compressed, tmp)
        new_size = os.path.getsize(tmp)
        os.remove(tmp)

        if original_size > 0:
            ratio = (1 - new_size / original_size) * 100
            self.status_var.set(
                f"\u58d3\u7e2e\u5b8c\u6210\uff1a{original_size // 1024}KB \u2192 {new_size // 1024}KB "
                f"(\u6e1b\u5c11 {ratio:.1f}%)"
            )
        else:
            self.status_var.set(f"\u58d3\u7e2e\u5b8c\u6210\uff1a{new_size // 1024}KB")

    def _on_to_images(self):
        if not self.pages:
            return
        dlg = ImageExportDialog(self.root)
        self.root.wait_window(dlg)
        if dlg.result is None:
            return

        out_dir = filedialog.askdirectory(title="\u9078\u64c7\u8f38\u51fa\u8cc7\u6599\u593e")
        if not out_dir:
            return

        doc = self._get_working_doc()
        indices = sorted(self.selected) if self.selected else list(range(len(self.pages)))

        paths = pdf_engine.pdf_to_images(
            doc, indices, out_dir,
            fmt=dlg.result["fmt"],
            dpi=dlg.result["dpi"]
        )
        doc.close()
        messagebox.showinfo("\u5b8c\u6210",
                            f"\u5df2\u8f38\u51fa {len(paths)} \u5f35\u5716\u7247\u81f3\uff1a\n{out_dir}")

    def _on_images_to_pdf(self):
        paths = filedialog.askopenfilenames(
            title="\u9078\u64c7\u5716\u7247\u6a94\u6848",
            filetypes=[
                ("\u5716\u7247", "*.png *.jpg *.jpeg *.bmp *.tiff *.gif"),
                ("\u6240\u6709\u6a94\u6848", "*.*")
            ]
        )
        if not paths:
            return
        self._save_undo()
        try:
            doc = pdf_engine.images_to_pdf(list(paths))
            doc_id = self._next_doc_id
            self._next_doc_id += 1
            self.loaded_docs[doc_id] = doc
            label = f"{len(paths)} images"
            self._source_files.append(label)
            self.file_listbox.insert("end", f"\u5716\u7247 ({len(paths)} \u5f35)")
            for i in range(len(doc)):
                self.pages.append(PageItem(doc, doc_id, i, label))
            self._refresh_thumbnails()
            self._update_status()
        except Exception as e:
            messagebox.showerror("\u932f\u8aa4", f"\u5716\u7247\u8f49 PDF \u5931\u6557\uff1a\n{e}")

    def _on_crop(self):
        if not self.pages:
            return
        dlg = CropDialog(self.root)
        self.root.wait_window(dlg)
        if dlg.result is None:
            return
        self._save_undo()
        doc = self._get_working_doc()
        indices = sorted(self.selected) if self.selected else list(range(len(self.pages)))
        result = pdf_engine.crop_pages(doc, indices, **dlg.result)
        doc.close()
        self._replace_with_doc(result, "cropped")
        self.status_var.set(f"\u5df2\u88c1\u5207 {len(indices)} \u9801")

    def _on_page_numbers(self):
        if not self.pages:
            return
        dlg = PageNumberDialog(self.root)
        self.root.wait_window(dlg)
        if dlg.result is None:
            return
        self._save_undo()
        doc = self._get_working_doc()
        result = pdf_engine.add_page_numbers(doc, **dlg.result)
        doc.close()
        self._replace_with_doc(result, "numbered")
        self.status_var.set("\u5df2\u52a0\u9801\u78bc")

    # ── Thumbnail Grid Rendering ─────────────────────────────────────

    def _on_canvas_resize(self, event=None):
        self._refresh_thumbnails()

    def _refresh_thumbnails(self):
        """Redraw the thumbnail grid."""
        self.canvas.delete("all")
        self._photo_refs.clear()

        if not self.pages:
            # Show drop hint
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            self.canvas.create_text(
                cw // 2, ch // 2,
                text="\u62d6\u653e PDF \u6a94\u6848\u5230\u6b64\u8655\n\u6216\u9ede\u64ca\u300c\u958b\u555f\u6a94\u6848\u300d",
                font=("", 14), fill="#999",
                justify="center"
            )
            return

        cw = max(self.canvas.winfo_width(), 400)
        cols = max(1, cw // self.CELL_W)

        total_rows = (len(self.pages) + cols - 1) // cols
        total_h = total_rows * self.CELL_H + 20

        self.canvas.configure(scrollregion=(0, 0, cw, total_h))

        for idx, page_item in enumerate(self.pages):
            row = idx // cols
            col = idx % cols

            x = col * self.CELL_W + self.CELL_W // 2
            y = row * self.CELL_H + 10 + self.THUMB_H // 2

            # Selection highlight
            is_selected = idx in self.selected
            if is_selected:
                rx0 = col * self.CELL_W + 5
                ry0 = row * self.CELL_H + 5
                rx1 = rx0 + self.CELL_W - 10
                ry1 = ry0 + self.CELL_H - 10
                self.canvas.create_rectangle(
                    rx0, ry0, rx1, ry1,
                    fill="#cce5ff", outline="#4a90d9", width=2,
                    tags=f"sel_{idx}"
                )

            # Drag indicator
            if self._drag_target_idx is not None and idx == self._drag_target_idx:
                line_x = col * self.CELL_W
                self.canvas.create_line(
                    line_x, row * self.CELL_H + 5,
                    line_x, row * self.CELL_H + self.CELL_H - 5,
                    fill="red", width=3
                )

            # Render thumbnail async
            self._render_thumb(page_item, idx, x, y)

            # Page label
            label_y = y + self.THUMB_H // 2 + 12
            label_text = f"P{idx + 1}"
            self.canvas.create_text(
                x, label_y, text=label_text,
                font=("", 9), fill="#333",
                tags=f"label_{idx}"
            )

    def _render_thumb(self, page_item: PageItem, idx: int, x: int, y: int):
        """Render a single page thumbnail."""
        def on_rendered(doc_id, page_num, photo):
            self.canvas.after(0, lambda: self._place_thumb(idx, x, y, photo))

        # Apply extra rotation for rendering
        if page_item.rotation_extra:
            page = page_item.doc[page_item.page_num]
            orig_rot = page.rotation
            page.set_rotation((orig_rot + page_item.rotation_extra) % 360)
            self.renderer.render_async(
                page_item.doc, page_item.doc_id, page_item.page_num,
                self.THUMB_W, self.THUMB_H, on_rendered
            )
            page.set_rotation(orig_rot)
        else:
            self.renderer.render_async(
                page_item.doc, page_item.doc_id, page_item.page_num,
                self.THUMB_W, self.THUMB_H, on_rendered
            )

    def _place_thumb(self, idx: int, x: int, y: int, photo: ImageTk.PhotoImage):
        """Place a rendered thumbnail on the canvas."""
        self._photo_refs.append(photo)  # prevent GC
        tag = f"thumb_{idx}"
        self.canvas.delete(tag)

        # Shadow
        self.canvas.create_rectangle(
            x - photo.width() // 2 + 3, y - photo.height() // 2 + 3,
            x + photo.width() // 2 + 3, y + photo.height() // 2 + 3,
            fill="#ccc", outline="", tags=tag
        )
        # Image
        self.canvas.create_image(x, y, image=photo, tags=tag)
        # Border
        self.canvas.create_rectangle(
            x - photo.width() // 2, y - photo.height() // 2,
            x + photo.width() // 2, y + photo.height() // 2,
            outline="#aaa", width=1, tags=tag
        )

    # ── Canvas Interaction ───────────────────────────────────────────

    def _idx_from_xy(self, x: int, y: int) -> int | None:
        """Get page index from canvas coordinates."""
        if not self.pages:
            return None
        # Account for scroll
        cy = self.canvas.canvasy(y)
        cx = x

        cw = max(self.canvas.winfo_width(), 400)
        cols = max(1, cw // self.CELL_W)

        col = cx // self.CELL_W
        row = int(cy) // self.CELL_H

        if col >= cols:
            return None

        idx = row * cols + col
        if 0 <= idx < len(self.pages):
            return idx
        return None

    def _on_canvas_click(self, event):
        idx = self._idx_from_xy(event.x, event.y)
        self._drag_start_idx = idx

        if idx is None:
            self.selected.clear()
        else:
            self.selected = {idx}

        self._refresh_thumbnails()
        self._update_status()

    def _on_canvas_ctrl_click(self, event):
        idx = self._idx_from_xy(event.x, event.y)
        if idx is None:
            return
        if idx in self.selected:
            self.selected.discard(idx)
        else:
            self.selected.add(idx)
        self._refresh_thumbnails()
        self._update_status()

    def _on_canvas_shift_click(self, event):
        idx = self._idx_from_xy(event.x, event.y)
        if idx is None:
            return
        if self.selected:
            min_sel = min(self.selected)
            max_sel = max(self.selected)
            if idx < min_sel:
                for i in range(idx, max_sel + 1):
                    self.selected.add(i)
            else:
                for i in range(min_sel, idx + 1):
                    self.selected.add(i)
        else:
            self.selected = {idx}
        self._refresh_thumbnails()
        self._update_status()

    def _on_canvas_drag(self, event):
        if self._drag_start_idx is None:
            return
        target = self._idx_from_xy(event.x, event.y)
        if target is not None and target != self._drag_target_idx:
            self._drag_target_idx = target
            self._refresh_thumbnails()

    def _on_canvas_drop(self, event):
        if (self._drag_start_idx is not None and
                self._drag_target_idx is not None and
                self._drag_start_idx != self._drag_target_idx):
            self._save_undo()
            # Move page
            page = self.pages.pop(self._drag_start_idx)
            insert_at = self._drag_target_idx
            if self._drag_start_idx < insert_at:
                insert_at -= 1
            self.pages.insert(insert_at, page)
            self.selected = {insert_at}
            self._refresh_thumbnails()
            self._update_status()

        self._drag_start_idx = None
        self._drag_target_idx = None

    def _on_right_click(self, event):
        idx = self._idx_from_xy(event.x, event.y)
        if idx is None:
            return
        if idx not in self.selected:
            self.selected = {idx}
            self._refresh_thumbnails()

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="\u5411\u5de6\u65cb\u8f49 90\u00b0", command=lambda: self._on_rotate(-90))
        menu.add_command(label="\u5411\u53f3\u65cb\u8f49 90\u00b0", command=lambda: self._on_rotate(90))
        menu.add_separator()
        menu.add_command(label="\u522a\u9664", command=self._on_delete)
        menu.add_command(label="\u63d0\u53d6\u53e6\u5b58", command=self._on_extract)
        menu.add_separator()
        menu.add_command(label="\u5168\u9078", command=self._on_select_all)
        menu.tk_popup(event.x_root, event.y_root)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    # ── Status ───────────────────────────────────────────────────────

    def _update_status(self):
        total = len(self.pages)
        sel = len(self.selected)
        if total == 0:
            self.status_var.set("\u62d6\u653e PDF \u6a94\u6848\u5230\u6b64\u8655\u958b\u59cb")
        elif sel > 0:
            self.status_var.set(f"\u5171 {total} \u9801 | \u5df2\u9078 {sel} \u9801")
        else:
            self.status_var.set(f"\u5171 {total} \u9801")

    # ── Run ──────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PDFMasterApp()
    app.run()
