"""Asynchronous Qt transport for the existing private application API."""
import json
from urllib.parse import urlencode

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


class ApiClient(QObject):
    ready = Signal()
    failed = Signal(str)

    def __init__(self, base_url, parent=None):
        super().__init__(parent)
        self.base_url = base_url.rstrip("/")
        self.network = QNetworkAccessManager(self)
        self.authenticated = False
        self.pending = []
        # The bootstrap response sets the process-local HttpOnly session cookie.
        # Its HTML is discarded; there is no browser or HTML renderer in this UI.
        reply = self.network.get(QNetworkRequest(QUrl(self.base_url + "/")))
        def bootstrap():
            ok = reply.error() == QNetworkReply.NetworkError.NoError
            reply.deleteLater()
            if not ok:
                self.failed.emit("Não foi possível conectar ao serviço local.")
                return
            self.authenticated = True
            pending, self.pending = self.pending, []
            for call in pending:
                call()
            self.ready.emit()
        reply.finished.connect(bootstrap)

    def request(self, path, callback, *, method="GET", data=None, error=None, binary=False):
        if not self.authenticated:
            self.pending.append(lambda: self.request(path, callback, method=method, data=data, error=error, binary=binary))
            return None
        request = QNetworkRequest(QUrl(self.base_url + path))
        request.setTransferTimeout(180_000)
        request.setRawHeader(b"Content-Type", b"application/json")
        reply = self.network.sendCustomRequest(request, method.encode(), json.dumps(data).encode() if data is not None else b"")
        def finish():
            raw = bytes(reply.readAll())
            try:
                if reply.error() != QNetworkReply.NetworkError.NoError:
                    try:
                        message = json.loads(raw).get("error", reply.errorString())
                    except (ValueError, AttributeError):
                        message = reply.errorString()
                    raise ValueError(message)
                callback(raw if binary else json.loads(raw))
            except (ValueError, TypeError) as exc:
                (error or self.failed.emit)(str(exc))
            finally:
                reply.deleteLater()
        reply.finished.connect(finish)
        return reply

    def search(self, body, event, finished):
        request = QNetworkRequest(QUrl(self.base_url + "/api/search-stream"))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        request.setTransferTimeout(180_000)
        reply = self.network.post(request, json.dumps(body).encode())
        buffer = bytearray()
        decoder = EventDecoder(event)
        def read():
            buffer.extend(bytes(reply.readAll()))
            if "text/event-stream" in str(reply.header(QNetworkRequest.KnownHeaders.ContentTypeHeader)):
                decoder.feed(bytes(buffer))
                buffer.clear()
        reply.readyRead.connect(read)
        def done():
            read()
            cancelled = reply.error() == QNetworkReply.NetworkError.OperationCanceledError
            error = None
            if not cancelled:
                if reply.error() != QNetworkReply.NetworkError.NoError:
                    try:
                        error = json.loads(buffer).get("error", reply.errorString())
                    except (ValueError, AttributeError):
                        error = reply.errorString()
                elif buffer:
                    try:
                        payload = json.loads(buffer)
                        event("posts", payload)
                        event("done", payload)
                    except ValueError:
                        error = "Resposta de busca inválida."
            finished(error, cancelled)
            reply.deleteLater()
        reply.finished.connect(done)
        return reply

    @staticmethod
    def media_path(post, *, preview=True):
        if post.get("rel_path"):
            return ("/api/thumb?" if preview else "/api/file?") + urlencode({"rel_path": post["rel_path"]})
        url = (post.get("preview_url") if preview else None) or post.get("url") or post.get("orig_url") or post.get("preview_url") or ""
        from .models import media_type
        endpoint = "/api/proxy-video?" if media_type({"url": url}) == "video" else "/api/proxy-image?"
        return endpoint + urlencode({"url": url})


class EventDecoder:
    """Parse SSE incrementally, including split UTF-8 and CRLF boundaries."""
    def __init__(self, callback):
        self.callback = callback
        self.buffer = b""
        self.name = "message"
        self.lines = []

    def feed(self, data):
        self.buffer += data
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            line = line.rstrip(b"\r").decode("utf-8")
            if not line:
                if self.lines:
                    try:
                        self.callback(self.name, json.loads("\n".join(self.lines)))
                    except ValueError:
                        pass
                self.name, self.lines = "message", []
            elif line.startswith("event:"):
                self.name = line[6:].strip()
            elif line.startswith("data:"):
                self.lines.append(line[5:].lstrip())
