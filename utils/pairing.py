"""Short-lived encrypted desktop-to-mobile configuration pairing.

The desktop serves only an AES-GCM ciphertext over the local network. The
decryption key lives in the QR/pairing code and is never included in the HTTP
request, response, logs, or persistent files.
"""

from __future__ import annotations

import atexit
import base64
import io
import ipaddress
import json
import secrets
import socket
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable


PAIRING_PREFIX = "artfinder-pair:v1:"
PAIRING_AAD = b"ArtFinder pairing v1"
PAIRING_TTL_SECONDS = 5 * 60
MAX_PAIRING_PAYLOAD_BYTES = 512 * 1024


class PairingError(RuntimeError):
    """Raised when a pairing session cannot be created safely."""


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def discover_lan_ipv4_addresses() -> list[str]:
    """Return private IPv4 addresses that another local device can reach."""
    candidates: set[str] = set()

    # The UDP socket does not send data; connect() only asks the OS which local
    # interface would be used for a normal internet route.
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("192.0.2.1", 9))
            candidates.add(probe.getsockname()[0])
        finally:
            probe.close()
    except OSError:
        pass

    try:
        for entry in socket.getaddrinfo(
            socket.gethostname(), None, socket.AF_INET, socket.SOCK_STREAM
        ):
            candidates.add(entry[4][0])
    except OSError:
        pass

    addresses = []
    for candidate in candidates:
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if (
            address.version == 4
            and address.is_private
            and not address.is_loopback
            and not address.is_link_local
            and not address.is_multicast
            and not address.is_unspecified
        ):
            addresses.append(str(address))
    return sorted(set(addresses))


def encrypt_payload(payload: dict[str, Any], key: bytes, nonce: bytes) -> bytes:
    """Serialize and encrypt a pairing payload with authenticated encryption."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    plaintext = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(plaintext) > MAX_PAIRING_PAYLOAD_BYTES:
        raise PairingError("A configuracao e grande demais para o pareamento")
    return AESGCM(key).encrypt(nonce, plaintext, PAIRING_AAD)


def decrypt_payload(envelope: dict[str, Any], key: bytes) -> dict[str, Any]:
    """Decrypt an envelope; primarily shared with deterministic unit tests."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if envelope.get("version") != 1 or envelope.get("algorithm") != "AES-256-GCM":
        raise PairingError("Formato de pareamento incompativel")
    try:
        nonce = _b64decode(str(envelope["nonce"]))
        ciphertext = _b64decode(str(envelope["ciphertext"]))
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, PAIRING_AAD)
        payload = json.loads(plaintext.decode("utf-8"))
    except Exception as exc:
        raise PairingError("O codigo de pareamento e invalido") from exc
    if not isinstance(payload, dict):
        raise PairingError("Conteudo de pareamento invalido")
    return payload


def _pairing_code(endpoint: str, key: bytes) -> str:
    descriptor = json.dumps(
        {"url": endpoint, "key": _b64encode(key)},
        separators=(",", ":"),
    ).encode("utf-8")
    return PAIRING_PREFIX + _b64encode(descriptor)


def parse_pairing_code(code: str) -> dict[str, str]:
    """Parse a code without contacting its endpoint."""
    if not isinstance(code, str) or not code.startswith(PAIRING_PREFIX):
        raise PairingError("Codigo de pareamento invalido")
    try:
        descriptor = json.loads(
            _b64decode(code[len(PAIRING_PREFIX) :].strip()).decode("utf-8")
        )
        endpoint = str(descriptor["url"])
        key = str(descriptor["key"])
        if len(_b64decode(key)) != 32:
            raise ValueError("invalid key length")
    except Exception as exc:
        raise PairingError("Codigo de pareamento invalido") from exc
    return {"url": endpoint, "key": key}


def _qr_data_uri(code: str) -> str:
    """Render a pairing code as an embedded SVG without external services."""
    import qrcode
    from qrcode.image.svg import SvgPathImage

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=7,
        border=4,
    )
    qr.add_data(code)
    qr.make(fit=True)
    image = qr.make_image(image_factory=SvgPathImage)
    output = io.BytesIO()
    image.save(output)
    return "data:image/svg+xml;base64," + base64.b64encode(output.getvalue()).decode(
        "ascii"
    )


