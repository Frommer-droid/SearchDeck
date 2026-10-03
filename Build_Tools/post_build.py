"""Подготовка поставки после обязательных native/frozen gates."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

APP_NAME = "SearchDeck"
FILES_TO_COPY = [
    ("logo.ico", "logo.ico"), ("VERSION", "VERSION"), ("assets", "assets"),
    ("LICENSE", "LICENSE"), ("THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"),
    ("SOURCE_CODE_ACCESS.md", "SOURCE_CODE_ACCESS.md"), ("README.md", "README.md"),
    ("README.en.md", "README.en.md"), ("RELEASE_NOTES.md", "RELEASE_NOTES.md"),
    ("settings.example.json", "settings.example.json"), ("DEVELOPER.md", "DEVELOPER.md"),
]


def main() -> None:
    tools = Path(__file__).resolve().parent
    root = tools.parent
    report = json.loads((tools / "verification" / "native-verification.json").read_text())
    if report["frozen_smoke"]["exit_code"] or report["SearchDeck"]["foreign_origins"]:
        raise RuntimeError("Native/frozen gates did not pass")
    source = tools / "dist" / APP_NAME
    target = root / APP_NAME
    if target.exists():
        raise RuntimeError("Old release directory must be removed before build")
    shutil.move(str(source), str(target))
    for source_name, target_name in FILES_TO_COPY:
        source_file = root / source_name
        if source_file.is_dir():
            shutil.copytree(source_file, target / target_name, dirs_exist_ok=True)
        else:
            shutil.copy2(source_file, target / target_name)
    # Qt licence texts shipped by the installed binding, without changing them.
    shutil.copytree(root / "assets" / "licenses", target / "licenses", dirs_exist_ok=True)
    manifest = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(target.rglob("*")) if p.is_file() and p.name != "settings.json"}
    (target / "SHA256SUMS.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Automatic application launch after build is disabled.")
    print(f"Verified release prepared: {target}")


if __name__ == "__main__":
    main()
