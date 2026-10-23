"""Pengiriman pesan NDJSON dari server ke client."""
from common import protocol as P
from server.session import Session


def send_to(session: Session, message_dict: dict) -> bool:
    """Kirim pesan ke satu client. False berarti koneksi perlu dibersihkan."""
    if not session.connected:
        return False
    try:
        session.conn.sendall(P.encode(message_dict))
        return True
    except OSError:
        session.close()
        return False


def broadcast(clients_dict: dict[str, Session], message_dict: dict) -> list[str]:
    """Kirim ke semua client; kembalikan ID koneksi yang gagal.

    Daftar pemain hanya boleh diubah oleh GameEngine, bukan oleh writer.
    """
    payload = P.encode(message_dict)
    dead_ids: list[str] = []

    # Pengiriman masih berurutan. ID yang gagal dikembalikan agar game thread menangani cleanup.
    for pid, session in list(clients_dict.items()):
        if not session.connected:
            dead_ids.append(pid)
            continue
        try:
            session.conn.sendall(payload)
        except OSError:
            session.close()
            dead_ids.append(pid)

    return dead_ids
