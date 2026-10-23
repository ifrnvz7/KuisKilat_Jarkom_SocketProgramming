"""Client kuis: satu thread input dan satu loop penerima pesan socket."""
import socket
import threading

from client import ui
from common import protocol as P


class QuizClient:
    """Client TCP interaktif untuk pemain KuisKilat."""

    def __init__(self, host: str, port: int, name: str) -> None:
        self.host = host
        self.port = port
        self.name = name
        self.conn: socket.socket | None = None
        self.running = False
        self.is_host = False
        self.current_q_id: int | None = None
        self.player_id: str | None = None

    def send_message(self, msg: dict) -> bool:
        """Mengirim dictionary pesan ke server melalui conn.sendall()."""
        if self.conn is None or not self.running:
            return False
        try:
            self.conn.sendall(P.encode(msg))
            return True
        except OSError:
            self.running = False
            return False

    def receive_loop(self) -> None:
        """Menerima pesan server sampai koneksi berakhir."""
        assert self.conn is not None
        buffer = b""
        try:
            while self.running:
                try:
                    chunk = self.conn.recv(P.RECV_BUFFER_SIZE)
                except OSError:
                    break
                if chunk == b"":
                    print("\n[!] Koneksi ditutup oleh server.")
                    break

                buffer += chunk
                # Simpan pesan yang belum selesai hingga recv() berikutnya.
                lines, buffer = P.extract_lines(buffer)
                for raw_line in lines:
                    try:
                        msg = P.decode(raw_line)
                    except P.ProtocolError:
                        continue
                    self._handle_server_message(msg)
        finally:
            self.running = False
            self.close()

    def _handle_server_message(self, msg: dict) -> None:
        mtype = msg.get("type")
        if mtype == P.JOIN_OK:
            self.is_host = bool(msg.get("is_host", False))
            self.player_id = str(msg.get("player_id", ""))
            ui.render_join_ok(str(msg.get("player_id", "?")), self.is_host)
        elif mtype == P.PLAYER_LIST:
            for p in msg.get("players", []):
                if p.get("player_id") == self.player_id:
                    self.is_host = bool(p.get("is_host", False))
            ui.render_player_list(msg.get("players", []))
        elif mtype == P.QUESTION:
            self.current_q_id = msg.get("q_id")
            ui.render_question(msg)
        elif mtype == P.RESULT:
            self.current_q_id = None
            ui.render_result(msg)
        elif mtype == P.GAME_OVER:
            self.current_q_id = None
            ui.render_game_over(msg)
        elif mtype == P.ERROR:
            ui.render_error(msg)

    def input_loop(self) -> None:
        """Membaca perintah terminal (dijalankan dalam input thread)."""
        try:
            while self.running:
                try:
                    user_in = input().strip()
                except (EOFError, KeyboardInterrupt):
                    self.send_message({"type": P.LEAVE})
                    break
    
                if not self.running:
                    break
                if not user_in:
                    continue
    
                cmd = user_in.lower()
                if cmd in ("quit", "exit", "q"):
                    self.send_message({"type": P.LEAVE})
                    break
                elif cmd == "start":
                    self.send_message({"type": P.START})
                elif cmd == "join":
                    self.send_message({"type": P.JOIN, "name": self.name})
                elif cmd.isdigit() and self.current_q_id is not None:
                    val = int(cmd)
                    choice_idx = val - 1  # Pilihan pada layar 1-4, indeks protokol 0-3.
                    if not 0 <= choice_idx <= 3:
                        print("Masukkan angka 1 sampai 4.")
                        continue
                    self.send_message({
                        "type": P.ANSWER,
                        "q_id": self.current_q_id,
                        "choice": choice_idx,
                    })
                else:
                    print("Perintah: start (host), join (coba masuk lobby), 1-4 (jawab), quit (keluar).")
        finally:
            self.close()

    def close(self) -> None:
        """Menutup socket client secara rapi."""
        self.running = False
        if self.conn is not None:
            try:
                self.conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.conn.close()
            except OSError:
                pass

    def start(self) -> None:
        """Menghubungkan socket ke server, mengirim JOIN, dan menjalankan loop."""
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.conn.connect((self.host, self.port))
        except OSError as exc:
            print(f"[!] Gagal terhubung ke server {self.host}:{self.port} -> {exc}")
            return

        self.running = True
        ui.print_banner(self.host, self.port)
        self.send_message({"type": P.JOIN, "name": self.name})

        # Input terminal boleh blocking; receiver berjalan di main thread agar
        # aplikasi bisa keluar saat server memutus koneksi.
        # input() memblokir thread input saja, sedangkan main thread tetap membaca server.
        input_thread = threading.Thread(
            target=self.input_loop, name="ClientInput", daemon=True,
        )
        input_thread.start()
        try:
            self.receive_loop()
        finally:
            self.close()
