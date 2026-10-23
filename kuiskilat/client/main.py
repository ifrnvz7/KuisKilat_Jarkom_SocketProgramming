"""Entrypoint utama Client Pemain KuisKilat.

Cara menjalankan dari folder root kuiskilat/:
    python -m client.main --host 127.0.0.1 --port 5000 --name Budi
"""
import argparse
from client.client import QuizClient
from common import protocol as P


def main() -> None:
    parser = argparse.ArgumentParser(description="Client CLI Pemain KuisKilat")
    parser.add_argument("--host", default=P.DEFAULT_HOST, help="IP Server (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=P.DEFAULT_PORT, help="Port TCP Server (default: 5000)")
    parser.add_argument("--name", default=None, help="Nama pemain")
    args = parser.parse_args()

    name = args.name
    while not name:
        try:
            name = input("Masukkan nama pemain: ").strip()
        except (EOFError, KeyboardInterrupt):
            return

    client = QuizClient(host=args.host, port=args.port, name=name)
    client.start()


if __name__ == "__main__":
    main()
