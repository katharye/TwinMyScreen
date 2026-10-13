# SPDX-License-Identifier: GPL-3.0-or-later
import argparse
import json
import sys

from . import __version__
from .adb import Adb
from .config import Config
from .mdns import CONNECT
from .errors import TwinError, UsageError
from .registry import Device, Registry
from .scrcpy import Scrcpy
from .session import Session

COMMANDS = {"connect", "pair", "disconnect", "list", "forget", "doctor"}


class App:
    """Склеивает компоненты; каждая команда это метод cmd_*."""

    def __init__(self, args: argparse.Namespace, extra: list[str]):
        self.args = args
        self.extra = extra
        self.config = Config(getattr(args, "config", None))
        self.registry = Registry()
        self.adb = Adb()
        self.scrcpy = Scrcpy()
        self.session = Session(self.adb, self.registry, self.config)

    def cmd_connect(self) -> int:
        a = self.args
        transport = self.config.get("transport", a.transport)
        timeout = float(self.config.get("timeout", a.timeout))
        device, target = self.session.prepare(a.name, transport, timeout)
        if a.no_launch:
            print(f"Подключено: {device.name} ({target})")
            return 0
        argv = self.scrcpy.build_args(target, self.config.get("screen", a.screen),
                                      self.config.get("audio", a.audio), self.extra)
        self.scrcpy.launch(argv)
        return 0

    def cmd_pair(self) -> int:
        a = self.args
        timeout = float(self.config.get("timeout", a.timeout))
        address = a.address
        if not address:
            print("Жду сервис сопряжения (Параметры разработчика -> Беспроводная отладка "
                  "-> Подключение устройства с помощью кода)...")
            address = self.session.discovery.wait_pairing(timeout).address
        code = a.code or input("Код сопряжения с экрана телефона: ").strip()
        self.adb.pair(address, code)
        host = address.rpartition(":")[0]
        service = self.session.discovery.connect_service_for_host(host, timeout)
        name = a.name or f"phone-{len(self.registry.devices) + 1}"
        self.registry.add(Device(name=name, device_id=service.device_id))
        print(f"Сопряжено: {name}")
        return 0

    def cmd_list(self) -> int:
        services = self.session.discovery.snapshot()
        online = {s.device_id: s.address for s in services if s.kind == CONNECT}
        usb = set(self.adb.usb_serials())
        rows = []
        for d in self.registry.devices:
            state = [t for t, ok in (("usb", d.device_id in usb), ("wifi", d.device_id in online)) if ok]
            rows.append({"name": d.name, "id": d.device_id, "state": state or ["offline"],
                         "default": d.name == self.registry.default})
        unknown = []
        if self.args.scan:
            known = {d.device_id for d in self.registry.devices}
            unknown = [{"id": s.device_id, "address": s.address}
                       for s in services if s.kind == CONNECT and s.device_id not in known]
        if self.args.json:
            print(json.dumps({"devices": rows, "unknown": unknown}, ensure_ascii=False, indent=2))
            return 0
        if not rows:
            print("Нет сопряжённых устройств.")
        for r in rows:
            mark = "*" if r["default"] else " "
            print(f"{mark} {r['name']:<16} {','.join(r['state']):<10} {r['id']}")
        for u in unknown:
            print(f"? неопознанное: {u['id']} ({u['address']})")
        return 0

    def cmd_disconnect(self) -> int:
        if self.args.all or not self.args.name and not self.registry.devices:
            self.adb.disconnect()
            return 0
        device = self.registry.resolve(self.args.name)
        for s in self.session.discovery.snapshot():
            if s.kind == CONNECT and s.device_id == device.device_id:
                self.adb.disconnect(s.address)
        return 0

    def cmd_forget(self) -> int:
        self.registry.remove(self.args.name)
        print(f"Удалено: {self.args.name}")
        return 0

    def cmd_doctor(self) -> int:
        ok = True
        for label, tool in (("adb", self.adb), ("scrcpy", self.scrcpy)):
            if tool.binary:
                print(f"[ok]   {label}: {tool.version()}")
            else:
                ok = False
                print(f"[fail] {label}: не найден")
        try:
            import zeroconf
            print(f"[ok]   zeroconf: {zeroconf.__version__}")
        except ImportError:
            ok = False
            print("[fail] zeroconf: не найден (sudo pacman -S python-zeroconf)")
        print("[info] Совет: в Параметрах разработчика отключи «тайм-аут авторизации adb», "
              "иначе сопряжение слетает через 7 дней.")
        return 0 if ok else 5


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="twinmyscreen",
                                description="Зеркалирование Android-телефона на ПК")
    p.add_argument("--version", action="version", version=f"twinmyscreen {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def add_common(sp):
        sp.add_argument("--config", help="путь к другому config.toml")

    c = sub.add_parser("connect", help="подключиться и запустить scrcpy")
    add_common(c)
    c.add_argument("name", nargs="?", help="имя устройства (по умолчанию — устройство по умолчанию)")
    c.add_argument("--screen", choices=["on", "off"], help="экран телефона во время трансляции")
    c.add_argument("--audio", choices=["on", "off", "only"], help="передача звука")
    c.add_argument("--transport", choices=["auto", "usb", "wifi"], help="способ подключения")
    c.add_argument("--timeout", type=float, help="сколько секунд ждать телефон")
    c.add_argument("--no-launch", action="store_true", help="только подключиться, без окна")

    s = sub.add_parser("pair", help="сопрячь новое устройство")
    add_common(s)
    s.add_argument("--name", help="имя устройства в реестре")
    s.add_argument("--code", help="код сопряжения (6 цифр)")
    s.add_argument("--address", help="ip:port сервиса сопряжения")
    s.add_argument("--timeout", type=float, help="сколько секунд ждать телефон")

    l = sub.add_parser("list", help="список устройств")
    add_common(l)
    l.add_argument("--scan", action="store_true", help="показать и неопознанные устройства")
    l.add_argument("--json", action="store_true", help="машинный вывод")

    d = sub.add_parser("disconnect", help="разорвать подключение")
    add_common(d)
    d.add_argument("name", nargs="?")
    d.add_argument("--all", action="store_true")

    f = sub.add_parser("forget", help="удалить устройство из реестра")
    add_common(f)
    f.add_argument("name")

    add_common(sub.add_parser("doctor", help="проверить окружение"))
    return p


def split_argv(argv: list[str]) -> tuple[list[str], list[str]]:
    """Отделяет флаги scrcpy после `--`; без подкоманды подставляет connect."""
    extra: list[str] = []
    if "--" in argv:
        i = argv.index("--")
        argv, extra = argv[:i], argv[i + 1:]
    if not argv or (argv[0] not in COMMANDS and argv[0] not in ("-h", "--help", "--version")):
        argv = ["connect", *argv]
    return argv, extra


def main(argv: list[str] | None = None) -> int:
    head, extra = split_argv(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(head)
    try:
        if extra and args.command != "connect":
            raise UsageError("Аргументы после `--` поддерживает только connect")
        return getattr(App(args, extra), f"cmd_{args.command}")()
    except TwinError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return e.exit_code
    except KeyboardInterrupt:
        return 130
