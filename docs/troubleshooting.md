# Bantuan dan Troubleshooting

Mulai dengan `python3 wizard.py --check`, `docker compose ps`, dan log service
yang bermasalah. Jangan mengirim isi `.env`, API key, password, atau log yang
mungkin memuat credential ke issue publik.

## Wizard dan Docker

### `docker` tidak ditemukan atau daemon tidak aktif

Install Docker Engine/Desktop dengan Compose v2 dan pastikan daemon hidup. Uji
dengan `docker compose version`, lalu ulangi `python3 wizard.py`.

### Wizard mengatakan `.env` atau Compose tidak valid

Jalankan setup menu wizard untuk membuat `.env`, atau salin `.env.example` secara
manual. Isi semua nilai `replace-...`; jangan biarkan secret contoh dipakai di
server publik. Jalankan `python3 wizard.py --check` lagi.

### Port dashboard sudah digunakan

Ubah `NINE_ROUTER_PORT` di `.env` ke port host yang kosong, lalu jalankan
`docker compose up -d`. Port internal service tetap `20128`.

### Health check 9Router timeout

Lihat `docker compose logs --tail=100 9router`. Pastikan container berjalan,
port host benar, dan storage dapat ditulis. Health check timeout tidak menghapus
data; wizard tetap menampilkan URL untuk pemeriksaan manual.

## Key dan model

### 9Router mengembalikan 401/403 atau daftar model kosong

Buat endpoint API key di dashboard 9Router, pastikan `REQUIRE_API_KEY=true`,
dan masukkan endpoint key tersebut ke wizard saat diminta. Pastikan provider
memiliki credential dan model aktif. Jangan gunakan password dashboard sebagai
endpoint API key.

### Hermes gagal menemukan model

Periksa daftar model di wizard atau dashboard. Masukkan ID model tepat seperti
yang dikembalikan `/v1/models`, bukan display name. Pastikan base URL internal
Hermes di Compose berakhir dengan `/v1`.

### Hermes tidak dapat menghubungi 9Router

Di Compose URL harus `http://9router:20128/v1`, bukan `localhost`. Periksa
`docker compose ps` dan `docker compose logs --tail=100 hermes 9router`. Pada
Railway/Koyeb, gunakan hostname private platform, bukan hostname Compose.

### Perubahan `.env` tidak tampak di container

Jalankan `docker compose up -d` setelah mengubah environment. Perubahan model
yang dibuat wizard tersimpan pada volume Hermes. Jangan hapus volume saat
restart.

## Data dan keamanan

### Login dashboard gagal

Gunakan password awal yang dimasukkan saat wizard dijalankan. Jika password
telah diubah, nilai lama di `.env` tidak otomatis menjadi password baru.

### Saya ingin reset deployment

`docker compose down` hanya menghentikan dan menghapus container/network.
Perintah `docker compose down -v` menghapus database 9Router dan state Hermes;
backup dahulu dan gunakan hanya bila benar-benar ingin reset penuh.

### Kaggle gagal mengambil secret

Tambahkan `NINE_ROUTER_BASE_URL` dan `NINE_ROUTER_API_KEY` pada Kaggle Secrets,
aktifkan Internet, attach dataset launcher, dan gunakan URL origin HTTPS tanpa
akhiran `/v1`. Opsional `HERMES_MODEL` harus sama dengan salah satu model ID di
`/v1/models`.

Kaggle runtime bersifat sementara. Jika runtime reset, jalankan ulang notebook;
jangan mengandalkannya untuk gateway 24/7.