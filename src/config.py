# SPDX-License-Identifier: GPL-3.0-or-later
import os
import tomllib
from pathlib import Path

from .errors import UsageError

DEFAULTS = {
    "screen": "off",      # on | off
    "audio": "on",        # on | off | only
    "transport": "auto",  # auto | usb | wifi
    "timeout": 10,        # секунды ожидания телефона
}


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "twinmyscreen"


class Config:
    """Приоритет значений: флаг CLI -> config.toml -> DEFAULTS."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else config_dir() / "config.toml"
        self._data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            with open(self.path, "rb") as f:
                return tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise UsageError(f"Ошибка в конфиге {self.path}: {e}")

    def get(self, key: str, cli_value=None):
        if cli_value is not None:
            return cli_value
        return self._data.get(key, DEFAULTS[key])
