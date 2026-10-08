#!/usr/bin/env python3
"""Interactive local deployment wizard for the Hermes + 9Router stack."""

import argparse
import getpass
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
ENV_TEMPLATE = ROOT / ".env.example"
SKILL_FILE = ROOT / "hermes-skills" / "syadagentic-safe" / "SKILL.md"


class Style:
    enabled = sys.stdout.isatty() and os.getenv("NO_COLOR") is None

    @classmethod
    def paint(cls, text, code):
        if not cls.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    @classmethod
    def title(cls, text):
        return cls.paint(text, "1;36")

    @classmethod
    def success(cls, text):
        return cls.paint(text, "32")

    @classmethod
    def warning(cls, text):
        return cls.paint(text, "33")

    @classmethod
    def error(cls, text):
        return cls.paint(text, "31")


def banner():
    print(Style.title("""
  +------------------------------------------------------+
  |             HERMES + 9ROUTER DEPLOY WIZARD           |
  |      Setup aman, lokal, tanpa dependency tambahan    |
  +------------------------------------------------------+
"""))


def prompt_choice(message, default="y"):
    answer = input(f"{message} [{default}]: ").strip().lower()
    return (answer or default) in ("y", "yes", "ya", "iya")


def read_env():
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] == "'":
                value = value[1:-1].replace("\\'", "'")
            values[key.strip()] = value
    return values


def encode_env_value(value):
    if "\n" in value or "\r" in value:
        raise ValueError("Nilai .env tidak boleh berisi baris baru.")
    return "'" + value.replace("'", "\\'") + "'"


def set_env_value(key, value):
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    new_lines = []
    replaced = False
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            existing_key = stripped.split("=", 1)[0].strip()
            if existing_key == key:
                if not replaced:
                    new_lines.append(f"{key}={encode_env_value(value)}")
                    replaced = True
                continue
        new_lines.append(line)
    if not replaced:
        new_lines.append(f"{key}={encode_env_value(value)}")
    ENV_FILE.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
    try:
        ENV_FILE.chmod(0o600)
    except OSError:
        pass


def run(command, capture=False):
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=capture,
        )
    except FileNotFoundError:
        print(Style.error("Perintah tidak ditemukan: " + command[0]))
        return False, ""
    output = result.stdout or ""
    if result.returncode != 0:
        detail = result.stderr.strip() if capture else ""
        print(Style.error(f"Perintah gagal (exit {result.returncode}): {' '.join(command)}"))
        if detail:
            print(detail)
        return False, output
    if output and not capture:
        print(output, end="")
    return True, output


def compose(*args, capture=False):
    return run(["docker", "compose", *args], capture=capture)


def check_docker():
    if shutil.which("docker") is None:
        print(Style.error("Docker belum ditemukan. Install Docker Engine/Desktop dan coba lagi."))
        return False
    ok, _ = compose("version", capture=True)
    if not ok:
        print("Pastikan Docker daemon aktif dan Docker Compose v2 tersedia.")
        return False
    print(Style.success("Docker Compose siap."))
    return True


def validate_compose():
    if not ENV_FILE.exists():
        print("File .env belum ada. Jalankan wizard setup dahulu.")
        return False
    ok, _ = compose("config", "--quiet", capture=True)
    if ok:
        print(Style.success("Konfigurasi Compose valid."))
    return ok


def input_port(current):
    while True:
        entered = input(f"Port dashboard 9Router [{current}]: ").strip()
        if not entered:
            return current
        if entered.isdigit() and 1 <= int(entered) <= 65535:
            return entered
        print("Masukkan angka port antara 1 dan 65535.")


def input_password(existing):
    if existing and not existing.startswith("replace-"):
        return existing
    while True:
        password = getpass.getpass("Password awal dashboard 9Router (min. 12 karakter): ")
        if len(password) < 12:
            print("Password harus minimal 12 karakter.")
            continue
        confirmation = getpass.getpass("Ulangi password: ")
        if password == confirmation:
            return password
        print("Password tidak sama, coba lagi.")


