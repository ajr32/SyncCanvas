"""Validated Canvas settings for SyncCanvas; no third-party settings package."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlsplit

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class SettingsError(ValueError):
    """Invalid application configuration (never includes a secret)."""


@dataclass(frozen=True)
class CanvasSettings:
    url: str = ""
    token: str = ""

    def __post_init__(self) -> None:
        if bool(self.url) != bool(self.token):
            raise SettingsError("Canvas URL and token must both be configured.")
        if self.url:
            parsed = urlsplit(self.url)
            if (parsed.scheme != "https" or not parsed.hostname or
                    parsed.username or parsed.password or parsed.query or
                    parsed.fragment or parsed.path not in ("", "/")):
                raise SettingsError("Canvas URL must be an HTTPS site root without credentials or query.")
            if any(c.isspace() for c in self.token):
                raise SettingsError("Canvas token must not contain whitespace.")


def read_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    """Read only SyncCanvas Canvas keys; never mutate process environment."""
    result: dict[str, str] = {}
    if not path.is_file():
        return result
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip()
        if name not in ("SYNCCANVAS_CANVAS_URL", "SYNCCANVAS_CANVAS_TOKEN"):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        result[name] = value
    return result


def get_settings(environ: dict[str, str] | None = None, env_file: Path = ENV_FILE) -> CanvasSettings:
    values = read_env_file(env_file)
    values.update(os.environ if environ is None else environ)
    return CanvasSettings(
        url=values.get("SYNCCANVAS_CANVAS_URL", "").strip(),
        token=values.get("SYNCCANVAS_CANVAS_TOKEN", "").strip(),
    )


def load_env_file() -> None:
    """Compatibility helper: load Canvas variables without overriding process settings."""
    for name, value in read_env_file().items():
        os.environ.setdefault(name, value)


def get_canvas_settings() -> tuple[str, str]:
    settings = get_settings()
    return settings.url, settings.token
