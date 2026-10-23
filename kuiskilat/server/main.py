"""Jalankan server KuisKilat (python -m server.main)."""
import argparse
import queue
import threading

from common import protocol as P
from server.game import GameEngine
from server.listener import accept_loop, create_welcoming_socket
from server.questions import QUESTIONS

def run_server(host: str = "0.0.0.0", port: int = P.DEFAULT_PORT) -> None:
    questions = QUESTIONS
    event_queue: queue.Queue = queue.Queue()
    stop_event = threading.Event()

    server_sock = create_welcoming_socket(host, port)
    engine = GameEngine(questions=questions, event_queue=event_queue)
    game_thread = threading.Thread(
        target=engine.run,
        args=(stop_event,),
        name="GameThread",
        daemon=True,
    )
    game_thread.start()

    print("=" * 60)
    print(f" SERVER KUISKILAT AKTIF DI {host}:{port} ({len(questions)} Soal)")
    print(" Menunggu pemain terhubung... (Tekan Ctrl+C untuk berhenti)")
    print("=" * 60)

    try:
        accept_loop(server_sock, event_queue, stop_event)
    except KeyboardInterrupt:
        print("\n[Server] Menerima sinyal berhenti, menutup server...")
    finally:
        stop_event.set()
        try:
            server_sock.close()
        except OSError:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Server KuisKilat TCP")
    parser.add_argument("--host", default="0.0.0.0", help="Alamat IP bind server (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=P.DEFAULT_PORT, help="Port TCP server (default: 5000)")
    args = parser.parse_args()
    run_server(args.host, args.port)
