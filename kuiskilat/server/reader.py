"""Membaca pesan NDJSON dari satu koneksi client."""
import queue
import socket
from common import protocol as P
from server.session import Session


def reader_thread(session: Session, event_queue: queue.Queue) -> None:
    """Membaca stream byte dari socket client, melakukan framing '\n',
    dan mengirim event terstruktur ke event_queue.
    """
    buffer = b""
    try:
        while session.connected:
            try:
                chunk = session.conn.recv(P.RECV_BUFFER_SIZE)
            except socket.timeout:
                continue  # Socket tetap terbuka selama client belum mengirim data.
            except (ConnectionError, OSError):
                # Koneksi diputus paksa oleh client (misal ConnectionResetError)
                break

            if chunk == b"":
                # EOF: Client menutup koneksi secara normal (FIN)
                break

            # TCP adalah byte stream, potongan dari recv() tidak selalu sejajar dengan satu pesan JSON.
            buffer += chunk
            lines, buffer = P.extract_lines(buffer)
            # Jangan simpan data tanpa newline tanpa batas.
            # Putuskan koneksi yang mengirim pesan terlalu panjang, termasuk tanpa newline.
            if len(buffer) > P.MAX_MESSAGE_BYTES or any(
                len(line) > P.MAX_MESSAGE_BYTES for line in lines
            ):
                break

            for raw_line in lines:
                try:
                    msg = P.decode(raw_line)
                    event_queue.put({
                        "type": "message",
                        "player_id": session.player_id,
                        "session": session,
                        "data": msg,
                    })
                except P.ProtocolError as exc:
                    event_queue.put({
                        "type": "bad_message",
                        "player_id": session.player_id,
                        "session": session,
                        "error": str(exc),
                    })
    finally:
        # Sampaikan disconnect melalui queue agar daftar pemain dibersihkan oleh GameEngine.
        session.close()
        event_queue.put({
            "type": "client_disconnect",
            "player_id": session.player_id,
            "session": session,
        })
