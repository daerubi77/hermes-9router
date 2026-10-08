# Hermes + 9Router

Stack Docker Compose untuk menjalankan Hermes Agent dengan 9Router sebagai
gateway model OpenAI-compatible. Hermes mengirim permintaan ke 9Router melalui
network internal Compose; dashboard 9Router tetap dapat dibuka dari browser.

## Mulai cepat

Prasyarat: Docker Engine/Desktop dengan Compose v2 dan Python 3.8+.

```sh
./wizard.py
```

Wizard memandu pembuatan konfigurasi, menjalankan 9Router terlebih dahulu,
meminta endpoint API key dan ID model, mengatur Hermes, lalu menjalankan stack.
Password awal diminta dengan input tersembunyi; secret lain dibuat otomatis dan
`.env` dibatasi ke permission user (`0600` pada sistem POSIX). Wizard tidak
mencetak API key ke layar.

Perintah lain:

```sh
./wizard.py --help             # bantuan CLI
./wizard.py --check             # validasi Docker dan .env tanpa deploy
docker compose ps              # status container
docker compose logs -f hermes  # log Hermes
docker compose down            # hentikan container, volume data tetap ada
```

Untuk update, jalankan `docker compose pull && docker compose up -d`. Backup
data sebelum update penting; lihat [panduan operasi](docs/wiki.md#operasi).

## Dokumentasi

- [Arsitektur](docs/architecture.md): services, network, port, secret, dan data.
- [Cara kerja](docs/how-it-works.md): urutan wizard, request model, lifecycle.
- [Wiki / indeks panduan](docs/wiki.md): deployment lokal, platform, Kaggle,
	operasi, konfigurasi, dan batasan.
- [Bantuan & troubleshooting](docs/troubleshooting.md): masalah umum dan
	langkah diagnosis.

Upstream: [Hermes Agent](https://github.com/NousResearch/hermes-agent) ·
[9Router](https://github.com/decolua/9router) ·
[Syadagentic](https://github.com/Sekolah76/syadagentic)

## Syadagentic untuk Hermes

Repo ini menyertakan skill `syadagentic-safe` untuk perencanaan bertahap,
checkpoint, batas resource, dry-run, dan pengujian keamanan yang berotorisasi.
Pada Compose, skill dipasang read-only ke `~/.hermes/skills/` di container.
Instruksinya menjaga guardrail Hermes tetap aktif.

Untuk Hermes yang sudah terinstal langsung di host, dari root repo jalankan:

```sh
mkdir -p ~/.hermes/skills/syadagentic-safe
cp hermes-skills/syadagentic-safe/SKILL.md ~/.hermes/skills/syadagentic-safe/SKILL.md
```

Mulai ulang sesi Hermes agar skill terdeteksi. Jangan jalankan installer upstream
atau terapkan prompt/patch `zero-refusal` dan guardrail-bypass; komponen tersebut
tidak termasuk integrasi ini.

## Uji melalui Kaggle

Notebook [kaggle_hermes_9router.ipynb](kaggle_hermes_9router.ipynb) menjalankan
Hermes sementara di Kaggle dan mengirim request ke 9Router yang dideploy
terpisah. Aktifkan Internet, unggah `kaggle_hermes_9router.py` sebagai Kaggle
Dataset, lalu attach dataset itu ke notebook. Tambahkan Kaggle Secrets
`NINE_ROUTER_BASE_URL` (origin HTTPS tanpa `/v1`), `NINE_ROUTER_API_KEY`, dan
opsional `HERMES_MODEL`. Notebook akan menguji endpoint `/v1/models`, mengatur
Hermes, memasang skill aman, lalu mengirim satu prompt uji.

Kaggle bukan deployment persisten: runtime dan proses Hermes berhenti saat sesi
berakhir. Gunakan Railway/Koyeb/VPS untuk service 24/7; jangan membuka API Hermes
Kaggle ke jaringan publik.

## Jalankan dengan Docker Compose

Jika tidak memakai wizard, prasyaratnya tetap Docker Engine dan Docker Compose v2.

1. Salin `.env.example` menjadi `.env`, lalu ganti semua nilai `replace-...`
	 dengan nilai rahasia unik.
2. Jalankan `docker compose up -d`.
3. Buka `http://localhost:20128`, masuk ke 9Router, tambahkan provider/model,
	 lalu buat endpoint API key. Gunakan password awal dari `INITIAL_PASSWORD`.
4. Masukkan endpoint API key yang baru dibuat sebagai `NINE_ROUTER_API_KEY`
	 pada `.env`, lalu jalankan ulang `docker compose up -d`.
5. Atur Hermes agar memakai endpoint internal dan model yang tersedia di
	 9Router:

	 ```sh
	 docker compose exec hermes hermes config set model.provider custom
	 docker compose exec hermes hermes config set model.base_url http://9router:20128/v1
	 docker compose exec hermes hermes config set model.key_env NINE_ROUTER_API_KEY
	 docker compose exec hermes hermes config set model.default <model-id-di-9router>
	 ```

6. Konfigurasikan kanal Hermes yang diperlukan (misalnya Telegram atau Discord)
	 di environment/config Hermes, lalu restart dengan `docker compose restart hermes`.

Data disimpan pada named volumes `nine_router_data` dan `hermes_data`. Jangan
hapus volume tersebut saat melakukan update jika ingin mempertahankan database,
konfigurasi, dan sesi.

## Railway, Koyeb, dan server container

Compose dapat dijalankan pada VM/VPS atau host yang mendukung Docker Compose.
Untuk platform yang membuat service satu per satu, deploy dua container dalam
project/network privat yang sama:

- 9Router: image `decolua/9router:latest`, port internal `20128`, mount volume
	persisten ke `/app/data`.
- Hermes: image `nousresearch/hermes-agent:latest`, command `gateway run`, mount
	volume persisten ke `/opt/data`.
- Untuk service Hermes yang dibuat terpisah, salin
	`hermes-skills/syadagentic-safe/SKILL.md` ke
	`/opt/data/skills/syadagentic-safe/SKILL.md` pada volume Hermes; bind mount
	Compose di atas tidak berlaku untuk deployment service manual.
- Set variabel 9Router dari `.env.example`; aktifkan `REQUIRE_API_KEY=true`.
	Di Hermes, set `NINE_ROUTER_API_KEY` ke endpoint key 9Router dan gunakan
	private service URL 9Router sebagai `model.base_url` (akhiran `/v1`).
- Ekspos port 9Router untuk dashboard; jangan ekspos port Hermes kecuali memang
	mengatur akses publik dan autentikasinya.
- Aktifkan `AUTH_COOKIE_SECURE=true` jika dashboard 9Router diakses melalui
	HTTPS.

Nama private URL dan dukungan volume berbeda antar-platform; gunakan alamat
internal yang disediakan platform, bukan `localhost`. Railway/Koyeb mungkin
memerlukan konfigurasi service dan volume secara manual, bukan import Compose
satu klik. Paket gratis dapat membatasi volume persisten, waktu aktif, atau
resource; cek batas platform sebelum mengandalkannya untuk agent 24/7.

Vercel Functions tidak cocok untuk menjalankan stack ini secara penuh: Hermes
Gateway perlu proses persisten dan 9Router membutuhkan penyimpanan data
persisten. Vercel dapat dipakai sebagai frontend/proxy terpisah, tetapi kedua
service tetap perlu dijalankan pada host container.
