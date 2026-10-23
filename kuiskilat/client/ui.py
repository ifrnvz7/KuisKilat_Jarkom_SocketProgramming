"""Tampilan terminal untuk pemain."""


def print_banner(host: str, port: int) -> None:
    print("=" * 58)
    print("        KUISKILAT — KUIS REALTIME MULTI-CLIENT TCP        ")
    print(f"        Terhubung ke Server {host}:{port:<22}")
    print("=" * 58)


def render_join_ok(player_id: str, is_host: bool) -> None:
    role = "HOST (Ketik 'start' untuk memulai kuis)" if is_host else "PESERTA (Menunggu Host memulai kuis)"
    print(f"\n[JOIN BERHASIL] ID Kamu: {player_id} | Peran: {role}")


def render_player_list(players: list[dict]) -> None:
    formatted = ", ".join(
        f"{p['name']}{' [HOST]' if p.get('is_host') else ''}"
        for p in players
    )
    print(f"\n[LOBBY] Daftar Pemain ({len(players)}): {formatted}")


def render_question(msg: dict) -> None:
    q_num = msg.get("number", msg.get("q_id", 1))
    total = msg.get("total", "?")
    limit = msg.get("time_limit", 15)
    print("\n" + "-" * 58)
    print(f"SOAL {q_num}/{total}  |  Waktu: {limit} detik")
    print("-" * 58)
    print(f"{msg.get('text', '')}\n")
    for idx, opt in enumerate(msg.get("options", []), start=1):
        print(f"  [{idx}] {opt}")
    print("\nKetik pilihanmu (1-4) lalu Enter: ", end="", flush=True)


def render_result(msg: dict) -> None:
    your_choice = msg.get("your_choice")
    correct = msg.get("correct")
    gained = msg.get("gained", 0)

    if your_choice is None:
        status = "WAKTU HABIS / TIDAK MENJAWAB"
    elif your_choice == correct:
        status = f"BENAR! (+{gained} poin)"
    else:
        status = f"SALAH! (Jawaban benar: pilihan nomor {int(correct) + 1})"

    print(f"\n>>> HASIL SOAL #{msg.get('q_id')}: {status}")
    print("    Klasemen Sementara:")
    for rank, row in enumerate(msg.get("scoreboard", []), start=1):
        print(f"      {rank}. {row['name']:<20} {row['score']} poin")


def render_game_over(msg: dict) -> None:
    print("\n" + "=" * 58)
    print("               *** PERMAINAN SELESAI ***                  ")
    print("=" * 58)
    for rank, row in enumerate(msg.get("ranking", []), start=1):
        medal = {1: "[JUARA 1]", 2: "[JUARA 2]", 3: "[JUARA 3]"}.get(rank, f"#{rank}")
        print(f"  {medal:<10} {row['name']:<20} {row['score']} poin")
    print("=" * 58)
    print("Kembali ke Lobby. Host dapat mengetik 'start' untuk bermain lagi, atau ketik 'quit' untuk keluar.")


def render_error(msg: dict) -> None:
    code = msg.get("code", "ERROR")
    text = msg.get("message", "Terjadi kesalahan.")
    print(f"\n[ERROR - {code}] {text}")
    if code == "GAME_STARTED":
        print("Coba ketik 'join' setelah permainan saat ini selesai.")
