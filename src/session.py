# SPDX-License-Identifier: GPL-3.0-or-later
from .adb import Adb
from .config import Config
from .discovery import Discovery
from .errors import DeviceNotFound
from .registry import Device, Registry


class Session:
    """Сценарий «найти телефон и подготовить подключение»."""

    def __init__(self, adb: Adb, registry: Registry, config: Config):
        self.adb = adb
        self.registry = registry
        self.config = config
        self.discovery = Discovery()

    def prepare(self, name: str | None, transport: str, timeout: float) -> tuple[Device, str]:
        """Возвращает устройство и serial/адрес, который нужно отдать scrcpy."""
        device = self.registry.resolve(name)
        usb = device.device_id in self.adb.usb_serials()

        if transport == "usb" and not usb:
            raise DeviceNotFound(f"'{device.name}' не подключён по USB")
        if transport == "usb" or (transport == "auto" and usb):
            return device, device.device_id

        service = self.discovery.wait_connect(device.device_id, timeout)
        self.adb.connect(service.address)
        return device, service.address
