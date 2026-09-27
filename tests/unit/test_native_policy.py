from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def policy():
    spec = importlib.util.spec_from_file_location(
        "native_policy", Path(__file__).resolve().parents[2] / "Build_Tools" / "native_policy.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_binary_outside_trusted_roots_fails(tmp_path):
    root = tmp_path / "trusted"
    root.mkdir()
    foreign = tmp_path / "foreign.dll"
    foreign.write_bytes(b"fixture")
    with pytest.raises(RuntimeError, match="Untrusted native binary"):
        policy().validate_origin(str(foreign), (root,))


def test_environment_does_not_inherit_toolchain_path(monkeypatch):
    monkeypatch.setenv("PATH", "C:/foreign-toolchain")
    assert "foreign-toolchain" not in policy().build_environment()["PATH"]


def test_foreign_binary_is_rejected_before_runtime_replacement(tmp_path):
    foreign = tmp_path / "vcruntime140.dll"
    foreign.write_bytes(b"foreign")
    with pytest.raises(RuntimeError, match="Untrusted native binary"):
        policy().enforce_binary_policy([("vcruntime140.dll", str(foreign), "BINARY")])
