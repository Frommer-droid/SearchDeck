# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo,
    VarStruct, VSVersionInfo,
)
project_root = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(project_root / 'Build_Tools'))
from native_policy import build_environment, enforce_binary_policy, qt_runtime_binaries
os.environ['PATH'] = build_environment()['PATH']
APP_NAME = 'SearchDeck'
smoke = os.environ.get('SEARCHDECK_SMOKE') == '1'
name = 'SearchDeckSmoke' if smoke else APP_NAME
script = project_root / 'Build_Tools' / 'frozen_smoke.py' if smoke else project_root / 'main.py'
version = (project_root / 'VERSION').read_text(encoding='utf-8').strip()
parts = tuple(int(part) for part in version.split('.')) + (0,)
resource = VSVersionInfo(
    ffi=FixedFileInfo(filevers=parts, prodvers=parts, mask=0x3f, flags=0,
                     OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
    kids=[StringFileInfo([StringTable('040904B0', [
        StringStruct('FileDescription', APP_NAME), StringStruct('ProductName', APP_NAME),
        StringStruct('FileVersion', version), StringStruct('ProductVersion', version),
        StringStruct('OriginalFilename', name + '.exe'),
    ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])],
)
a = Analysis(
    [str(script)], pathex=[str(project_root)], binaries=qt_runtime_binaries(),
    datas=[(str(project_root / 'VERSION'), '.'), (str(project_root / 'logo.ico'), '.'),
           (str(project_root / 'assets'), 'assets')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
a.binaries = enforce_binary_policy(a.binaries)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=name, debug=False,
          strip=False, upx=False, console=smoke, icon=str(project_root / 'logo.ico'),
          version=resource, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=name)