def prepare_env():
    if not ENV_FILE.exists():
        shutil.copyfile(ENV_TEMPLATE, ENV_FILE)

    values = read_env()
    current_port = values.get("NINE_ROUTER_PORT", "20128")
    port = input_port(current_port)
    set_env_value("NINE_ROUTER_PORT", port)

    password = input_password(values.get("INITIAL_PASSWORD", ""))
    set_env_value("INITIAL_PASSWORD", password)

    generated = {
        "JWT_SECRET": "replace-",
        "API_KEY_SECRET": "replace-",
        "MACHINE_ID_SALT": "replace-",
    }
    for key, placeholder in generated.items():
        existing = read_env().get(key, "")
        if not existing or existing.startswith(placeholder):
            set_env_value(key, secrets.token_urlsafe(36))

    current_key = read_env().get("NINE_ROUTER_API_KEY", "")
    if not current_key or current_key.startswith("replace-"):
        set_env_value("NINE_ROUTER_API_KEY", "pending-" + secrets.token_urlsafe(18))

    values = read_env()
    if values.get("AUTH_COOKIE_SECURE", "false").lower() not in ("true", "false"):
        set_env_value("AUTH_COOKIE_SECURE", "false")

    try:
        ENV_FILE.chmod(0o600)
    except OSError:
        pass
    print(Style.success("File .env disiapkan dan permission dibatasi untuk user lokal."))
    print("Password awal disimpan di .env; simpan dengan aman untuk login pertama.")
    return port


def wait_for_router(port, timeout=90):
    health_url = f"http://127.0.0.1:{port}/api/health"
    print("Menunggu health check 9Router", end="", flush=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=3) as response:
                if 200 <= response.status < 300:
                    print("\n" + Style.success("9Router siap."))
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        print(".", end="", flush=True)
        time.sleep(3)
    print("\n" + Style.warning("Health check belum merespons dalam batas waktu."))
    print("Lihat log dengan memilih menu Logs; Anda tetap dapat mencoba dashboard.")
    return False


def fetch_model_ids(port, api_key):
    url = f"http://127.0.0.1:{port}/v1/models"
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return [item["id"] for item in payload.get("data", []) if item.get("id")]
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError):
        return []


def configure_hermes(model_id):
    api_key = read_env().get("NINE_ROUTER_API_KEY", "")
    commands = [
        ("model.provider", "custom"),
        ("model.base_url", "http://9router:20128/v1"),
        ("model.key_env", "NINE_ROUTER_API_KEY"),
        ("model.default", model_id),
    ]
    environment = os.environ.copy()
    environment["NINE_ROUTER_API_KEY"] = api_key
    for key, value in commands:
        command = [
            "docker", "compose", "run", "--rm", "--no-deps", "hermes",
            "config", "set", key, value,
        ]
        try:
            result = subprocess.run(command, cwd=ROOT, env=environment, check=False)
        except FileNotFoundError:
            print(Style.error("Docker tidak ditemukan."))
            return False
        if result.returncode != 0:
            print(Style.error(f"Gagal mengatur Hermes: {key}"))
            return False
    return True


