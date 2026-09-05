from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AI_CREDENTIALS_VAULT_VERSION = "ai-credentials-vault.v1.34"
MAX_GEMINI_SLOTS = 5
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_VAULT_PATH = PROJECT_ROOT / "data" / "secrets" / "ai_credentials.enc"
DEFAULT_SECRET_KEY_PATH = PROJECT_ROOT / "data" / "secrets" / "tradevision_secret.key"
def _vault_path() -> Path:
    return Path(os.getenv("TRADEVISION_AI_CREDENTIAL_VAULT_PATH", str(DEFAULT_VAULT_PATH)))


def _secret_key_path() -> Path:
    return Path(os.getenv("TRADEVISION_SECRET_KEY_FILE", str(DEFAULT_SECRET_KEY_PATH)))


def build_ai_credential_status() -> dict[str, Any]:
    vault = _load_vault_plaintext() if _secret_key() else _empty_vault()
    gemini_slots = []
    for slot in range(1, MAX_GEMINI_SLOTS + 1):
        value = vault["gemini"].get(f"slot_{slot}", "")
        gemini_slots.append(_slot_status(provider="gemini", slot=slot, value=value))
    grok_value = vault["grok"].get("api_key", "")
    return {
        "vault_version": AI_CREDENTIALS_VAULT_VERSION,
        "vault_locked": not bool(_secret_key()),
        "vault_path": str(_vault_path()),
        "secret_key_configured": bool(_secret_key()),
        "secret_key_source": _secret_key_source(),
        "secret_key_path": str(_secret_key_path()),
        "local_secret_key_path": str(_secret_key_path()),
        "secret_key_file_exists": _secret_key_path().exists(),
        "local_secret_key_file_exists": _secret_key_path().exists(),
        "vault_file_exists": _vault_path().exists(),
        "gemini": {
            "configured_slots": sum(1 for item in gemini_slots if item["configured"]),
            "active_slot": _first_configured_slot(gemini_slots),
            "slots": gemini_slots,
            "fallback_slots_supported": MAX_GEMINI_SLOTS,
        },
        "grok": {
            **_slot_status(provider="grok", slot=None, value=grok_value),
            "provider": "grok",
        },
        "security": _security_policy(),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def save_gemini_credential(slot: int, api_key: str, label: str | None = None) -> dict[str, Any]:
    _assert_unlocked()
    if slot < 1 or slot > MAX_GEMINI_SLOTS:
        raise ValueError("Gemini slot must be between 1 and 5.")
    clean = _validate_secret(api_key)
    vault = _load_vault_plaintext()
    vault["gemini"][f"slot_{slot}"] = clean
    vault["metadata"][f"gemini_slot_{slot}"] = _metadata(label=label, value=clean)
    _save_vault_plaintext(vault)
    return build_ai_credential_status()


def save_grok_credential(api_key: str, label: str | None = None) -> dict[str, Any]:
    _assert_unlocked()
    clean = _validate_secret(api_key)
    vault = _load_vault_plaintext()
    vault["grok"]["api_key"] = clean
    vault["metadata"]["grok_api_key"] = _metadata(label=label, value=clean)
    _save_vault_plaintext(vault)
    return build_ai_credential_status()


def clear_gemini_credential(slot: int) -> dict[str, Any]:
    _assert_unlocked()
    if slot < 1 or slot > MAX_GEMINI_SLOTS:
        raise ValueError("Gemini slot must be between 1 and 5.")
    vault = _load_vault_plaintext()
    vault["gemini"][f"slot_{slot}"] = ""
    vault["metadata"].pop(f"gemini_slot_{slot}", None)
    _save_vault_plaintext(vault)
    return build_ai_credential_status()


def clear_grok_credential() -> dict[str, Any]:
    _assert_unlocked()
    vault = _load_vault_plaintext()
    vault["grok"]["api_key"] = ""
    vault["metadata"].pop("grok_api_key", None)
    _save_vault_plaintext(vault)
    return build_ai_credential_status()


def test_ai_credential(provider: str, slot: int | None = None) -> dict[str, Any]:
    status = build_ai_credential_status()
    normalized = provider.strip().lower()
    if normalized == "gemini":
        if slot is None:
            slot = status["gemini"]["active_slot"]
        configured = bool(slot and 1 <= slot <= MAX_GEMINI_SLOTS and status["gemini"]["slots"][slot - 1]["configured"])
        target = f"gemini_slot_{slot or 'none'}"
    elif normalized == "grok":
        configured = bool(status["grok"]["configured"])
        target = "grok_api_key"
    else:
        raise ValueError("provider must be gemini or grok")
    return {
        "test_version": f"{AI_CREDENTIALS_VAULT_VERSION}.test-stub",
        "provider": normalized,
        "target": target,
        "status": "configured_not_live_tested" if configured else "missing",
        "configured": configured,
        "live_network_call_performed": False,
        "message": "Credential is present in the local backend vault. Live provider call is added in the next version.",
        "security": _security_policy(),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def get_gemini_api_key(slot: int) -> str | None:
    if not _secret_key() or slot < 1 or slot > MAX_GEMINI_SLOTS:
        return None
    return _load_vault_plaintext()["gemini"].get(f"slot_{slot}") or None


def get_grok_api_key() -> str | None:
    if not _secret_key():
        return None
    return _load_vault_plaintext()["grok"].get("api_key") or None


def _metadata(*, label: str | None, value: str) -> dict[str, Any]:
    return {
        "label": label or "",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": _fingerprint(value),
        "last4": value[-4:],
    }


def _slot_status(*, provider: str, slot: int | None, value: str) -> dict[str, Any]:
    configured = bool(value)
    return {
        "provider": provider,
        "slot": slot,
        "configured": configured,
        "fingerprint": _fingerprint(value) if configured else None,
        "last4": value[-4:] if configured else None,
        "display": f"****{value[-4:]}" if configured else "not configured",
        "secret_returned_to_frontend": False,
    }


def _first_configured_slot(slots: list[dict[str, Any]]) -> int | None:
    for item in slots:
        if item["configured"]:
            return int(item["slot"])
    return None


def _security_policy() -> dict[str, Any]:
    return {
        "frontend_receives_plaintext_secret": False,
        "local_storage_used": False,
        "browser_password_login_supported": False,
        "cookie_or_session_capture_supported": False,
        "vault_requires_tradevision_secret_key": True,
        "secret_key_file_supported": True,
        "secret_key_file_path_returned_without_secret": True,
        "network_test_in_this_version": False,
    }


def _validate_secret(value: str) -> str:
    clean = value.strip()
    if len(clean) < 12:
        raise ValueError("Credential is too short.")
    lowered = clean.lower()
    if " " in clean or lowered.startswith("http://") or lowered.startswith("https://"):
        raise ValueError("Credential must be an API key/token, not a URL or sentence.")
    return clean


def _assert_unlocked() -> None:
    if not _secret_key():
        raise RuntimeError("Credential vault locked. Set TRADEVISION_SECRET_KEY before saving AI credentials.")


def _secret_key() -> str:
    env_value = os.getenv("TRADEVISION_SECRET_KEY", "").strip()
    if env_value:
        return env_value
    try:
        return _secret_key_path().read_text(encoding="utf-8").strip() if _secret_key_path().exists() else ""
    except OSError:
        return ""


def _secret_key_source() -> str:
    if os.getenv("TRADEVISION_SECRET_KEY", "").strip():
        return "TRADEVISION_SECRET_KEY"
    if _secret_key_path().exists() and _secret_key():
        return "TRADEVISION_SECRET_KEY_FILE"
    return "missing"


def _load_vault_plaintext() -> dict[str, Any]:
    if not _vault_path().exists():
        return _empty_vault()
    try:
        payload = json.loads(_vault_path().read_text(encoding="utf-8"))
        encrypted = base64.b64decode(payload["ciphertext"])
        nonce = base64.b64decode(payload["nonce"])
        expected = payload["hmac"]
        actual = _hmac_hex(nonce + encrypted)
        if not hmac.compare_digest(actual, expected):
            raise RuntimeError("Credential vault integrity check failed.")
        plain = _xor_stream(encrypted, nonce)
        decoded = json.loads(plain.decode("utf-8"))
        return _normalize_vault(decoded)
    except Exception as exc:
        raise RuntimeError(f"Credential vault could not be opened: {exc}") from exc


def _save_vault_plaintext(vault: dict[str, Any]) -> None:
    normalized = _normalize_vault(vault)
    _vault_path().parent.mkdir(parents=True, exist_ok=True)
    nonce = os.urandom(16)
    plain = json.dumps(normalized, sort_keys=True).encode("utf-8")
    encrypted = _xor_stream(plain, nonce)
    payload = {
        "version": AI_CREDENTIALS_VAULT_VERSION,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(encrypted).decode("ascii"),
        "hmac": _hmac_hex(nonce + encrypted),
    }
    _vault_path().write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _empty_vault() -> dict[str, Any]:
    return {
        "version": AI_CREDENTIALS_VAULT_VERSION,
        "gemini": {f"slot_{idx}": "" for idx in range(1, MAX_GEMINI_SLOTS + 1)},
        "grok": {"api_key": ""},
        "metadata": {},
    }


def _normalize_vault(vault: dict[str, Any]) -> dict[str, Any]:
    clean = _empty_vault()
    clean["version"] = str(vault.get("version") or AI_CREDENTIALS_VAULT_VERSION)
    for idx in range(1, MAX_GEMINI_SLOTS + 1):
        clean["gemini"][f"slot_{idx}"] = str(vault.get("gemini", {}).get(f"slot_{idx}", ""))
    clean["grok"]["api_key"] = str(vault.get("grok", {}).get("api_key", ""))
    clean["metadata"] = vault.get("metadata", {}) if isinstance(vault.get("metadata"), dict) else {}
    return clean


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _hmac_hex(value: bytes) -> str:
    return hmac.new(_key_bytes(), value, hashlib.sha256).hexdigest()


def _key_bytes() -> bytes:
    return hashlib.sha256(_secret_key().encode("utf-8")).digest()


def _xor_stream(value: bytes, nonce: bytes) -> bytes:
    key = _key_bytes()
    output = bytearray()
    counter = 0
    while len(output) < len(value):
        block = hashlib.sha256(key + nonce + counter.to_bytes(8, "big")).digest()
        output.extend(block)
        counter += 1
    return bytes(item ^ output[idx] for idx, item in enumerate(value))
