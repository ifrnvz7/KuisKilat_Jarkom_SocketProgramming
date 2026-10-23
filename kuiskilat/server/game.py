"""Logika kuis, timer soal, dan pengelolaan pemain.

Daftar pemain, skor, dan status kuis dikelola game thread lewat antrean event.
"""
import queue
import threading
import time
from enum import Enum

from common import protocol as P
from server.session import Session
from server.writer import broadcast, send_to

MAX_NAME_LEN = 20
MAX_POINTS = 1000
MIN_POINTS = 500
REVEAL_DELAY = 3.0


class GameState(Enum):
    LOBBY = "LOBBY"
    QUESTION = "QUESTION"
    REVEAL = "REVEAL"
    FINISHED = "FINISHED"


class GameEngine:
    """State machine kuis yang memproses seluruh event dari event_queue."""

    def __init__(
        self,
        questions: list[dict],
        event_queue: queue.Queue,
        reveal_delay: float = REVEAL_DELAY,
    ) -> None:
        self.questions = questions
        self.event_queue = event_queue
        self.reveal_delay = reveal_delay

        # Daftar ini diubah oleh game thread, bukan thread pembaca socket.
        self.sessions: dict[str, Session] = {}   # seluruh koneksi aktif
        self.players: dict[str, Session] = {}    # koneksi yang sudah mengirim JOIN valid
        self.state = GameState.LOBBY

        self.current_index: int = -1
        self.current_question: dict | None = None
        self.q_start_time: float = 0.0
        self.q_deadline: float = 0.0
        self.reveal_deadline: float = 0.0

    # Loop game
    def run(self, stop_event: threading.Event | None = None) -> None:
        """Menjalankan event loop berbasis queue.get(timeout=...) di Game Thread."""
        while stop_event is None or not stop_event.is_set():
            timeout = self._compute_timeout()
            try:
                event = self.event_queue.get(timeout=timeout)
                self._dispatch_event(event)
            except queue.Empty:
                self._on_timeout()

    def _compute_timeout(self) -> float:
        """Menentukan batas waktu tunggu queue berdasarkan state aktif."""
        # Deadline dihitung memakai jam monotonic, bukan waktu kalender sistem.
        now = time.monotonic()
        if self.state == GameState.QUESTION:
            return max(0.0, self.q_deadline - now)
        if self.state == GameState.REVEAL:
            return max(0.0, self.reveal_deadline - now)
        return 0.2

    def _on_timeout(self) -> None:
        """Dipanggil ketika waktu tunggu habis (soal selesai atau jeda reveal selesai)."""
        now = time.monotonic()
        if self.state == GameState.QUESTION and now >= self.q_deadline:
            self._finish_current_question()
        elif self.state == GameState.REVEAL and now >= self.reveal_deadline:
            self._advance_next_step()

    # Event dari reader
    def _dispatch_event(self, event: dict) -> None:
        etype = event.get("type")
        session: Session = event.get("session")

        if etype == "new_client":
            self.sessions[session.player_id] = session

        elif etype == "client_disconnect":
            self._handle_disconnect(session)

        elif etype == "bad_message":
            err_msg = event.get("error", "Format pesan tidak valid.")
            send_to(session, P.make_error(err_msg, code="BAD_MESSAGE"))

        elif etype == "message":
            self._handle_client_message(session, event.get("data", {}))

        # Cek apakah setelah memproses event waktu soal/reveal sudah habis
        self._on_timeout()

    def _handle_client_message(self, session: Session, msg: dict) -> None:
        mtype = msg.get("type")

        if mtype == P.JOIN:
            self._handle_join(session, msg.get("name"))
        elif session.player_id not in self.players:
            send_to(session, P.make_error("Silakan kirim pesan JOIN terlebih dahulu.", code="NOT_JOINED"))
        elif mtype == P.START:
            self._handle_start(session)
        elif mtype == P.ANSWER:
            self._handle_answer(session, msg.get("q_id"), msg.get("choice"))
        elif mtype == P.LEAVE:
            session.close()
            self._handle_disconnect(session)
        else:
            send_to(session, P.make_error(f"Tipe pesan tidak dikenal: {mtype}", code="UNKNOWN_TYPE"))

    # Aksi pemain
    def _handle_join(self, session: Session, raw_name) -> None:
        if session.player_id in self.players:
            send_to(session, P.make_error("Kamu sudah bergabung di dalam lobby.", code="ALREADY_JOINED"))
            return
        if self.state != GameState.LOBBY:
            send_to(session, P.make_error("Permainan sedang berlangsung, tunggu sesi berikutnya.", code="GAME_STARTED"))
            return

        name = raw_name.strip() if isinstance(raw_name, str) else ""
        if not name or len(name) > MAX_NAME_LEN:
            send_to(session, P.make_error(f"Nama wajib diisi (maksimal {MAX_NAME_LEN} karakter).", code="BAD_NAME"))
            return
        if any(p.name and p.name.lower() == name.lower() for p in self.players.values()):
            send_to(session, P.make_error("Nama sudah digunakan pemain lain.", code="NAME_TAKEN"))
            return

        session.name = name
        session.score = 0
        session.answer = None
        session.is_host = len(self.players) == 0  # Pemain pertama otomatis menjadi Host
        self.players[session.player_id] = session

        print(f"[*] Pemain bergabung: {session.name} ({session.player_id}, host={session.is_host})")
        send_to(session, {
            "type": P.JOIN_OK,
            "player_id": session.player_id,
            "is_host": session.is_host,
        })
        self._broadcast_player_list()

    def _handle_start(self, session: Session) -> None:
        if not session.is_host:
            send_to(session, P.make_error("Hanya Host yang dapat memulai permainan.", code="NOT_HOST"))
            return
        if self.state != GameState.LOBBY:
            send_to(session, P.make_error("Permainan sudah berjalan.", code="BAD_STATE"))
            return
        if not self.questions:
            send_to(session, P.make_error("Bank soal kosong.", code="NO_QUESTIONS"))
            return

        print(f"[!] Permainan dimulai oleh Host {session.name} ({len(self.players)} pemain)")
        for p in self.players.values():
            p.score = 0
            p.answer = None
        self.current_index = -1
        self._advance_next_step()

    def _handle_answer(self, session: Session, q_id, choice) -> None:
        if self.state != GameState.QUESTION or self.current_question is None:
            send_to(session, P.make_error("Tidak ada soal yang sedang aktif.", code="BAD_STATE"))
            return
        if q_id != self.current_question["q_id"]:
            send_to(session, P.make_error("ID soal tidak sesuai atau sudah kedaluwarsa.", code="BAD_QID"))
            return

        # Cek ulang deadline ketika ANSWER diproses, bukan hanya ketika queue kosong.
        if time.monotonic() >= self.q_deadline:
            send_to(session, P.make_error("Waktu menjawab soal sudah habis.", code="TIME_UP"))
            return

        n_opts = len(self.current_question["options"])
        if not isinstance(choice, int) or isinstance(choice, bool) or not (0 <= choice < n_opts):
            send_to(session, P.make_error(f"Pilihan jawaban harus berupa angka 0 sampai {n_opts - 1}.", code="BAD_CHOICE"))
            return
        if session.answer is not None:
            send_to(session, P.make_error("Kamu sudah menjawab soal ini.", code="ALREADY_ANSWERED"))
            return

        elapsed = max(0.0, time.monotonic() - self.q_start_time)
        session.answer = (choice, elapsed)

        # Jika seluruh pemain aktif sudah menjawab, langsung akhiri soal tanpa menunggu timeout
        if self.players and all(p.answer is not None for p in self.players.values()):
            self._finish_current_question()

    def _handle_disconnect(self, session: Session) -> None:
        self.sessions.pop(session.player_id, None)
        removed = self.players.pop(session.player_id, None)
        if removed is None:
            return

        print(f"[-] Pemain keluar/putus: {removed.name} ({removed.player_id})")

        if not self.players:
            # Semua pemain keluar -> reset ke LOBBY
            self._reset_to_lobby()
            return

        # Jika Host keluar, promosikan pemain paling awal berikutnya menjadi Host
        # Urutan dict pemain mengikuti urutan JOIN, sehingga pemain terlama berikutnya dipilih.
        if removed.is_host:
            next_host = next(iter(self.players.values()))
            next_host.is_host = True
            print(f"[*] Host dialihkan ke {next_host.name} ({next_host.player_id})")

        self._broadcast_player_list()

        # Pastikan jika pemain keluar saat QUESTION, ronde tidak macet menunggu dia
        if self.state == GameState.QUESTION:
            if all(p.answer is not None for p in self.players.values()):
                self._finish_current_question()

    # Alur soal
    def _advance_next_step(self) -> None:
        self.current_index += 1
        if self.current_index >= len(self.questions):
            self.state = GameState.FINISHED
            ranking = self._build_scoreboard()
            self._handle_dead_clients(broadcast(self.players, {"type": P.GAME_OVER, "ranking": ranking}))
            print("[!] Permainan selesai. Mengembalikan pemain ke Lobby.")
            self._reset_to_lobby()
            self._broadcast_player_list()
            return

        q_raw = self.questions[self.current_index]
        q_number = self.current_index + 1
        time_limit = int(q_raw.get("time_limit", 15))

        self.current_question = {
            "q_id": q_number,
            "number": q_number,
            "total": len(self.questions),
            "text": q_raw["text"],
            "options": q_raw["options"],
            "answer": q_raw["answer"],
            "time_limit": time_limit,
        }

        for p in self.players.values():
            p.answer = None

        self.state = GameState.QUESTION
        self.q_start_time = time.monotonic()
        self.q_deadline = self.q_start_time + time_limit

        # Kirim QUESTION ke semua pemain (TANPA menyertakan field 'answer')
        dead_ids = broadcast(self.players, {
            "type": P.QUESTION,
            "q_id": q_number,
            "number": q_number,
            "total": len(self.questions),
            "text": q_raw["text"],
            "options": q_raw["options"],
            "time_limit": time_limit,
        })
        self._handle_dead_clients(dead_ids)

    def _finish_current_question(self) -> None:
        if self.current_question is None:
            return

        q = self.current_question
        gained_map: dict[str, int] = {}

        for pid, p in self.players.items():
            pts = self._calculate_points(p, q)
            gained_map[pid] = pts
            p.score += pts

        board = self._build_scoreboard()

        # Setelah menghitung skor, kirim hasil ke pemain yang masih terhubung.
        # REVEAL tetap aktif selama jeda, walaupun semua pemain sudah menjawab.
        self.state = GameState.REVEAL
        self.reveal_deadline = time.monotonic() + self.reveal_delay
        dead_ids: list[str] = []
        for pid, p in list(self.players.items()):
            ok = send_to(p, {
                "type": P.RESULT,
                "q_id": q["q_id"],
                "correct": q["answer"],
                "your_choice": p.answer[0] if p.answer is not None else None,
                "gained": gained_map.get(pid, 0),
                "scoreboard": board,
            })
            if not ok:
                dead_ids.append(pid)

        self._handle_dead_clients(dead_ids)
        if not self.players:
            self._reset_to_lobby()

    def _reset_to_lobby(self) -> None:
        self.state = GameState.LOBBY
        self.current_index = -1
        self.current_question = None
        for p in self.players.values():
            p.score = 0
            p.answer = None

    # Skor dan pengiriman
    @staticmethod
    def _calculate_points(player: Session, q: dict) -> int:
        if player.answer is None:
            return 0
        choice, elapsed = player.answer
        if choice != q["answer"]:
            return 0
        time_limit = max(1.0, float(q["time_limit"]))
        ratio = min(max(elapsed / time_limit, 0.0), 1.0)
        return int(MAX_POINTS - (MAX_POINTS - MIN_POINTS) * ratio)

    def _build_scoreboard(self) -> list[dict]:
        ranked = sorted(self.players.values(), key=lambda p: p.score, reverse=True)
        return [{"name": p.name, "score": p.score} for p in ranked]

    def _broadcast_player_list(self) -> None:
        player_info = [
            {
                "player_id": p.player_id,
                "name": p.name,
                "score": p.score,
                "is_host": p.is_host,
            }
            for p in self.players.values()
        ]
        dead_ids = broadcast(self.players, {"type": P.PLAYER_LIST, "players": player_info})
        self._handle_dead_clients(dead_ids)

    def _handle_dead_clients(self, dead_ids: list[str]) -> None:
        for pid in dead_ids:
            session = self.sessions.get(pid)
            if session is not None:
                self._handle_disconnect(session)
