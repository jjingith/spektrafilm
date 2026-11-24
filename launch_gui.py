"""Launch spektrafilm GUI from the workspace src (with optimizations).

Run:  python launch_gui.py   (or double-click 启动GUI-测试版.bat)

The only thing this launcher must do is force ``PYTHONPATH=<repo>/src`` so the
optimized workspace code is imported instead of the venv's stale copy install.
Font-path repair for CJK directories now lives in ``spektrafilm_gui.font_fix``
and runs inside ``create_app()``, so it also works in the frozen (PyInstaller)
build where this launcher is not used.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / "测试版本" / "spektrafilm" / "Scripts" / "python.exe"
SRC = ROOT / "src"


def main() -> int:
    if not VENV_PY.is_file():
        print(f"[launch_gui] venv python not found: {VENV_PY}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")

    print("[launch_gui] python :", VENV_PY)
    print("[launch_gui] source :", SRC)

    bootstrap = (
        "from spektrafilm.utils import raw_file_processor as m; "
        "assert hasattr(m, '_wb_adaptation_matrix'), 'NOT loading optimized source!'; "
        "from spektrafilm_gui.app import main; main()"
    )
    return subprocess.call([str(VENV_PY), "-c", bootstrap], env=env)


if __name__ == "__main__":
    raise SystemExit(main())
