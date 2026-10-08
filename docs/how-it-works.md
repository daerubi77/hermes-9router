# Cara Kerja

## Wizard deployment

Jalankan `python3 wizard.py` dari root repo. Wizard memakai Python standard
library; tidak ada package tambahan yang perlu diinstal.

1. Memeriksa `docker` dan Docker Compose v2.
2. Membuat `.env` dari template bila belum ada, meminta port dashboard dan
   password awal, lalu membuat secret acak. Password tidak ditampilkan saat
   diketik. Permission `.env` diatur ke `0600` bila filesystem mendukungnya.
3. Menjalankan `docker compose config --quiet` untuk mendeteksi konfigurasi yang
   tidak valid tanpa menampilkan secret.
4. Menjalankan hanya service `9router`. Key sementara ada di `.env` agar Compose
   dapat menginterpolasi konfigurasi; Hermes belum dijalankan.
5. Menunggu health endpoint lokal, lalu meminta pengguna menyiapkan provider
   dan model di dashboard 9Router serta membuat endpoint API key.
6. Membaca endpoint `/v1/models` dengan key tersebut untuk membantu memilih
   model. Jika endpoint belum siap, wizard meminta ID model secara manual.
7. Menjalankan `hermes config set` di container sekali pakai untuk menulis
   `model.provider`, `model.base_url`, `model.key_env`, dan `model.default` ke
   volume Hermes.
8. Menjalankan kedua service dan memberi akses ke menu status, log, restart,
   stop, atau bantuan.

Wizard tidak menjalankan `docker compose down -v`, tidak menghapus database,
dan tidak mencetak nilai key. Pilihan Stop menjalankan `docker compose down`;
volume tetap tersimpan.

## Jalur request model

1. Pengguna mengirim pesan ke kanal Hermes yang telah dikonfigurasi.
2. Hermes memuat model default dan key dari `NINE_ROUTER_API_KEY`.
3. Hermes mengirim request OpenAI-compatible melalui network internal ke
   `http://9router:20128/v1`.
4. 9Router memeriksa endpoint API key dan meneruskan request memakai provider
   serta model yang sudah dipilih pada dashboard.
5. Jawaban provider dikembalikan melalui 9Router ke Hermes, lalu ke kanal chat.

Kredensial provider disimpan dan dikelola di 9Router; Hermes memakai endpoint
key 9Router, bukan credential langsung setiap provider.

## Kaggle

Notebook Kaggle adalah jalur uji alternatif. Hermes berjalan sementara di
runtime Kaggle dan memanggil 9Router publik melalui HTTPS. Notebook membutuhkan
Secrets `NINE_ROUTER_BASE_URL`, `NINE_ROUTER_API_KEY`, dan opsional
`HERMES_MODEL`. Gateway API Hermes hanya bind ke `127.0.0.1` di notebook.

Kaggle menghentikan proses dan dapat menghapus filesystem saat sesi berakhir.
Gunakan container dengan volume persisten untuk bot atau gateway yang perlu
selalu aktif.