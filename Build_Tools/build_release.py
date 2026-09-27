"""CLI: clean build, проверка TOC/MSVC, frozen smoke, затем post-build."""
from __future__ import annotations

import ast
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from native_policy import (
    PROJECT_ROOT, QT_ROOT, RUNTIME_NAMES, build_environment, validate_origin, file_version,
)


def remove_work_directory(path: Path) -> None:
    resolved = path.resolve()
    allowed = {PROJECT_ROOT / "SearchDeck", PROJECT_ROOT / "Build_Tools" / "build",
               PROJECT_ROOT / "Build_Tools" / "dist"}
    if resolved not in allowed or not resolved.is_relative_to(PROJECT_ROOT):
        raise RuntimeError(f"Unsafe cleanup target: {resolved}")
    if resolved.exists():
        if resolved.is_symlink() or resolved.is_junction():
            raise RuntimeError(f"Refusing linked cleanup target: {resolved}")
        shutil.rmtree(resolved)


def verify_collect(path: Path, bundle: Path) -> dict:
    payload = ast.literal_eval(path.read_text(encoding="utf-8"))
    entries = payload[-1]
    native = [entry for entry in entries if entry[2] in ("BINARY", "EXTENSION", "EXECUTABLE")]
    for _destination, source, _kind in native:
        validate_origin(source)
    versions = {}
    for name in RUNTIME_NAMES:
        supplied = bundle / "_internal" / name
        if hashlib.sha256(supplied.read_bytes()).digest() != hashlib.sha256((QT_ROOT / name).read_bytes()).digest():
            raise RuntimeError(f"MSVC runtime does not match Qt: {name}")
        versions[name] = file_version(supplied)
    if len({tuple(version) for version in versions.values()}) != 1:
        raise RuntimeError("Mixed MSVC runtime versions")
    return {"foreign_origins": [], "native_count": len(native), "runtime_versions": versions}


def main() -> int:
    expected = PROJECT_ROOT / ".venv"
    if Path(sys.prefix).resolve() != expected.resolve():
        raise RuntimeError("Build must run from the project .venv")
    tools = PROJECT_ROOT / "Build_Tools"
    reports = tools / "verification"
    reports.mkdir(exist_ok=True)
    # Runtime state remains in the repository, backed up before cleanup.
    state = PROJECT_ROOT / "SearchDeck" / "settings.json"
    if state.exists():
        shutil.copy2(state, reports / "previous-build-settings.json")
    for path in (PROJECT_ROOT / "SearchDeck", tools / "build", tools / "dist"):
        remove_work_directory(path)
    env = build_environment()
    results = {}
    for smoke in (False, True):
        name = "SearchDeckSmoke" if smoke else "SearchDeck"
        current_env = {**env, "SEARCHDECK_SMOKE": "1" if smoke else "0"}
        completed = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm",
             "--workpath", str(tools / "build" / name), "--distpath", str(tools / "dist"),
             str(tools / "SearchDeck.spec")],
            cwd=PROJECT_ROOT, env=current_env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=600,
        )
        (reports / f"{name}-build.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
        if completed.returncode:
            raise RuntimeError(f"{name} build failed; see {reports / (name + '-build.log')}")
        toc = tools / "build" / name / "SearchDeck" / "COLLECT-00.toc"
        results[name] = verify_collect(toc, tools / "dist" / name)
        shutil.copy2(toc, reports / f"{name}-COLLECT-00.toc")
        print(f"{name}: native origin and MSVC gates passed", flush=True)
    smoke = subprocess.run(
        [str(tools / "dist" / "SearchDeckSmoke" / "SearchDeckSmoke.exe")],
        cwd=tools / "dist" / "SearchDeckSmoke", env={**env, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    results["frozen_smoke"] = {"exit_code": smoke.returncode, "stdout": smoke.stdout, "stderr": smoke.stderr}
    (reports / "native-verification.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    forbidden = ("Traceback", "ImportError", "DLL load failed", "PyInstallerImportError", ":ERROR]")
    if smoke.returncode or any(marker in smoke.stdout + smoke.stderr for marker in forbidden):
        raise RuntimeError("Frozen smoke failed; see native-verification.json")
    smoke_result = json.loads(smoke.stdout.strip())
    if smoke_result.get("status") != "ok" or not smoke_result.get("frozen"):
        raise RuntimeError("Frozen smoke did not complete successfully")
    # Post-build cannot run until the persisted gate report exists.
    subprocess.run([sys.executable, str(tools / "post_build.py")], cwd=PROJECT_ROOT, env=env, check=True)
    print(smoke.stdout.strip(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
