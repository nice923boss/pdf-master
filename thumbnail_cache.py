"""Thumbnail Cache — Async page thumbnail rendering with LRU cache."""

import threading
from collections import OrderedDict
from io import BytesIO
from PIL import Image, ImageTk
import fitz


class ThumbnailCache:
    """Thread-safe LRU cache for PDF page thumbnails."""

    def __init__(self, max_size: int = 500):
        self._cache: OrderedDict[str, ImageTk.PhotoImage] = OrderedDict()
        self._raw_cache: OrderedDict[str, Image.Image] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()

    def _make_key(self, doc_id: int, page_num: int, width: int, height: int,
                  rotation: int = 0) -> str:
        return f"{doc_id}:{page_num}:{width}x{height}:r{rotation}"

    def get(self, doc_id: int, page_num: int,
            width: int, height: int, rotation: int = 0) -> ImageTk.PhotoImage | None:
        """Get cached thumbnail. Returns None if not cached."""
        key = self._make_key(doc_id, page_num, width, height, rotation)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        return None

    def put(self, doc_id: int, page_num: int,
            width: int, height: int, rotation: int,
            photo: ImageTk.PhotoImage, pil_image: Image.Image):
        """Store a thumbnail in cache."""
        key = self._make_key(doc_id, page_num, width, height, rotation)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                self._cache[key] = photo
                self._raw_cache[key] = pil_image
                if len(self._cache) > self._max_size:
                    self._cache.popitem(last=False)
                    self._raw_cache.popitem(last=False)

    def invalidate_doc(self, doc_id: int):
        """Remove all cached thumbnails for a document."""
        prefix = f"{doc_id}:"
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._cache[k]
                self._raw_cache.pop(k, None)

    def invalidate_page(self, doc_id: int, page_num: int):
        """Remove cached thumbnails for a specific page."""
        prefix = f"{doc_id}:{page_num}:"
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._cache[k]
                self._raw_cache.pop(k, None)

    def clear(self):
        """Clear all cached thumbnails."""
        with self._lock:
            self._cache.clear()
            self._raw_cache.clear()


class ThumbnailRenderer:
    """Renders PDF page thumbnails in background threads."""

    def __init__(self, cache: ThumbnailCache):
        self.cache = cache
        self._pending: set[str] = set()
        self._lock = threading.Lock()

    def render_async(self, doc: fitz.Document, doc_id: int, page_num: int,
                     max_width: int, max_height: int,
                     callback: callable):
        """Render a thumbnail in a background thread.

        Args:
            callback: Called with (doc_id, page_num, PhotoImage) on completion.
                      Called in the background thread — use widget.after() to
                      update GUI from it.
        """
        page = doc[page_num]
        rotation = page.rotation
        cached = self.cache.get(doc_id, page_num, max_width, max_height, rotation)
        if cached is not None:
            callback(doc_id, page_num, cached)
            return

        key = f"{doc_id}:{page_num}:{max_width}x{max_height}:r{rotation}"
        with self._lock:
            if key in self._pending:
                return
            self._pending.add(key)

        def _do_render():
            try:
                p = doc[page_num]
                rect = p.rect

                scale_w = max_width / rect.width
                scale_h = max_height / rect.height
                scale = min(scale_w, scale_h)

                mat = fitz.Matrix(scale, scale)
                pix = p.get_pixmap(matrix=mat, alpha=False)

                png_data = pix.tobytes("png")
                pil_img = Image.open(BytesIO(png_data))
                photo = ImageTk.PhotoImage(pil_img)

                self.cache.put(doc_id, page_num, max_width, max_height,
                               rotation, photo, pil_img)
                callback(doc_id, page_num, photo)

            except Exception:
                pass
            finally:
                with self._lock:
                    self._pending.discard(key)

        thread = threading.Thread(target=_do_render, daemon=True)
        thread.start()

    def render_sync(self, doc: fitz.Document, doc_id: int, page_num: int,
                    max_width: int, max_height: int) -> ImageTk.PhotoImage:
        """Render a thumbnail synchronously (blocking). Returns PhotoImage."""
        page = doc[page_num]
        rotation = page.rotation
        cached = self.cache.get(doc_id, page_num, max_width, max_height, rotation)
        if cached is not None:
            return cached

        rect = page.rect
        scale_w = max_width / rect.width
        scale_h = max_height / rect.height
        scale = min(scale_w, scale_h)

        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        png_data = pix.tobytes("png")
        pil_img = Image.open(BytesIO(png_data))
        photo = ImageTk.PhotoImage(pil_img)

        self.cache.put(doc_id, page_num, max_width, max_height,
                       rotation, photo, pil_img)
        return photo
