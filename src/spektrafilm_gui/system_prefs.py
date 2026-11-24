"""System preferences (language / GPU) persisted via QSettings.

These are application-wide preferences rather than per-document GUI state, so
they live in QSettings (like dialog directories) instead of the JSON GUI state.
Changes take effect after restarting the app: on startup ``apply_to_environment``
reads them and sets the environment variables consumed by i18n / gpu modules.
"""
from __future__ import annotations

import os
from enum import Enum

from qtpy import QtCore

QSettings = getattr(QtCore, 'QSettings')

_SETTINGS = ('spektrafilm', 'spektrafilm')
_KEY_LANG = 'system/language'
_KEY_GPU = 'system/gpu'


class AppLanguage(str, Enum):
    DEFAULT = 'default'   # follow environment / auto-detect (zh_CN by default)
    ZH_CN = 'zh_CN'
    EN = 'en'


class GpuMode(str, Enum):
    AUTO = 'auto'
    ON = 'on'
    OFF = 'off'


def _settings() -> QSettings:
    return QSettings(*_SETTINGS)


def read_language() -> AppLanguage:
    raw = str(_settings().value(_KEY_LANG, AppLanguage.DEFAULT.value))
    try:
        return AppLanguage(raw)
    except ValueError:
        return AppLanguage.DEFAULT


def read_gpu() -> GpuMode:
    raw = str(_settings().value(_KEY_GPU, GpuMode.AUTO.value))
    try:
        return GpuMode(raw)
    except ValueError:
        return GpuMode.AUTO


def write_language(value: AppLanguage) -> None:
    _settings().setValue(_KEY_LANG, value.value)


def write_gpu(value: GpuMode) -> None:
    _settings().setValue(_KEY_GPU, value.value)


def apply_to_environment() -> None:
    """Push stored preferences into env vars before GUI modules initialise."""
    lang = read_language()
    if lang is not AppLanguage.DEFAULT:
        os.environ['SPEKTRAFILM_LANG'] = lang.value

    gpu = read_gpu()
    if gpu is GpuMode.ON:
        os.environ['SPEKTRAFILM_GPU'] = '1'
    elif gpu is GpuMode.OFF:
        os.environ['SPEKTRAFILM_GPU'] = '0'
    else:
        # Auto: let gpu.py detect CuPy/CUDA on its own; clear a stale override.
        os.environ.pop('SPEKTRAFILM_GPU', None)


__all__ = [
    'AppLanguage', 'GpuMode', 'read_language', 'read_gpu',
    'write_language', 'write_gpu', 'apply_to_environment',
]
