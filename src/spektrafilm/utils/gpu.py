from __future__ import annotations

import os
from typing import Any

import numpy as np

_CUPY: Any | None = None
_CUPY_CHECKED = False


def gpu_requested() -> bool:
    value = os.environ.get("SPEKTRAFILM_GPU", "").strip().lower()
    return value not in {"", "0", "false", "off", "no", "cpu"}


def _load_cupy() -> Any | None:
    global _CUPY, _CUPY_CHECKED

    if _CUPY_CHECKED:
        return _CUPY
    _CUPY_CHECKED = True

    if not gpu_requested():
        return None

    if os.name == "nt":
        cuda_path = os.environ.get("CUDA_PATH")
        if cuda_path:
            bin_path = os.path.join(cuda_path, "bin")
            if os.path.isdir(bin_path):
                try:
                    os.add_dll_directory(bin_path)
                except (AttributeError, OSError):
                    pass

    try:
        import cupy  # type: ignore[import-not-found]
    except Exception:
        return None

    try:
        cupy.cuda.runtime.getDeviceCount()
    except Exception:
        return None

    _CUPY = cupy
    return _CUPY


def gpu_available() -> bool:
    return _load_cupy() is not None


def _chunk_rows(cp: Any, width: int, height: int, wavelengths: int, itemsize: int) -> int:
    try:
        free_bytes, _total = cp.cuda.runtime.memGetInfo()
    except Exception:
        free_bytes = 2 * 1024**3
    budget = min(int(free_bytes * 0.35), 1536 * 1024**2)
    bytes_per_row = max(1, width * wavelengths * itemsize * 3)
    rows = int(budget // bytes_per_row)
    return max(16, min(height, rows, 512))


def project_log(
    cmy: np.ndarray,
    channel_density: np.ndarray,
    base_density: np.ndarray | None,
    illuminant: np.ndarray,
    matrix: np.ndarray,
    *,
    scale: float | np.ndarray = 1.0,
    offset: float | np.ndarray | None = None,
    min_pixels: int = 65536,
) -> np.ndarray | None:
    """GPU implementation of the per-pixel spectral density integral.

    Returns ``log10(max(light @ matrix * scale + offset, 0) + 1e-10)`` as a
    float64 NumPy array, or ``None`` when the GPU path is unavailable or the
    image is too small to benefit from it.
    """
    cp = _load_cupy()
    if cp is None:
        return None

    cmy = np.asarray(cmy)
    if cmy.ndim != 3 or cmy.shape[2] != 3:
        return None
    height, width, _channels = cmy.shape
    if height * width < min_pixels:
        return None

    channel_density = np.asarray(channel_density, dtype=np.float64)
    illuminant = np.asarray(illuminant, dtype=np.float64)
    matrix = np.asarray(matrix, dtype=np.float64)
    wavelengths = channel_density.shape[0]
    if base_density is not None:
        base_density = np.asarray(base_density, dtype=np.float64)

    use_float64 = height * width <= 1_000_000
    dtype = cp.float64 if use_float64 else cp.float32
    itemsize = 8 if use_float64 else 4

    cd_gpu = cp.asarray(channel_density, dtype=dtype)
    illum_gpu = cp.asarray(illuminant, dtype=dtype)
    matrix_gpu = cp.asarray(matrix, dtype=dtype)
    base_gpu = cp.asarray(base_density, dtype=dtype) if base_density is not None else None
    scale_gpu = cp.asarray(scale, dtype=dtype)
    offset_gpu = cp.asarray(offset, dtype=dtype) if offset is not None else None

    output = np.empty((height, width, 3), dtype=np.float64)
    rows = _chunk_rows(cp, width, height, wavelengths, itemsize)

    for start in range(0, height, rows):
        stop = min(height, start + rows)
        chunk = cp.asarray(cmy[start:stop], dtype=dtype)
        density_spectral = cp.einsum("ijk,lk->ijl", chunk, cd_gpu)
        if base_gpu is not None:
            density_spectral += base_gpu
        light = cp.power(10.0, -density_spectral) * illum_gpu
        light = cp.nan_to_num(light, nan=0.0)
        projected = cp.einsum("ijl,lm->ijm", light, matrix_gpu)
        projected *= scale_gpu
        if offset_gpu is not None:
            projected += offset_gpu
        result = cp.log10(cp.fmax(projected, 0.0) + 1e-10)
        output[start:stop] = cp.asnumpy(result).astype(np.float64)
        del chunk, density_spectral, light, projected, result

    return output
