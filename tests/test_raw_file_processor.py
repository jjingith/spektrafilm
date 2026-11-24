from types import SimpleNamespace

import numpy as np
import pytest

from spektrafilm.utils import raw_file_processor


def _stub_raw_reader(monkeypatch, raw_image: np.ndarray) -> None:
    class Reader:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def postprocess(self, **_kwargs):
            return raw_image

    monkeypatch.setattr(
        raw_file_processor,
        'rawpy',
        SimpleNamespace(
            imread=lambda path: Reader(),
            ColorSpace=SimpleNamespace(ACES='ACES'),
        ),
    )


def _stub_exif(monkeypatch, **overrides) -> None:
    values = {
        'make': 'Canon',
        'model': 'Canon EOS 5D Mark IV',
        'lens_make': 'Canon',
        'lens_model': 'Canon EF 50mm f/1.8 STM',
        'focal_length': 50.0,
        'f_number': 2.8,
    }
    values.update(overrides)
    exif_metadata = raw_file_processor.ExifData(**values)
    monkeypatch.setattr(raw_file_processor, '_read_exif_metadata', lambda path: exif_metadata)


def test_process_raw_file_daylight_uses_linear_output_and_colour_conversion(monkeypatch):
    """Daylight WB uses linear 16-bit ACES output, no rawpy WB knobs, and the
    ACES->sRGB conversion is the same linear matrix colour-science would use.

    The conversion is applied via a precomputed matrix (fast path); this test
    verifies the observable result against colour's own RGB_to_RGB rather than
    spying on internal call arguments.
    """
    raw_image = np.full((2, 2, 3), 16384, dtype=np.uint16)
    captured = {}

    class Reader:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def postprocess(self, **kwargs):
            captured['postprocess'] = kwargs
            return raw_image

    def imread(path):
        captured['path'] = path
        return Reader()

    monkeypatch.setattr(
        raw_file_processor,
        'rawpy',
        SimpleNamespace(
            imread=imread,
            ColorSpace=SimpleNamespace(ACES='ACES'),
        ),
    )

    result = raw_file_processor.load_and_process_raw_file(
        'example.nef',
        white_balance='daylight',
        output_colorspace='sRGB',
        output_cctf_encoding=False,
    )

    expected_linear = raw_image.astype(np.float32) / 65535.0
    expected = np.asarray(raw_file_processor.colour.RGB_to_RGB(
        expected_linear,
        input_colourspace=raw_file_processor.colour.RGB_COLOURSPACES['ACES2065-1'],
        output_colourspace=raw_file_processor.colour.RGB_COLOURSPACES['sRGB'],
        apply_cctf_decoding=False,
        apply_cctf_encoding=False,
    ), dtype=np.float32)
    np.testing.assert_allclose(result, expected, atol=1e-6)
    assert captured['path'] == 'example.nef'
    assert captured['postprocess']['output_color'] == 'ACES'
    assert captured['postprocess']['output_bps'] == 16
    assert captured['postprocess']['no_auto_bright'] is True
    assert captured['postprocess']['gamma'] == (1, 1)
    assert 'user_wb' not in captured['postprocess']
    assert 'use_camera_wb' not in captured['postprocess']


def test_process_raw_file_as_shot_uses_camera_white_balance(monkeypatch):
    raw_image = np.full((1, 1, 3), 32768, dtype=np.uint16)
    captured = {}

    class Reader:
        daylight_whitebalance = [2.0, 1.0, 1.5, 1.0]
        rgb_xyz_matrix = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0],
            ],
            dtype=np.float64,
        )

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def postprocess(self, **kwargs):
            captured['postprocess'] = kwargs
            return raw_image

    monkeypatch.setattr(
        raw_file_processor,
        'rawpy',
        SimpleNamespace(
            imread=lambda path: Reader(),
            ColorSpace=SimpleNamespace(ACES='ACES'),
        ),
    )

    result = raw_file_processor.load_and_process_raw_file('example.nef', white_balance='as_shot')

    np.testing.assert_allclose(result, raw_image.astype(np.float32) / 65535.0)
    assert captured['postprocess']['use_camera_wb'] is True
    assert 'user_wb' not in captured['postprocess']


