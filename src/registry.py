# SPDX-License-Identifier: GPL-3.0-or-later
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import config_dir
from .errors import DeviceNotFound, NotPaired


@dataclass
class Device:
    name: str
    device_id: str  # стабильный ID (серийник из mDNS-имени), не IP/порт


class Registry:
    """Список сопряжённых устройств в devices.json."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else config_dir() / "devices.json"
        self.devices: list[Device] = []
        self.default: str | None = None
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text())
        self.devices = [Device(**d) for d in data.get("devices", [])]
        self.default = data.get("default")

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"default": self.default, "devices": [asdict(d) for d in self.devices]}
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def add(self, device: Device) -> None:
        self.devices = [d for d in self.devices if d.device_id != device.device_id]
        self.devices.append(device)
        if self.default is None:
            self.default = device.name
        self.save()

    def remove(self, name: str) -> None:
        device = self.resolve(name)
        self.devices.remove(device)
        if self.default == device.name:
            self.default = self.devices[0].name if self.devices else None
        self.save()

    def resolve(self, name: str | None = None) -> Device:
        """Найти устройство по имени; без имени берётся устройство по умолчанию."""
        if not self.devices:
            raise NotPaired("Нет сопряжённых устройств. Выполни: twinmyscreen pair")
        wanted = name or self.default
        for d in self.devices:
            if d.name == wanted:
                return d
        raise DeviceNotFound(f"Устройство '{wanted}' не найдено в реестре")
