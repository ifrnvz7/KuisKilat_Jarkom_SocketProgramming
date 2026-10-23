"""Menerima koneksi TCP dan menjalankan thread pembaca untuk setiap client."""
import itertools
import queue
import socket
import threading

from server.reader import reader_thread
from server.session import Session


def create_welcoming_socket(host: str, port: int, backlog: int = 10) -> socket.socket:
    """Membuat, mengonfigurasi SO_REUSEADDR, bind, dan listen welcoming socket TCP."""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Mengatasi masalah port tertahan di state TIME_WAIT saat restart server cepat
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(backlog)
    return server_sock


def accept_loop(
    server_sock: socket.socket,
    event_queue: queue.Queue,
    stop_event: threading.Event | None = None,
) -> None:
    """Terima koneksi dan daftarkan thread reader per client."""
    counter = itertools.count(1)
    try:
        while stop_event is None or not stop_event.is_set():
            try:
                conn, addr = server_sock.accept()
            except OSError:
                # Socket welcoming ditutup saat shutdown
                break

            # Batas waktu juga berlaku saat writer mengirim ke client yang lambat.
            # Koneksi yang tidak merespons tidak boleh menahan sendall() tanpa batas.
            conn.settimeout(1.0)
            player_id = f"P{next(counter)}"
            session = Session(player_id=player_id, conn=conn, addr=addr)
            print(f"[+] Koneksi baru dari {addr[0]}:{addr[1]} (ID: {player_id})")

            # Reader belum mengubah daftar pemain, GameEngine menerima koneksi ini lewat queue.
            event_queue.put({
                "type": "new_client",
                "player_id": player_id,
                "session": session,
            })

            t = threading.Thread(
                target=reader_thread,
                args=(session, event_queue),
                name=f"Reader-{player_id}",
                daemon=True,
            )
            t.start()
    finally:
        try:
            server_sock.close()
        except OSError:
            pass
