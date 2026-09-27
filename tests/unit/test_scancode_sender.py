from __future__ import annotations

import ctypes

from app.services.scancode_sender import (
    ALT,
    CTRL,
    ENTER,
    INPUT,
    KEYBDINPUT,
    L,
    MOUSEINPUT,
    _INPUTUNION,
    ScancodeKeyboardSender,
)


def test_input_union_includes_mouse_structure_size():
    assert ctypes.sizeof(_INPUTUNION) >= ctypes.sizeof(MOUSEINPUT)
    assert ctypes.sizeof(INPUT) > ctypes.sizeof(KEYBDINPUT)


def test_send_shortcut_ctrl_l_uses_expected_scancodes(monkeypatch):
    sender = ScancodeKeyboardSender()
    events = []

    def fake_send_key_event(key, key_up):
        events.append((key.name, key_up))

    monkeypatch.setattr(sender, "_send_key_event", fake_send_key_event)

    sender.send_shortcut("ctrl_l")

    assert events == [
        (CTRL.name, False),
        (L.name, False),
        (L.name, True),
        (CTRL.name, True),
    ]


def test_send_shortcut_alt_enter_uses_expected_scancodes(monkeypatch):
    sender = ScancodeKeyboardSender()
    events = []

    def fake_send_key_event(key, key_up):
        events.append((key.name, key_up))

    monkeypatch.setattr(sender, "_send_key_event", fake_send_key_event)

    sender.send_shortcut("alt_enter")

    assert events == [
        (ALT.name, False),
        (ENTER.name, False),
        (ENTER.name, True),
        (ALT.name, True),
    ]
