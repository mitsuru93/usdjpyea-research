"""Path helpers for deterministic study-runner orchestration."""

from __future__ import annotations

from pathlib import Path


def resolve_local_path(raw_path: str | Path, base_dir: Path) -> Path:
    """Resolve absolute paths directly and relative paths from base_dir."""
    path = Path(raw_path)
    return path if path.is_absolute() else (base_dir / path)


def ensure_directory(path: Path) -> Path:
    """Create path if needed and return it for inline composition."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_label(label: str) -> str:
    """Convert run labels to conservative folder/file-safe tokens."""
    clean = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in label.strip())
    return clean or "run"
