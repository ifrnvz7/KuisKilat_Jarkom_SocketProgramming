"""Informasi koneksi dan pemain pada server."""
import socket
from dataclasses import dataclass, field


@dataclass
class Session:
    """Menyimpan state koneksi socket dan metadata pemain."""
    player_id: str
    conn: socket.socket
    addr: tuple[str, int]
    name: str | None = None
    score: int = 0
    is_host: bool = False
    answer: tuple[int, float] | None = field(default=None)
    connected: bool = True

    def close(self) -> None:
        """Menutup dedicated connection socket secara aman (idempotent)."""
        self.connected = False
        try:
            self.conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.conn.close()
        except OSError:
            pass
