# SPDX-License-Identifier: GPL-3.0-or-later
"""Ошибки программы. Каждая несёт свой код возврата для скриптов."""


class TwinError(Exception):
    exit_code = 1


class UsageError(TwinError):
    exit_code = 2


class DeviceNotFound(TwinError):
    exit_code = 3


class NotPaired(TwinError):
    exit_code = 4


class ToolMissing(TwinError):
    exit_code = 5


class WaitTimeout(TwinError):
    exit_code = 6


class ScrcpyFailed(TwinError):
    exit_code = 7
