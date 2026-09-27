from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass


INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008


SendInput = ctypes.windll.user32.SendInput


try:
    ULONG_PTR = wintypes.ULONG_PTR
except AttributeError:
    ULONG_PTR = wintypes.WPARAM


@dataclass(slots=True, frozen=True)
class KeySpec:
    name: str
    scan_code: int
    extended: bool = False


CTRL = KeySpec("ctrl", 0x1D)
ALT = KeySpec("alt", 0x38)
F = KeySpec("f", 0x21)
L = KeySpec("l", 0x26)
V = KeySpec("v", 0x2F)
ENTER = KeySpec("enter", 0x1C)
ESCAPE = KeySpec("escape", 0x01)


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUTUNION)]


SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
SendInput.restype = wintypes.UINT


class ScancodeKeyboardSender:
    """Отправляет клавиши в Windows через scan codes."""

    def send_shortcut(self, shortcut: str) -> None:
        if shortcut == "ctrl_f":
            self.send_combination((CTRL, F))
            return
        if shortcut == "ctrl_l":
            self.send_combination((CTRL, L))
            return
        if shortcut == "ctrl_v":
            self.send_combination((CTRL, V))
            return
        if shortcut == "alt_enter":
            self.send_combination((ALT, ENTER))
            return
        raise ValueError(f"Неизвестное сочетание: {shortcut}")

    def send_key(self, key_name: str) -> None:
        mapping = {
            "enter": ENTER,
            "escape": ESCAPE,
        }
        key = mapping.get(key_name)
        if key is None:
            raise ValueError(f"Неизвестная клавиша: {key_name}")
        self._send_key_event(key, key_up=False)
        self._send_key_event(key, key_up=True)

    def send_combination(self, keys: tuple[KeySpec, ...]) -> None:
        for key in keys:
            self._send_key_event(key, key_up=False)
        for key in reversed(keys):
            self._send_key_event(key, key_up=True)

    def _send_key_event(self, key: KeySpec, key_up: bool) -> None:
        flags = KEYEVENTF_SCANCODE
        if key.extended:
            flags |= KEYEVENTF_EXTENDEDKEY
        if key_up:
            flags |= KEYEVENTF_KEYUP
        event = INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(0, key.scan_code, flags, 0, 0),
        )
        result = SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
        if result != 1:
            error_code = ctypes.get_last_error()
            if error_code:
                raise OSError(f"SendInput не отправил событие клавиатуры. WinError={error_code}")
            raise OSError(
                "SendInput не отправил событие клавиатуры. Возможна блокировка фокуса/UIPI."
            )
