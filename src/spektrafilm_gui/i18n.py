from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_LOCALE_DIR = Path(__file__).with_name("locale")


def _load_catalog(name: str) -> dict[str, str]:
    path = _LOCALE_DIR / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


_UI_CATALOG = _load_catalog("zh_CN.json")
_STATUS_CATALOG = _load_catalog("zh_CN_status.json")


def current_language() -> str:
    return os.environ.get("SPEKTRAFILM_LANG", "zh_CN").replace("-", "_").lower()


def is_chinese() -> bool:
    return current_language().startswith("zh")


def tr(text: str) -> str:
    if not isinstance(text, str) or not is_chinese():
        return text
    return _UI_CATALOG.get(text) or _STATUS_CATALOG.get(text) or text


def trf(template: str, **kwargs: Any) -> str:
    translated = tr(template)
    try:
        return translated.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return translated


def apply_widget_translations(root: Any) -> None:
    """Translate static widget text created before the language layer ran."""
    if not is_chinese():
        return

    from qtpy.QtWidgets import (
        QAbstractButton,
        QAction,
        QComboBox,
        QDockWidget,
        QGroupBox,
        QLabel,
        QTabBar,
        QWidget,
    )

    for widget in root.findChildren(QWidget):
        if isinstance(widget, QLabel):
            widget.setText(tr(widget.text()))
        elif isinstance(widget, QAbstractButton):
            widget.setText(tr(widget.text()))
        elif isinstance(widget, QGroupBox):
            widget.setTitle(tr(widget.title()))
        elif isinstance(widget, QDockWidget):
            widget.setWindowTitle(tr(widget.windowTitle()))
        elif isinstance(widget, QTabBar):
            for index in range(widget.count()):
                widget.setTabText(index, tr(widget.tabText(index)))
        elif isinstance(widget, QComboBox):
            # EnumEditor and ProfileEnumEditor manage their own display text.
            pass
        if widget.toolTip():
            widget.setToolTip(tr(widget.toolTip()))

    for action in root.findChildren(QAction):
        if action.text():
            action.setText(tr(action.text()))
        if action.toolTip():
            action.setToolTip(tr(action.toolTip()))
