# SPDX-License-Identifier: GPL-3.0-or-later
import shutil
import subprocess

from .errors import ToolMissing, TwinError

class Adb:
    """Тонкая обёртка над командой adb."""

    def __init__(self):
        self.binary = shutil.which("adb")

    def _require(self) -> str:
        if not self.binary:
            raise ToolMissing("adb не найден. Установи: sudo pacman -S android-tools")
        return self.binary

    def run(self, *args: str, timeout: float = 15) -> subprocess.CompletedProcess:
        try:
            return subprocess.run([self._require(), *args], capture_output=True,
                                  text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise TwinError(f"adb {' '.join(args)}: не ответил за {timeout} с")

    def version(self) -> str:
        out = self.run("version").stdout.strip().splitlines()
        return out[0] if out else "?"

    def usb_serials(self) -> list[str]:
        """Серийники устройств, подключённых по проводу (не по Wi-Fi)."""
        out = self.run("devices").stdout.splitlines()[1:]
        serials = []
        for line in out:
            parts = line.split()
            if len(parts) == 2 and parts[1] == "device":
                if ":" not in parts[0] and "_adb-tls" not in parts[0]:
                    serials.append(parts[0])
        return serials

    def pair(self, address: str, code: str) -> None:
        r = self.run("pair", address, code)
        if r.returncode != 0 or "Successfully" not in r.stdout:
            raise TwinError(f"Сопряжение не удалось: {(r.stdout + r.stderr).strip()}")

    def connect(self, address: str) -> None:
        r = self.run("connect", address)
        if "connected" not in r.stdout:
            raise TwinError(f"adb connect не удался: {(r.stdout + r.stderr).strip()}")

    def disconnect(self, address: str | None = None) -> None:
        self.run("disconnect", *([address] if address else []))
