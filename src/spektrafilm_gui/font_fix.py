"""Work around vispy/freetype failing to open fonts under non-ASCII paths.

On Windows, freetype-py uses ANSI APIs, so a TTF whose path contains CJK
characters (e.g. an app installed under 中文目录) fails with
``FT_Exception: cannot open resource`` at napari viewer construction time.
This copies vispy's bundled fonts to an ASCII temp directory and redirects
``_get_vispy_font_filename`` there. Safe to call multiple times; also works
from a PyInstaller bundle (fonts are located via importlib.resources / sys._MEIPASS).
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

_FONT_NAMES = (
    'OpenSans-Regular', 'OpenSans-Bold', 'OpenSans-Italic', 'OpenSans-BoldItalic',
)
_applied = False


def _bundled_font_dir() -> Path | None:
    candidates: list[Path] = []
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidates.append(Path(meipass) / 'spektrafilm_gui' / 'assets' / 'fonts')
        candidates.append(Path(meipass) / 'vispy' / 'util' / 'fonts' / 'data')
    try:
        import vispy.util.fonts as vfonts  # type: ignore
        candidates.append(Path(vfonts.__file__).resolve().parent / 'data')
    except Exception:
        pass
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _is_ascii_path(path: Path) -> bool:
    try:
        str(path).encode('ascii')
        return True
    except UnicodeEncodeError:
        return False


def _ascii_font_dir() -> Path | None:
    """Return a writable ASCII-only directory for the font copies."""
    candidates = [Path(tempfile.gettempdir()) / 'spektrafilm_fonts']
    candidates.append(Path('C:/ProgramData/spektrafilm/fonts'))
    candidates.append(Path('C:/Windows/Temp/spektrafilm_fonts'))
    for candidate in candidates:
        if not _is_ascii_path(candidate):
            continue
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / '.write_test'
            probe.write_bytes(b'x')
            probe.unlink()
            return candidate
        except OSError:
            continue
    return None


def _font_readable(path: Path) -> bool:
    """True if freetype can open the font (catches truncated/corrupt copies)."""
    if not path.is_file() or path.stat().st_size == 0:
        return False
    try:
        from freetype import Face  # type: ignore
        Face(str(path))
        return True
    except Exception:
        return False


def apply_font_path_fix() -> None:
    global _applied
    if _applied:
        return
    _applied = True

    source = _bundled_font_dir()
    if source is None:
        return

    # Prefer an ASCII-only base. tempfile.gettempdir() honours TMP/TEMP and
    # returned a non-standard "D:\\Temp\\2" on one machine, so resolve it and
    # fall back to a fixed ASCII location if the result is not usable.
    ascii_dir = _ascii_font_dir()
    if ascii_dir is None:
        return

    # A single unreadable/unwritable font must not abort the whole fix; patch
    # the lookup as long as at least one usable TTF landed on disk.
    copied_any = False
    for name in _FONT_NAMES:
        src = source / f'{name}.ttf'
        dst = ascii_dir / f'{name}.ttf'
        if not src.is_file():
            continue
        if _font_readable(dst):
            copied_any = True
            continue
        try:
            with open(src, 'rb') as fh:
                data = fh.read()
            if dst.exists():
                dst.unlink()
            dst.write_bytes(data)
            if _font_readable(dst):
                copied_any = True
        except OSError:
            continue

    if not copied_any:
        return

    def _patched(face, bold, italic):
        name = face + '-'
        name += 'Regular' if not bold and not italic else ''
        name += 'Bold' if bold else ''
        name += 'Italic' if italic else ''
        name += '.ttf'
        return os.path.join(str(ascii_dir), name)

    # freetype imports this symbol from _vispy_fonts into its own namespace;
    # patch both the definition site and the consumer to be safe.
    for module_name in ('vispy.util.fonts._vispy_fonts', 'vispy.util.fonts._freetype'):
        try:
            module = __import__(module_name, fromlist=['_get_vispy_font_filename'])
            if hasattr(module, '_get_vispy_font_filename'):
                setattr(module, '_get_vispy_font_filename', _patched)
        except Exception:
            continue
