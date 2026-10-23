"""Pesan protokol KuisKilat: satu objek JSON UTF-8 per baris (NDJSON)."""
import json

ENCODING = "utf-8"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
RECV_BUFFER_SIZE = 4096
MAX_MESSAGE_BYTES = 64 * 1024

# --- Tipe Pesan: Client -> Server ---
JOIN = "JOIN"        # {"type": "JOIN", "name": "Budi"}
START = "START"      # {"type": "START"}
ANSWER = "ANSWER"    # {"type": "ANSWER", "q_id": 1, "choice": 2}
LEAVE = "LEAVE"      # {"type": "LEAVE"}

# --- Tipe Pesan: Server -> Client ---
JOIN_OK = "JOIN_OK"          # {"type": "JOIN_OK", "player_id": "P1", "is_host": True}
PLAYER_LIST = "PLAYER_LIST"  # {"type": "PLAYER_LIST", "players": [...]}
QUESTION = "QUESTION"        # {"type": "QUESTION", "q_id": 1, "number": 1, "total": 5, "text": "...", "options": [...], "time_limit": 15}
RESULT = "RESULT"            # {"type": "RESULT", "q_id": 1, "correct": 1, "your_choice": 1, "gained": 950, "scoreboard": [...]}
GAME_OVER = "GAME_OVER"      # {"type": "GAME_OVER", "ranking": [...]}
ERROR = "ERROR"              # {"type": "ERROR", "code": "...", "message": "..."}


class ProtocolError(Exception):
    """Exception ketika byte pesan tidak sesuai spesifikasi protokol NDJSON."""


def encode(msg: dict) -> bytes:
    """Mengubah dictionary Python menjadi bytes NDJSON (diakhiri '\n')."""
    if not isinstance(msg, dict) or not isinstance(msg.get("type"), str):
        raise ProtocolError("Pesan yang di-encode harus berupa dict dengan field 'type' (str).")
    json_str = json.dumps(msg, ensure_ascii=False, separators=(",", ":"))
    # Newline menandai akhir pesan, sebab recv() dapat memuat sebagian atau beberapa JSON sekaligus.
    return (json_str + "\n").encode(ENCODING)


def decode(raw_line: bytes | str) -> dict:
    """Mengubah satu baris bytes/str JSON menjadi dictionary Python.

    Melempar ProtocolError apabila format JSON rusak atau tidak memiliki field 'type'.
    """
    try:
        if isinstance(raw_line, bytes):
            text = raw_line.decode(ENCODING).strip()
        else:
            text = raw_line.strip()
        msg = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("Format JSON tidak valid") from exc

    if not isinstance(msg, dict) or not isinstance(msg.get("type"), str):
        raise ProtocolError("Pesan wajib berupa objek JSON dengan field 'type' bertipe string")
    return msg


def extract_lines(buffer: bytes) -> tuple[list[bytes], bytes]:
    """Memisahkan seluruh baris lengkap (berakhir '\n') dari buffer byte stream.

    Mengembalikan (list_baris_bytes, sisa_buffer).
    """
    # Baris terakhir yang belum lengkap dikembalikan untuk digabung dengan recv() berikutnya.
    lines: list[bytes] = []
    while b"\n" in buffer:
        raw_line, buffer = buffer.split(b"\n", 1)
        if raw_line.strip():
            lines.append(raw_line)
    return lines, buffer


def make_error(message: str, code: str = "BAD_REQUEST") -> dict:
    """Membuat dictionary pesan ERROR standar dari Server ke Client."""
    return {"type": ERROR, "code": code, "message": message}
