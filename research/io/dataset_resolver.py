"""Dataset resolution helpers for cloud-first study orchestration.

Supports deterministic resolution for:
- provider=repo_path (repo-local files)
- provider=url (downloaded to a local cache path)

Backward compatibility:
- entries without `provider` are treated as `repo_path`.
"""

from __future__ import annotations

import hashlib
import shutil
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SUPPORTED_PROVIDERS = {"repo_path", "url"}
_SHA256_HEX_LEN = 64


def validate_dataset_entry(dataset_id: str, entry: dict[str, Any]) -> list[str]:
    """Return human-readable validation errors for a single registry entry."""
    if not isinstance(entry, dict):
        return [f"dataset '{dataset_id}' must be a mapping entry"]

    provider = str(entry.get("provider", "repo_path")).strip() or "repo_path"
    errors: list[str] = []
    if provider not in SUPPORTED_PROVIDERS:
        errors.append(
            f"dataset '{dataset_id}' has unsupported provider '{provider}' "
            f"(allowed: {sorted(SUPPORTED_PROVIDERS)})"
        )
        return errors

    if provider == "repo_path":
        dataset_path = str(entry.get("path", "")).strip()
        if dataset_path == "":
            errors.append(f"dataset '{dataset_id}' provider=repo_path requires non-empty 'path'")
        return errors

    dataset_url = str(entry.get("url", "")).strip()
    filename = str(entry.get("filename", "")).strip()
    if dataset_url == "":
        errors.append(f"dataset '{dataset_id}' provider=url requires non-empty 'url'")
    else:
        parsed = urllib.parse.urlparse(dataset_url)
        if parsed.scheme not in {"http", "https"}:
            errors.append(
                f"dataset '{dataset_id}' provider=url requires http/https URL; got scheme '{parsed.scheme or '<none>'}'"
            )
        if parsed.netloc == "":
            errors.append(f"dataset '{dataset_id}' provider=url requires URL host; got '{dataset_url}'")
    if filename == "":
        errors.append(f"dataset '{dataset_id}' provider=url requires non-empty 'filename'")

    sha256_value = entry.get("sha256")
    if sha256_value not in (None, ""):
        sha_text = str(sha256_value).strip().lower()
        if len(sha_text) != _SHA256_HEX_LEN or any(ch not in "0123456789abcdef" for ch in sha_text):
            errors.append(
                f"dataset '{dataset_id}' sha256 must be 64 lowercase hex chars when provided; got '{sha256_value}'"
            )

    return errors


def resolve_dataset_to_local_csv(
    *,
    dataset_id: str,
    entry: dict[str, Any],
    repo_root: Path,
    cache_dir: Path,
) -> Path:
    """Resolve one dataset entry to a deterministic local CSV file path."""
    errors = validate_dataset_entry(dataset_id, entry)
    if errors:
        raise ValueError("; ".join(errors))

    provider = str(entry.get("provider", "repo_path")).strip() or "repo_path"
    if provider == "repo_path":
        return _resolve_repo_path_entry(dataset_id=dataset_id, entry=entry, repo_root=repo_root)
    if provider == "url":
        return _resolve_url_entry(dataset_id=dataset_id, entry=entry, cache_dir=cache_dir)

    raise ValueError(f"dataset '{dataset_id}' has unsupported provider '{provider}'")


def _resolve_repo_path_entry(*, dataset_id: str, entry: dict[str, Any], repo_root: Path) -> Path:
    dataset_path = str(entry.get("path", "")).strip()
    candidate = Path(dataset_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (repo_root / candidate).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"dataset '{dataset_id}' repo_path not found: {resolved}")
    return resolved


def _resolve_url_entry(*, dataset_id: str, entry: dict[str, Any], cache_dir: Path) -> Path:
    dataset_url = str(entry["url"]).strip()
    filename = str(entry["filename"]).strip()
    expected_sha256 = str(entry.get("sha256", "")).strip().lower() or None

    target_dir = (cache_dir / "url" / dataset_id).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = (target_dir / filename).resolve()

    if target_file.exists():
        _verify_sha256(path=target_file, expected_sha256=expected_sha256, dataset_id=dataset_id)
        return target_file

    tmp_file = target_file.with_suffix(target_file.suffix + ".tmp")
    with urllib.request.urlopen(dataset_url, timeout=60) as response, tmp_file.open("wb") as out:
        shutil.copyfileobj(response, out)

    _verify_sha256(path=tmp_file, expected_sha256=expected_sha256, dataset_id=dataset_id)
    tmp_file.replace(target_file)
    return target_file


def _verify_sha256(*, path: Path, expected_sha256: str | None, dataset_id: str) -> None:
    if expected_sha256 is None:
        return
    actual = _sha256_file(path)
    if actual != expected_sha256:
        raise ValueError(
            f"dataset '{dataset_id}' checksum mismatch for {path}: "
            f"expected {expected_sha256}, got {actual}"
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
