"""Kumpulan soal pilihan ganda KuisKilat."""

QUESTIONS = [{'text': 'Port default untuk protokol HTTP adalah?',
  'options': ['21', '80', '443', '25'],
  'answer': 1,
  'time_limit': 15},
 {'text': 'Protokol layer transport yang menjamin pengiriman data berurutan dan andal '
          '(reliable) adalah?',
  'options': ['UDP', 'ICMP', 'TCP', 'ARP'],
  'answer': 2,
  'time_limit': 15},
 {'text': 'Fungsi Socket API di sisi server untuk menerima koneksi masuk dari antrean '
          'adalah?',
  'options': ['connect()', 'accept()', 'sendall()', 'bind()'],
  'answer': 1,
  'time_limit': 15},
 {'text': 'Pada model referensi OSI, pengalamatan IP Address bekerja pada layer?',
  'options': ['Data Link', 'Transport', 'Network', 'Application'],
  'answer': 2,
  'time_limit': 15},
 {'text': 'Opsi socket agar port dapat langsung dipakai ulang tanpa terhalang state '
          'TIME_WAIT adalah?',
  'options': ['SO_KEEPALIVE', 'SO_REUSEADDR', 'SO_BROADCAST', 'TCP_NODELAY'],
  'answer': 1,
  'time_limit': 15}]
