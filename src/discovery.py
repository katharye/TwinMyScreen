# SPDX-License-Identifier: GPL-3.0-or-later
import time

from .errors import DeviceNotFound, WaitTimeout
from .mdns import CONNECT, PAIRING, MdnsScanner, MdnsService


class Discovery:
    """Поиск телефонов в сети (поверх MdnsScanner).

    Позже тут появится поток событий для демона и GUI.
    """

    def __init__(self, interval: float = 0.5):
        self.interval = interval

    def snapshot(self, duration: float = 2.0) -> list[MdnsService]:
        """Разовый список всего, что нашлось за `duration` секунд."""
        with MdnsScanner() as scanner:
            time.sleep(duration)
            return scanner.services()

    def _wait(self, kind: str, match, timeout: float) -> MdnsService:
        deadline = time.monotonic() + timeout
        with MdnsScanner() as scanner:
            while True:
                for svc in scanner.services():
                    if svc.kind == kind and match(svc):
                        return svc
                if time.monotonic() >= deadline:
                    raise WaitTimeout("Телефон не найден в сети. Включена ли беспроводная отладка?")
                time.sleep(self.interval)

    def wait_connect(self, device_id: str, timeout: float) -> MdnsService:
        return self._wait(CONNECT, lambda s: s.device_id == device_id, timeout)

    def wait_pairing(self, timeout: float) -> MdnsService:
        return self._wait(PAIRING, lambda s: True, timeout)

    def connect_service_for_host(self, host: str, timeout: float) -> MdnsService:
        try:
            return self._wait(CONNECT, lambda s: s.host == host, timeout)
        except WaitTimeout:
            raise DeviceNotFound("После сопряжения телефон не появился в сети")