@dataclass
class _SessionState:
    path: str
    body: bytes
    expires_at: float
    monotonic_deadline: float
    consumed: bool = False


class PairingSession:
    """A single-use HTTP endpoint holding only an encrypted envelope."""

    def __init__(
        self,
        payload: dict[str, Any],
        *,
        ttl_seconds: int = PAIRING_TTL_SECONDS,
        addresses: list[str] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds < 1 or ttl_seconds > PAIRING_TTL_SECONDS:
            raise PairingError("Tempo de pareamento invalido")

        key = secrets.token_bytes(32)
        nonce = secrets.token_bytes(12)
        ciphertext = encrypt_payload(payload, key, nonce)
        expires_at = time.time() + ttl_seconds
        envelope = {
            "version": 1,
            "algorithm": "AES-256-GCM",
            "nonce": _b64encode(nonce),
            "ciphertext": _b64encode(ciphertext),
            "expires_at": int(expires_at),
        }
        body = json.dumps(envelope, separators=(",", ":")).encode("utf-8")
        token = secrets.token_urlsafe(32)
        self._clock = clock
        self._state = _SessionState(
            path=f"/v1/pair/{token}",
            body=body,
            expires_at=expires_at,
            monotonic_deadline=clock() + ttl_seconds,
        )
        self._lock = threading.RLock()
        self._closed = False
        self._server = self._create_server()
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="artfinder-pairing",
            daemon=True,
        )
        self._thread.start()
        self._timer = threading.Timer(ttl_seconds, self.close)
        self._timer.daemon = True
        self._timer.start()

        port = int(self._server.server_address[1])
        lan_addresses = addresses if addresses is not None else discover_lan_ipv4_addresses()
        if not lan_addresses:
            self.close()
            raise PairingError(
                "Nenhum endereco de rede local foi encontrado; conecte PC e celular ao mesmo Wi-Fi"
            )
        self.options = []
        try:
            for address in lan_addresses:
                endpoint = f"http://{address}:{port}{self._state.path}"
                code = _pairing_code(endpoint, key)
                self.options.append(
                    {
                        "address": address,
                        "code": code,
                        "qr": _qr_data_uri(code),
                    }
                )
        except Exception as exc:
            self.close()
            raise PairingError("Nao foi possivel gerar o QR Code") from exc

    def _create_server(self) -> ThreadingHTTPServer:
        session = self

        class PairingHandler(BaseHTTPRequestHandler):
            def _headers(self, status: int, length: int = 0) -> None:
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(length))
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Allow-Private-Network", "true")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()

            def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib handler API
                self._headers(204)

            def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
                with session._lock:
                    expired = session._clock() >= session._state.monotonic_deadline
                    if self.path != session._state.path:
                        self._headers(404)
                        return
                    if expired or session._state.consumed:
                        self._headers(410)
                        return
                    body = session._state.body
                    session._state.consumed = True

                self._headers(200, len(body))
                self.wfile.write(body)
                self.wfile.flush()
                close_timer = threading.Timer(0.25, session.close)
                close_timer.daemon = True
                close_timer.start()

            def log_message(self, _format: str, *_args: Any) -> None:
                return

        server = ThreadingHTTPServer(("0.0.0.0", 0), PairingHandler)
        server.daemon_threads = True
        return server

    @property
    def expires_at(self) -> int:
        return int(self._state.expires_at)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._timer.cancel()
        self._server.shutdown()
        self._server.server_close()


class PairingManager:
    """Own at most one active pairing session per ArtFinder process."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._session: PairingSession | None = None

    def create(
        self,
        payload: dict[str, Any],
        *,
        ttl_seconds: int = PAIRING_TTL_SECONDS,
        addresses: list[str] | None = None,
    ) -> PairingSession:
        with self._lock:
            if self._session is not None:
                self._session.close()
                self._session = None
            session = PairingSession(
                payload,
                ttl_seconds=ttl_seconds,
                addresses=addresses,
            )
            self._session = session
            return session

    def close(self) -> None:
        with self._lock:
            if self._session is not None:
                self._session.close()
                self._session = None


pairing_manager = PairingManager()
atexit.register(pairing_manager.close)
