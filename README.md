# KuisKilat — Implementasi Socket TCP (Socket-Only)

Proyek Kelompok Mata Kuliah **Jaringan Komputer (PACS262202)**

Rujukan materi: *Kurose & Ross, Computer Networking: A Top-Down Approach, 8th Edition*, khususnya Bab 2 §2.7 tentang *Socket Programming with TCP*.

> **Catatan versi:** Arsip ini merupakan versi **socket-only** dari KuisKilat. Versi ini berfokus pada komunikasi antara client dan server menggunakan TCP socket melalui terminal (CLI). Fitur Frontend/Web UI, WebSocket Gateway, dan SQLite yang terdapat atau direncanakan pada versi full-stack tidak termasuk dalam versi arsip ini.

## Anggota Kelompok

1. Dharu Triayuda (23/523164/PA/22511)
2. Gradien Ridholumintu (25/555306/PA/23271)
3. Muhammad Irfan Zain (25/555588/PA/23291)
4. Muhammad Gauza Faliha (25/555851/PA/23315)
5. Bimo Ataullah Rahman (25/556364/PA/23359)

## 1. Gambaran Umum dan Arsitektur

KuisKilat adalah permainan kuis multipemain berbasis client-server. Pada versi socket-only ini, client berkomunikasi langsung dengan server menggunakan **TCP socket**. Server menerima koneksi pemain, mengelola sesi, memproses pesan protokol, serta menjalankan alur permainan dan perhitungan skor.

```text
[ Client Pemain 1 (CLI) ] ──┐
                            │
[ Client Pemain 2 (CLI) ] ──┼── TCP Socket ──> [ Server KuisKilat ]
                            │                  (listener, session,
[ Client Pemain N (CLI) ] ──┘                   reader, writer, game)
```

### Komponen utama

- **TCP socket:** menyediakan komunikasi dua arah antara client dan server.
- **Threading dan pembacaan client:** memungkinkan server menangani koneksi pemain dan menerima pesan dari client.
- **Protokol pesan bersama:** mengatur pengodean/penguraian pesan serta penanganan framing agar pesan yang diterima dapat diproses dengan benar.
- **Game logic:** mengelola alur kuis, status permainan, pertanyaan, dan skor.
- **Client CLI:** menyediakan antarmuka berbasis terminal untuk pemain.

Versi ini tidak menjalankan HTTP server, WebSocket gateway, Web UI di browser, ataupun database SQLite. Bank soal ditangani melalui modul `server/questions.py`.

## 2. Struktur Direktori

```text
kuiskilat/
├── README.md                  # Panduan proyek
├── common/
│   ├── __init__.py
│   └── protocol.py            # Pengodean pesan dan framing protokol
├── server/
│   ├── __init__.py
│   ├── listener.py            # Socket server dan penerimaan koneksi
│   ├── session.py             # Data/status sesi client
│   ├── reader.py              # Pembacaan pesan dari client
│   ├── writer.py              # Pengiriman pesan/broadcast ke client
│   ├── questions.py           # Bank atau pengelolaan pertanyaan
│   ├── game.py                # Logika dan alur permainan kuis
│   └── main.py                # Entrypoint server TCP
└── client/
    ├── __init__.py
    ├── client.py              # Koneksi socket dan komunikasi client
    ├── ui.py                  # Tampilan antarmuka terminal
    └── main.py                # Entrypoint client CLI
```

## 3. Persiapan

1. Ekstrak arsip proyek.
2. Pastikan Python 3 sudah terpasang.
3. Buka terminal pada folder root `kuiskilat/`, yaitu folder yang berisi direktori `client/`, `common/`, dan `server/`.

Implementasi ini menggunakan modul standar Python untuk socket dan komunikasi jaringan. Tidak diperlukan instalasi paket eksternal berdasarkan struktur proyek ini.

## 4. Cara Menjalankan Server dan Client

Jalankan seluruh perintah dari folder root `kuiskilat/`.

### Langkah 1 — Jalankan Server TCP

Buka terminal pertama, kemudian jalankan:

```bash
python -m server.main
```

Server akan dijalankan sebagai pusat komunikasi bagi client. Biarkan terminal server tetap terbuka selama permainan berlangsung.

### Langkah 2 — Jalankan Client Pemain

Buka terminal kedua untuk pemain pertama:

```bash
python -m client.main
```

Jalankan perintah yang sama pada terminal lain untuk menambahkan pemain. Setiap pemain menjalankan proses client tersendiri.

Jika aplikasi menyediakan argumen CLI untuk nama pemain, argumen tersebut dapat digunakan sesuai bantuan atau implementasi pada `client/main.py`. Jika tidak, ikuti instruksi yang ditampilkan oleh aplikasi setelah client dijalankan.

### Langkah 3 — Bermain

1. Pastikan server aktif terlebih dahulu.
2. Jalankan client pada terminal masing-masing pemain.
3. Ikuti petunjuk pada terminal untuk bergabung dan berinteraksi dengan kuis.
4. Biarkan semua client tetap terhubung selama permainan berlangsung.
5. Untuk menghentikan permainan, ikuti mekanisme keluar yang disediakan aplikasi dan hentikan proses server setelah seluruh client selesai.

**Penting:** versi ini menggunakan antarmuka terminal (CLI), bukan browser. Perintah untuk menjalankan `gateway.gateway` atau membuka `http://localhost:8080` tidak berlaku pada versi socket-only ini.

## 5. Pengujian dan Pemeriksaan

Sebelum menjalankan permainan, pemeriksaan sintaks seluruh file Python dapat dilakukan dari folder root:

```bash
python -m compileall .
```

Jika kompilasi berhasil, Python tidak menemukan kesalahan sintaks pada file yang diperiksa. Pemeriksaan ini **tidak menjamin** bahwa seluruh alur permainan atau komunikasi jaringan sudah berjalan benar; pengujian runtime tetap diperlukan.

Pengujian manual yang disarankan:

1. Jalankan server, lalu hubungkan satu client.
2. Hubungkan beberapa client dari terminal terpisah.
3. Periksa apakah pesan dari server diterima dengan benar oleh client.
4. Uji alur permainan dari awal hingga selesai, termasuk pengiriman jawaban dan pembaruan skor jika tersedia.
5. Uji penutupan salah satu client dan amati apakah server tetap dapat menangani client lainnya.

## 6. Catatan Protokol dan Batasan Versi

- Komunikasi utama dilakukan menggunakan **TCP**, yang menyediakan aliran byte andal dan berurutan.
- TCP tidak mempertahankan batas pesan aplikasi secara otomatis. Karena itu, aplikasi memerlukan aturan framing/protokol agar data yang diterima dapat dipisahkan menjadi pesan-pesan yang benar.
- Modul `common/protocol.py` menjadi tempat bersama untuk aturan protokol yang digunakan oleh client dan server.
- Versi ini berfokus pada komunikasi socket TCP dan permainan melalui CLI.
- **Tidak termasuk dalam arsip socket-only ini:** Web UI, HTTP server, WebSocket gateway, integrasi browser dan CLI dalam lobby yang sama melalui gateway, serta database SQLite.

Untuk laporan yang membahas versi full-stack, jelaskan bahwa arsip ini merupakan implementasi socket-only yang menjadi bagian komunikasi TCP inti. Fitur gateway, web, dan database harus dijelaskan berdasarkan source code versi full-stack yang benar-benar digunakan dalam laporan, bukan dianggap tersedia pada arsip ini.
