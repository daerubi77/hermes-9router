# Wiki

Indeks referensi untuk operator Hermes + 9Router.

## Mulai dan konfigurasi

- [Mulai cepat dan wizard](../README.md#mulai-cepat)
- [Arsitektur dan network](architecture.md)
- [Cara kerja request dan deploy](how-it-works.md)
- [Bantuan dan troubleshooting](troubleshooting.md)
- [Skill Syadagentic aman](../hermes-skills/syadagentic-safe/SKILL.md)

## Mode deployment

### Docker Compose lokal/VPS

Jalankan wizard dari root repo. Mode ini membuat dua container di satu network
privat dan menyimpan data di named volumes Compose. Port dashboard 9Router dapat
diubah dari default `20128`; Hermes tidak dipublikasikan ke host.

### Railway atau Koyeb

Buat dua service container dalam project dan private network yang sama. Set
9Router ke port internal `20128`, persistent volume `/app/data`, dan variable
secret dari `.env.example`. Set Hermes ke command `gateway run` dengan persistent
volume `/opt/data`. Atur `model.base_url` di Hermes ke URL privat 9Router dengan
akhiran `/v1`, dan `NINE_ROUTER_API_KEY` ke endpoint key yang dibuat di dashboard.

Hostname private, konfigurasi domain, dan kuota volume berbeda di tiap platform;
periksa dokumentasi platform sebelum deploy. Paket gratis dapat sleep, membatasi
resource, atau tidak menyediakan volume persisten.

### Kaggle

Gunakan [notebook Kaggle](../kaggle_hermes_9router.ipynb) untuk uji interaktif,
bukan untuk hosting. Unggah `kaggle_hermes_9router.py` sebagai Dataset, attach
ke notebook, aktifkan Internet, lalu buat Kaggle Secrets. Lihat [cara kerja](how-it-works.md#kaggle)
untuk nama secret. Jangan menaruh key pada cell atau output notebook.

### Vercel

Vercel Functions bukan runtime untuk dua service ini: Hermes Gateway memerlukan
proses persisten dan 9Router memerlukan data persisten. Vercel hanya dapat
menjadi frontend/proxy terpisah, sementara kedua service berjalan di host
container.

## Operasi

| Tujuan | Perintah |
|---|---|
| Wizard | `python3 wizard.py` |
| Validasi aman | `python3 wizard.py --check` |
| Status | `docker compose ps` |
| Log Hermes | `docker compose logs -f --tail=100 hermes` |
| Log 9Router | `docker compose logs -f --tail=100 9router` |
| Restart | `docker compose up -d` |
| Stop tanpa menghapus data | `docker compose down` |
| Ambil image terbaru | `docker compose pull && docker compose up -d` |

Backup data sebelum update atau migrasi. Jalankan `mkdir -p backups`, lalu
salin data dari container yang aktif:

```sh
docker compose cp 9router:/app/data ./backups/9router-data
docker compose cp hermes:/opt/data ./backups/hermes-data
```

Backup `.env` secara terpisah pada penyimpanan rahasia yang aman. Jangan commit
backup atau `.env`. Hindari `docker compose down -v` kecuali memang ingin
menghapus semua data persisten.

## Batas integrasi Syadagentic

Skill `syadagentic-safe` menyediakan planning, checkpoint, resource limits,
dry-run, dan pengujian keamanan yang berotorisasi. Ini bukan installer lengkap
upstream. Integrasi tidak memasang prompt zero-refusal, patch bypass guardrail,
evasion, atau account-farming.