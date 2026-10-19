"""QML catalog state with request identity checks for rapid navigation/search."""

from collections import OrderedDict
import json
from pathlib import Path
import time

from PySide6.QtCore import QObject, Property, Signal, Slot


class CatalogView(QObject):
    changed = Signal()
    navigationStarted = Signal()

    def __init__(self, worker, cache_path, account, parent=None):
        super().__init__(parent)
        self.worker, self.account = worker, account
        self.cache_path = str(Path(cache_path))
        self._request = None
        self._route, self._params = "home", {}
        self._data = {}
        self._busy, self._error, self._append = False, "", False
        self._revision, self._scroll = 0, None
        self._pages = OrderedDict()
        self._loaded_at = None
        self._identity = self._account_identity()
        if worker:
            worker.succeeded.connect(self._succeeded)
            worker.failed.connect(self._failed)
            if hasattr(worker, "progress"):
                worker.progress.connect(self._progress)

    def _account_identity(self):
        profile = getattr(self.account, "profile", {})
        return tuple(profile.get(key, "") for key in ("name", "handle"))

    def accountChanged(self):
        identity = self._account_identity()
        if identity != self._identity:
            self._identity = identity
            self.invalidate()
            self._cancel()
            if not self._data.get("downloadKey") and self._route != "downloads":
                self._data = {}
            self.changed.emit()

    def invalidate(self):
        self._pages.clear()
        self._loaded_at = None

    def _key(self):
        return json.dumps([self._route, self._params], sort_keys=True)

    def _remember(self):
        if self._loaded_at is None or not self._data:
            return
        count = len(self._data.get("items", [])) + sum(len(s.get("items", [])) for s in self._data.get("shelves", []))
        # Large paginated collections stay in the worker's disk cache.
        if count > 400:
            self._pages.pop(self._key(), None)
            return
        self._pages[self._key()] = (self._data, self._scroll, self._loaded_at)
        self._pages.move_to_end(self._key())
        while len(self._pages) > 12:
            self._pages.popitem(last=False)

    def _cancel(self):
        if self.worker and self._request is not None:
            self.worker.cancelQueued(self._request)
        self._request, self._busy, self._error = None, False, ""

    @Property("QVariantMap", notify=changed)
    def data(self):
        return self._data

    @Property(bool, notify=changed)
    def hasData(self):
        return bool(self._data)

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(str, notify=changed)
    def error(self):
        return self._error

    @Property(str, notify=changed)
    def route(self):
        return self._route

    @Property("QVariantMap", notify=changed)
    def parameters(self):
        return self._params

    @Property(int, notify=changed)
    def revision(self):
        return self._revision

    @Property(float, notify=changed)
    def scrollPosition(self):
        return self._scroll if self._scroll is not None else 0.

    @Property(bool, notify=changed)
    def hasScrollPosition(self):
        return self._scroll is not None

    @Slot(float)
    def saveScroll(self, value):
        self._scroll = float(value)

    @Slot(str, "QVariantMap")
    def load(self, route, params):
        if self._busy and route == self._route and dict(params) == self._params:
            return
        self.navigationStarted.emit()
        self._remember()
        self._cancel()
        self._route, self._params = route, dict(params)
        self._data = {}
        self._loaded_at = None
        self._revision, self._scroll = self._revision + 1, None
        cached = self._pages.get(self._key())
        if cached:
            self._data, self._scroll, self._loaded_at = cached
            self._pages.move_to_end(self._key())
            if time.monotonic() - self._loaded_at < 60 and not self._data.get("stale"):
                self.changed.emit()
                return
        count = max(len(self._data.get("items", [])), len(self._data.get("shelves", [])))
        self._send(page_size=count or None)

    def showLocal(self, route, data, params=None, scroll=None):
        self.navigationStarted.emit()
        self._remember()
        self._cancel()
        self._loaded_at = None
        self._route, self._data = route, dict(data)
        self._params = dict(params or {})
        self._revision, self._scroll = self._revision + 1, scroll
        self.changed.emit()

    def snapshot(self):
        return {"route": self._route, "params": self._params, "data": self._data, "scroll": self._scroll}

    def patch(self, values):
        self._data.update(values)
        self.changed.emit()

    @Slot()
    def refresh(self):
        count = max(len(self._data.get("items", [])), len(self._data.get("shelves", [])))
        self._revision += 1
        self._pages.pop(self._key(), None)
        self._loaded_at = None
        self._send(refresh=True, page_size=count or None)

    @Slot()
    def more(self):
        if not self._busy and self._data.get("cursor") is not None:
            self._send(offset=self._data["cursor"])

    def _send(self, offset=0, refresh=False, page_size=None):
        if not self.worker:
            self.changed.emit()
            return
        if self._request is not None:
            self.worker.cancelQueued(self._request)
        self._busy, self._error, self._append = True, "", offset > 0
        self._request = self.worker.request("catalog", {"cache_path": self.cache_path, "route": self._route, "params": self._params, "offset": offset, "refresh": refresh, "page_size": page_size, "preview_cached": not self._data and not offset and not refresh})
        self.changed.emit()

    def _progress(self, identifier, result):
        if identifier == self._request and not self._append and not self._data and isinstance(result.get("cached_page"), dict):
            self._data = result["cached_page"]
            self.changed.emit()

    def _succeeded(self, identifier, result):
        if result.get("action") or result.get("recorded"):
            self.invalidate()
        if identifier != self._request:
            return
        if self._append:
            result["items"] = self._data.get("items", []) + result.get("items", [])
            result["shelves"] = self._data.get("shelves", []) + result.get("shelves", [])
        self._data, self._busy, self._request = result, False, None
        self._loaded_at = time.monotonic() if not result.get("stale") else None
        self._remember()
        if result.get("warning") == "reconnect":
            self.account.requireReconnect("Your session needs reconnecting. Cached music remains available.")
        self.changed.emit()

    def _failed(self, identifier, error):
        if identifier != self._request:
            return
        self._busy, self._request = False, None
        self._error = error.get("message", "This page could not be loaded. Retry.")
        if error.get("code") in {"reconnect", "AuthError"}:
            self.account.requireReconnect(self._error)
        self.changed.emit()
