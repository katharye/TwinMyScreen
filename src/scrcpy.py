# SPDX-License-Identifier: GPL-3.0-or-later
import os
import shutil
import subprocess

from .errors import ToolMissing


class Scrcpy:
    """Сборка аргументов и запуск scrcpy."""

    def __init__(self):
        self.binary = shutil.which("scrcpy")

    def _require(self) -> str:
        if not self.binary:
            raise ToolMissing("scrcpy не найден. Установи: sudo pacman -S scrcpy")
        return self.binary

    def version(self) -> str:
        out = subprocess.run([self._require(), "--version"], capture_output=True, text=True)
        return out.stdout.splitlines()[0] if out.stdout else "?"

    def build_args(self, serial: str, screen: str, audio: str, extra: list[str]) -> list[str]:
        args = [self._require(), "-s", serial]
        if audio == "off":
            args.append("--no-audio")
        elif audio == "only":
            args += ["--no-video", "--no-control"]
        # гашение экрана работает только при включённом управлении
        control = audio != "only" and "--no-control" not in extra
        if screen == "off" and control:
            args.append("--turn-screen-off")
        return args + extra

    def launch(self, args: list[str]) -> None:
        """Заменяет процесс на scrcpy: сигналы и код возврата как у родного."""
        os.execvp(args[0], args)
