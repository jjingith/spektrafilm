"""fast_color must stay bit-identical to colour-science's linear transforms.

These tests pin the contract that makes the GPU/CPU acceleration in the
scanning and gamut-compression stages safe: RGB<->XYZ with CCTF off is a pure
3x3 matrix, and the combined matrix reproduces colour-science's default
CAT02 chromatic adaptation to floating-point noise.
"""
from __future__ import annotations

import colour
import numpy as np
import pytest

from spektrafilm.utils import fast_color


@pytest.mark.parametrize("space", ["sRGB", "ACEScg", "ProPhoto RGB", "ITU-R BT.2020"])
@pytest.mark.parametrize("illuminant_kind", ["none", "white", "custom"])
def test_rgb_to_xyz_matches_colour(space, illuminant_kind):
    cs = colour.RGB_COLOURSPACES[space]
    if illuminant_kind == "none":
        illuminant = None
    elif illuminant_kind == "white":
        illuminant = np.asarray(cs.whitepoint)
    else:
        # Deliberately different from the space whitepoint -> CAT02 is active.
        illuminant = np.array([0.30, 0.40])

    rng = np.random.default_rng(11)
    rgb = rng.random((512, 3)) * 0.8 + 0.05

    expected = np.asarray(colour.RGB_to_XYZ(
        rgb,
        colourspace=cs,
        illuminant=illuminant,
        apply_cctf_decoding=False,
    ))
    actual = fast_color.rgb_to_xyz(rgb, cs, illuminant=illuminant)
    np.testing.assert_allclose(actual, expected, rtol=0, atol=2e-15)


@pytest.mark.parametrize("space", ["sRGB", "ACEScg", "ProPhoto RGB", "ITU-R BT.2020"])
@pytest.mark.parametrize("illuminant_kind", ["none", "white", "custom"])
def test_xyz_to_rgb_matches_colour(space, illuminant_kind):
    cs = colour.RGB_COLOURSPACES[space]
    if illuminant_kind == "none":
        illuminant = None
    elif illuminant_kind == "white":
        illuminant = np.asarray(cs.whitepoint)
    else:
        illuminant = np.array([0.25, 0.55])

    rng = np.random.default_rng(13)
    xyz = rng.random((512, 3)) * 0.8 + 0.05

    expected = np.asarray(colour.XYZ_to_RGB(
        xyz,
        colourspace=cs,
        illuminant=illuminant,
        apply_cctf_encoding=False,
    ))
    actual = fast_color.xyz_to_rgb(xyz, cs, illuminant=illuminant)
    np.testing.assert_allclose(actual, expected, rtol=0, atol=2e-15)


def test_matrix_is_reused_from_cache():
    cs = colour.RGB_COLOURSPACES["sRGB"]
    m1 = fast_color._rgb_to_xyz_matrix(cs, None)
    m2 = fast_color._rgb_to_xyz_matrix(cs, None)
    assert m1 is m2
