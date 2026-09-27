from __future__ import annotations

import runpy
from pathlib import Path


def test_portable_update_preserves_destination_settings(tmp_path):
    root = Path(__file__).resolve().parents[2]
    namespace = runpy.run_path(str(root / "00_Move.pyw"))
    copy_release = namespace["copy_release_folder"]
    copy_release.__globals__["DESTINATION_ROOT"] = tmp_path / "portable"
    source = tmp_path / "source"
    source.mkdir()
    (source / "SearchDeck.exe").write_bytes(b"new executable")
    destination = tmp_path / "portable" / "SearchDeck"
    destination.mkdir(parents=True)
    settings = b'{"personal_catalog": true}'
    (destination / "settings.json").write_bytes(settings)
    (destination / "SearchDeck.exe").write_bytes(b"old executable")
    copy_release(source, destination)
    assert (destination / "settings.json").read_bytes() == settings
    assert (destination / "SearchDeck.exe").read_bytes() == b"new executable"
