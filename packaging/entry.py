"""Frozen-app entry point for the portable (green) build.

Runs the GUI and, on any unhandled exception, writes a traceback next to the
executable so a windowed build (no console) is still diagnosable.
"""
from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime


def _log_path() -> str:
    base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
    return os.path.join(base, 'spektrafilm_crash.log')


def main() -> int:
    try:
        from spektrafilm_gui.app import main as app_main
        app_main()
        return 0
    except BaseException:
        try:
            with open(_log_path(), 'a', encoding='utf-8') as fh:
                fh.write(f'\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n')
                traceback.print_exc(file=fh)
        except OSError:
            pass
        raise


if __name__ == '__main__':
    raise SystemExit(main())
