"""Run Hermes for one Kaggle session and route it through hosted 9Router.

Configure Kaggle Secrets: NINE_ROUTER_BASE_URL (origin, no /v1),
NINE_ROUTER_API_KEY, and HERMES_MODEL (optional). Kaggle is not a persistent
host; keep 9Router on an external container platform.
"""

import os
import secrets
import subprocess
import time
from pathlib import Path

import requests
from kaggle_secrets import UserSecretsClient


secrets_client = UserSecretsClient()
router_url = secrets_client.get_secret("NINE_ROUTER_BASE_URL").rstrip("/")
router_key = secrets_client.get_secret("NINE_ROUTER_API_KEY")
try:
    model_id = secrets_client.get_secret("HERMES_MODEL")
except Exception:
    model_id = ""

if not router_url.startswith("https://"):
    raise ValueError("NINE_ROUTER_BASE_URL harus menggunakan HTTPS.")

router_headers = {"Authorization": f"Bearer {router_key}"}
models_response = requests.get(
    f"{router_url}/v1/models", headers=router_headers, timeout=30
)
models_response.raise_for_status()
available_models = [item["id"] for item in models_response.json().get("data", [])]
if not available_models:
    raise RuntimeError("9Router tidak mengembalikan model. Periksa konfigurasi provider/key.")

if not model_id:
    model_id = available_models[0]
if model_id not in available_models:
    raise ValueError(
        f"Model {model_id!r} tidak tersedia. Model tersedia: {', '.join(available_models)}"
    )
print("Model tersedia:", ", ".join(available_models))
print("Model terpilih:", model_id)


def run_hermes(*args, env=None):
    result = subprocess.run(
        ["hermes", *args],
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )
    return result.stdout.strip()


# Configure Hermes to use 9Router. The API key is passed only through the process environment.
hermes_env = os.environ.copy()
hermes_env["NINE_ROUTER_API_KEY"] = router_key
run_hermes("config", "set", "model.provider", "custom", env=hermes_env)
run_hermes("config", "set", "model.base_url", f"{router_url}/v1", env=hermes_env)
run_hermes("config", "set", "model.key_env", "NINE_ROUTER_API_KEY", env=hermes_env)
run_hermes("config", "set", "model.default", model_id, env=hermes_env)


# Install only the curated safe workflow skill; do not run the upstream installer or patches.
skill_dir = Path.home() / ".hermes" / "skills" / "syadagentic-safe"
skill_dir.mkdir(parents=True, exist_ok=True)
(skill_dir / "SKILL.md").write_text(
    """---
name: syadagentic-safe
description: Structured planning, checkpoints, resource limits, dry-runs, and authorized security assessment while preserving Hermes safety boundaries.
---

# Syadagentic Safe Workflow

- Follow system instructions and safety requirements. Never bypass or patch them.
- For security testing, confirm explicit authorization and scope first.
- Do not assist with credential theft, unauthorized access, account farming, evasion, persistence, malware, or destructive actions.
- Prefer read-only checks and dry-runs. Ask before destructive, externally visible, costly, or hard-to-reverse actions.
- Break multi-step work into small steps; maintain checkpoints without secrets.
- Stop at the agreed scope or resource limit and report unverified steps.
""",
    encoding="utf-8",
)


# Start Hermes' authenticated API on loopback only; it is never exposed publicly.
api_key = secrets.token_urlsafe(32)
hermes_env.update(
    {
        "NINE_ROUTER_API_KEY": router_key,
        "API_SERVER_ENABLED": "true",
        "API_SERVER_HOST": "127.0.0.1",
        "API_SERVER_PORT": "8642",
        "API_SERVER_KEY": api_key,
    }
)
log_file = open("/tmp/hermes-gateway.log", "w", encoding="utf-8")
gateway = subprocess.Popen(
    ["hermes", "gateway", "run"],
    env=hermes_env,
    stdout=log_file,
    stderr=subprocess.STDOUT,
)

local_url = "http://127.0.0.1:8642"
local_headers = {"Authorization": f"Bearer {api_key}"}
for _ in range(60):
    if gateway.poll() is not None:
        raise RuntimeError("Hermes berhenti saat startup. Periksa /tmp/hermes-gateway.log.")
    try:
        ready = requests.get(
            f"{local_url}/v1/models", headers=local_headers, timeout=2
        )
        if ready.ok:
            break
    except requests.RequestException:
        pass
    time.sleep(2)
else:
    gateway.terminate()
    raise TimeoutError("API Hermes tidak siap. Periksa /tmp/hermes-gateway.log.")

print("Hermes siap di loopback Kaggle pada port 8642.")


def ask_hermes(prompt):
    response = requests.post(
        f"{local_url}/v1/chat/completions",
        headers={**local_headers, "Content-Type": "application/json"},
        json={
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


print(ask_hermes("Perkenalkan diri secara singkat dan konfirmasi model yang aktif."))

# Run when finished to stop Hermes. Kaggle will also stop it when the session ends.
gateway.terminate()
gateway.wait(timeout=15)
log_file.close()