@pytest.mark.parametrize(
    ('white_balance', 'temperature', 'tint', 'expect_adaptation', 'expected_tint'),
    [
        ('tungsten', None, None, True, 1.0),
        ('custom', 3200.0, 0.85, True, 0.85),
        ('custom', 6504.0, 1.0, False, 1.0),
    ],
    ids=['tungsten', 'custom-tungsten', 'custom-daylight'],
)
def test_process_raw_file_temperature_white_balance_variants(
    monkeypatch, white_balance, temperature, tint, expect_adaptation, expected_tint,
):
    """White-balance contract: temperature modes adapt in linear ACES, tint
    scales green, 6504 K is the daylight identity, and rawpy's own WB knobs
    are never used (adaptation is done in colour-science space).
    """
    raw_image = np.full((2, 2, 3), 16384, dtype=np.uint16)
    postprocess_calls: list[dict[str, object]] = []
    matrix_calls: list[tuple[np.ndarray, np.ndarray]] = []

    class Reader:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def postprocess(self, **kwargs):
            postprocess_calls.append(kwargs)
            return raw_image

    monkeypatch.setattr(
        raw_file_processor,
        'rawpy',
        SimpleNamespace(
            imread=lambda path: Reader(),
            ColorSpace=SimpleNamespace(ACES='ACES'),
        ),
    )

    real_matrix = raw_file_processor._wb_adaptation_matrix

    def spy_matrix(source, target):
        matrix_calls.append((np.asarray(source).copy(), np.asarray(target).copy()))
        return real_matrix(source, target)

    monkeypatch.setattr(raw_file_processor, '_wb_adaptation_matrix', spy_matrix)

    result = raw_file_processor.load_and_process_raw_file(
        'example.nef',
        white_balance=white_balance,
        temperature=temperature,
        tint=tint,
    )

    expected_linear = raw_image.astype(np.float32) / 65535.0
    expected_tint_scale = np.array([1.0, expected_tint, 1.0], dtype=np.float32)
    assert result.dtype == np.float32
    assert all('user_wb' not in call for call in postprocess_calls)
    assert all('use_camera_wb' not in call for call in postprocess_calls)

    if not expect_adaptation:
        # 6504 K == daylight reference -> no chromatic adaptation matrix call.
        assert matrix_calls == []
        np.testing.assert_allclose(result, expected_linear * expected_tint_scale)
    else:
        assert len(matrix_calls) == 1
        source, target = matrix_calls[0]
        # Both whites are normalised to Y == 1. Target is the 6504 K daylight
        # reference; source is the requested (warmer) scene temperature.
        np.testing.assert_allclose(target, raw_file_processor._whitepoint_xyz_from_temperature(6504.0) / raw_file_processor._whitepoint_xyz_from_temperature(6504.0)[1])
        assert source[1] == pytest.approx(1.0)
        if white_balance == 'tungsten':
            expected_source_wb = raw_file_processor._whitepoint_xyz_from_temperature(raw_file_processor._TUNGSTEN_TEMPERATURE)
        else:
            expected_source_wb = raw_file_processor._whitepoint_xyz_from_temperature(3200.0)
        np.testing.assert_allclose(source, expected_source_wb / expected_source_wb[1])
        # Adaptation actually changed the pixels (not an identity matrix).
        assert not np.allclose(result, expected_linear * expected_tint_scale)


@pytest.mark.parametrize(
    ('lens_model', 'correction_summary', 'expect_database_call', 'expected_lens_info'),
    [
        ('', None, False, {}),
        ('Canon EF 50mm f/1.8 STM', '', True, {}),
        (
            'Canon EF 50mm f/1.8 STM',
            'Canon EF 50mm f/1.8 STM @ 50.0mm f/2.8',
            True,
            {'summary': 'Canon EF 50mm f/1.8 STM @ 50.0mm f/2.8'},
        ),
    ],
    ids=['missing-lens-model', 'no-correction-summary', 'correction-summary'],
)
def test_process_raw_file_lens_info_reporting(
    monkeypatch,
    lens_model: str,
    correction_summary: str | None,
    expect_database_call: bool,
    expected_lens_info: dict[str, str],
):
    raw_image = np.full((1, 1, 3), 16384, dtype=np.uint16)
    lens_info_out: dict[str, str] = {}

    _stub_raw_reader(monkeypatch, raw_image)
    _stub_exif(monkeypatch, lens_model=lens_model)

    if not expect_database_call:
        monkeypatch.setattr(
            raw_file_processor.lensfunpy,
            'Database',
            lambda: (_ for _ in ()).throw(AssertionError('lensfun database should not be queried without a lens model')),
        )
    else:
        monkeypatch.setattr(
            raw_file_processor,
            '_apply_lens_correction',
            lambda rgb, exif_metadata: (rgb, '' if correction_summary is None else correction_summary),
        )

    result = raw_file_processor.load_and_process_raw_file(
        'example.nef',
        lens_correction=True,
        lens_info_out=lens_info_out,
    )

    np.testing.assert_allclose(result, raw_image.astype(np.float32) / 65535.0)
    assert lens_info_out == expected_lens_info
