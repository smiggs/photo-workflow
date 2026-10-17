import numpy as np
import pytest
from hypothesis import given, strategies as st

from photo_workflow.coordinates import MappingError, map_mask, map_point, map_support, orientation_transform
from photo_workflow.models import CoordinateTransform, Rectangle


def rectangle(width=7, height=5):
    return Rectangle(width_px=width, height_px=height)


def transform(**changes):
    values = dict(source_space='active_sensor', target_space='preview',
                  source_domain=rectangle(), target_domain=rectangle(),
                  matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    return CoordinateTransform(**(values | changes))


@given(orientation=st.integers(1, 8), width=st.integers(2, 101), height=st.integers(2, 101),
       u=st.floats(0, 1), v=st.floats(0, 1))
def test_all_exif_orientations_round_trip(orientation, width, height, u, v):
    mapping = orientation_transform(width, height, orientation)
    point = ((width - 1) * u, (height - 1) * v)
    projected = map_point(mapping, point)
    assert projected is not None
    assert np.allclose(map_point(mapping, projected, inverse=True), point, atol=1e-8)


@pytest.mark.parametrize('orientation,expected', [(1, (1, 2)), (2, (5, 2)), (3, (5, 2)),
    (4, (1, 2)), (5, (2, 1)), (6, (2, 1)), (7, (2, 5)), (8, (2, 5))])
def test_orientation_landmarks(orientation, expected):
    assert map_point(orientation_transform(7, 5, orientation), (1, 2)) == expected


def test_crop_does_not_clamp_or_invent_visibility():
    mapping = transform(matrix=((1, 0, -2), (0, 1, -1), (0, 0, 1)), target_domain=rectangle(3, 3))
    assert map_point(mapping, (0, 0)) is None
    assert map_point(mapping, (2, 1)) == (0, 0)
    with pytest.raises(MappingError, match='partially clipped'):
        map_support(mapping, [(1, 1), (3, 1), (3, 3), (1, 3)])
    assert map_support(mapping, [(0, 0), (1, 0), (1, .5), (0, .5)]) is None


def test_perspective_round_trip_and_non_circular_support():
    mapping = transform(matrix=((1, .1, 0), (0, 1, 0), (.01, 0, 1)))
    assert np.allclose(map_point(mapping, map_point(mapping, (3, 2)), inverse=True), (3, 2))
    result = map_support(mapping, [(2, 1), (4, 1), (4, 3), (2, 3)])
    assert not np.isclose(np.linalg.norm(np.subtract(result[0], result[1])),
                          np.linalg.norm(np.subtract(result[2], result[3])))


def test_mask_rotation_matches_array_rotation():
    mask = np.zeros((5, 7), dtype=bool)
    mask[1:3, 2:4] = True
    assert np.array_equal(map_mask(orientation_transform(7, 5, 6), mask), np.rot90(mask, -1))


def test_lens_mapping_and_unavailable_inverse_fail_closed():
    mapping = transform(kind='unsupported', matrix=None, inverse_available=False,
                        unsupported_reason='lens correction has not been calibrated')
    with pytest.raises(MappingError, match='unsupported'):
        map_point(mapping, (2, 2))
    with pytest.raises(MappingError, match='inverse'):
        map_point(transform(inverse_available=False), (2, 2), inverse=True)
    with pytest.raises(MappingError, match='singular'):
        map_point(transform(matrix=((0, 0, 0), (0, 0, 0), (0, 0, 1))), (2, 2))


def test_projective_horizon_and_bad_error_bounds_fail_closed():
    with pytest.raises(MappingError, match='horizon'):
        map_point(transform(matrix=((1, 0, 0), (0, 1, 0), (1, 0, -2))), (3, 2))
    with pytest.raises(MappingError, match='tolerance'):
        map_point(transform(max_error_px=1), (2, 2), tolerance_px=.1)