def guided_setup():
    if not check_docker():
        return
    port = prepare_env()
    if not validate_compose():
        print("Perbaiki nilai di .env lalu jalankan wizard lagi.")
        return

    print("\nTahap 1/2: menyalakan 9Router saja.")
    if not prompt_choice("Lanjutkan menjalankan container 9Router", "y"):
        print("Setup disimpan. Jalankan wizard lagi saat siap.")
        return
    started, _ = compose("up", "-d", "9router")
    if not started:
        return
    wait_for_router(port)

    print(f"\nBuka dashboard: http://localhost:{port}")
    print("Login memakai password awal yang tersimpan di .env.")
    print("Di dashboard, tambahkan provider/model dan buat endpoint API key.")
    input("Tekan Enter setelah API key endpoint siap, atau Ctrl+C untuk berhenti: ")

    endpoint_key = getpass.getpass("Tempel endpoint API key 9Router (input tersembunyi): ").strip()
    if not endpoint_key:
        print("Key tidak diubah. 9Router tetap aktif; jalankan wizard lagi untuk melanjutkan.")
        return
    set_env_value("NINE_ROUTER_API_KEY", endpoint_key)

    model_ids = fetch_model_ids(port, endpoint_key)
    if model_ids:
        print("Model tersedia:")
        for available_id in model_ids:
            print(f"  - {available_id}")
    else:
        print(Style.warning("Daftar model belum bisa dibaca. Pastikan provider dan key sudah benar."))

    default_model = model_ids[0] if model_ids else ""
    model_id = input(f"ID model untuk Hermes [{default_model}]: ").strip() or default_model
    if not model_id:
        print("ID model diperlukan. Key tersimpan; jalankan wizard lagi setelah model siap.")
        return

    if not validate_compose():
        return
    print("\nMengatur Hermes dan menyalakan kedua service...")
    if not configure_hermes(model_id):
        print("Konfigurasi belum selesai. Baca bagian troubleshooting di README.")
        return
    started, _ = compose("up", "-d")
    if not started:
        return
    print(Style.success("Deploy lokal selesai."))
    print(f"Dashboard 9Router: http://localhost:{port}")
    print("Status: pilih menu Status. Log: pilih menu Logs.")


def show_status():
    if validate_compose():
        compose("ps")


def show_logs():
    service = input("Service [hermes/9router, default hermes]: ").strip().lower() or "hermes"
    if service not in ("hermes", "9router"):
        print("Pilih hermes atau 9router.")
        return
    compose("logs", "--tail", "100", "-f", service)


def show_help():
    print("\nWizard menjalankan dua container lokal dan menyimpan data di named volumes.")
    print("- Setup: buat .env, start 9Router, masukkan endpoint key dan model, start Hermes.")
    print("- Status: lihat container aktif dan port.")
    print("- Logs: ikuti log Hermes atau 9Router; Ctrl+C untuk kembali.")
    print("- Stop: hentikan container tanpa menghapus volume/database.")
    print("- Validasi: python3 wizard.py --check")
    print("Dokumentasi: README.md dan docs/architecture.md, docs/how-it-works.md,")
    print("docs/wiki.md, docs/troubleshooting.md.")
    print("Kaggle hanya untuk sesi sementara; bukan host service 24/7.")


def menu():
    while True:
        print("\n" + Style.title("Pilih tindakan"))
        print("  1) Setup / deploy terpandu")
        print("  2) Status service")
        print("  3) Lihat log")
        print("  4) Start ulang stack")
        print("  5) Stop stack (data tetap disimpan)")
        print("  6) Bantuan")
        print("  q) Keluar")
        choice = input("Pilihan: ").strip().lower()
        if choice == "1":
            guided_setup()
        elif choice == "2":
            show_status()
        elif choice == "3":
            show_logs()
        elif choice == "4":
            if validate_compose():
                compose("up", "-d")
        elif choice == "5":
            if prompt_choice("Hentikan service tanpa menghapus data", "y"):
                compose("down")
        elif choice == "6":
            show_help()
        elif choice in ("q", "quit", "exit"):
            return
        else:
            print("Pilihan tidak dikenal. Ketik 1-6 atau q.")


def main():
    parser = argparse.ArgumentParser(
        description="Wizard interaktif untuk deploy Hermes + 9Router dengan Docker Compose."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="cek Docker Compose dan validasi .env tanpa mengubah deployment",
    )
    args = parser.parse_args()
    banner()
    if args.check:
        if check_docker() and validate_compose():
            return 0
        return 1
    if not ENV_TEMPLATE.exists() or not SKILL_FILE.exists():
        print(Style.error("Jalankan wizard dari salinan repo lengkap; file template/skill tidak ditemukan."))
        return 1
    try:
        menu()
    except KeyboardInterrupt:
        print("\nDihentikan. Container dan data yang sudah dibuat tidak dihapus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())