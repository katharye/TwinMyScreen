# SPDX-License-Identifier: GPL-3.0-or-later
"""Поиск телефонов по mDNS через библиотеку zeroconf (adb mdns на Arch не работает)."""
import re
from dataclasses import dataclass

from .errors import ToolMissing

CONNECT = "_adb-tls-connect._tcp"
PAIRING = "_adb-tls-pairing._tcp"
_ID_RE = re.compile(r"^adb-(.+)-[^-]+$")  # adb-<серийник>-<суффикс>; формат проверить на телефоне


@dataclass
class MdnsService:
    name: str
    kind: str
    host: str
    port: int

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def device_id(self) -> str:
        m = _ID_RE.match(self.name)
        return m.group(1) if m else self.name


class MdnsScanner:
    """Слушает сервисы ADB в сети. Использовать как контекстный менеджер."""

    def __init__(self):
        try:
            from zeroconf import IPVersion, ServiceBrowser, ServiceListener, Zeroconf
        except ImportError:
            raise ToolMissing("Не найдена библиотека zeroconf. Установи: sudo pacman -S python-zeroconf")
        self._found: dict[str, MdnsService] = {}
        scanner = self

        class Listener(ServiceListener):
            def add_service(self, zc, type_, name):
                self._store(zc, type_, name)

            def update_service(self, zc, type_, name):
                self._store(zc, type_, name)

            def remove_service(self, zc, type_, name):
                scanner._found.pop(name, None)

            def _store(self, zc, type_, name):
                info = zc.get_service_info(type_, name, timeout=2000)
                addrs = info.parsed_addresses(IPVersion.V4Only) if info else []
                if addrs:
                    kind = type_.removesuffix(".local.")
                    instance = name.removesuffix(f".{type_}")
                    scanner._found[name] = MdnsService(instance, kind, addrs[0], info.port)

        self._zc = Zeroconf()
        self._browser = ServiceBrowser(
            self._zc, [f"{CONNECT}.local.", f"{PAIRING}.local."], Listener())

    def services(self) -> list[MdnsService]:
        return list(self._found.values())

    def close(self) -> None:
        self._browser.cancel()
        self._zc.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
