"""Pixel-centre mappings with explicit domains and unavailable geometry."""

import numpy as np

from .models import CoordinateTransform, Rectangle


class MappingError(ValueError):
    pass


def _inside(points, domain):
    return ((points[:, 0] >= domain.x_px - 1e-10)
            & (points[:, 0] < domain.x_px + domain.width_px)
            & (points[:, 1] >= domain.y_px - 1e-10)
            & (points[:, 1] < domain.y_px + domain.height_px))


def _project(matrix, points):
    homogeneous = np.column_stack((points, np.ones(len(points)))) @ matrix.T
    if np.any(np.abs(homogeneous[:, 2]) < 1e-12):
        raise MappingError('projective horizon intersects support')
    output = homogeneous[:, :2] / homogeneous[:, 2, None]
    if not np.isfinite(output).all():
        raise MappingError('non-finite mapping')
    output[np.abs(output) < 1e-10] = 0
    return output


def _prepare(mapping, inverse=False, tolerance_px=1e-3):
    if mapping.kind != 'homography':
        raise MappingError(f'unsupported mapping: {mapping.unsupported_reason}')
    if mapping.max_error_px > tolerance_px:
        raise MappingError('mapping error exceeds tolerance')
    if inverse and not mapping.inverse_available:
        raise MappingError('required inverse is unavailable')
    matrix = np.asarray(mapping.matrix, dtype=float)
    if abs(np.linalg.det(matrix)) < 1e-12 or np.linalg.cond(matrix) > 1e12:
        raise MappingError('singular or ill-conditioned mapping')
    source, target = mapping.source_domain, mapping.target_domain
    if inverse:
        matrix = np.linalg.inv(matrix)
        source, target = target, source
    x, y, w, h = source.x_px, source.y_px, source.width_px, source.height_px
    denominators = np.array([[x, y, 1], [x + w, y, 1], [x, y + h, 1],
                             [x + w, y + h, 1]]) @ matrix[2]
    if min(denominators) <= 0 <= max(denominators):
        raise MappingError('projective horizon intersects domain')
    return matrix, source, target


def map_point(mapping, point, *, inverse=False, tolerance_px=1e-3):
    matrix, source, target = _prepare(mapping, inverse, tolerance_px)
    points = np.asarray([point], dtype=float)
    if not np.isfinite(points).all() or not _inside(points, source).all():
        raise MappingError('point outside mapping source domain')
    output = _project(matrix, points)
    return tuple(output[0]) if _inside(output, target)[0] else None


def map_support(mapping, polygon, *, tolerance_px=1e-3):
    matrix, source, target = _prepare(mapping, tolerance_px=tolerance_px)
    points = np.asarray(polygon, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 3:
        raise MappingError('support requires at least three polygon vertices')
    if not np.isfinite(points).all() or not _inside(points, source).all():
        raise MappingError('support outside mapping source domain')
    output = _project(matrix, points)
    if _inside(output, target).all():
        return [tuple(point) for point in output]
    # Bounding boxes conservatively reject ambiguous intersections.
    if (output[:, 0].max() < target.x_px or output[:, 1].max() < target.y_px
            or output[:, 0].min() >= target.x_px + target.width_px
            or output[:, 1].min() >= target.y_px + target.height_px):
        return None
    raise MappingError('partially clipped repair support')


def map_mask(mapping, mask, *, tolerance_px=1e-3):
    matrix, source, target = _prepare(mapping, tolerance_px=tolerance_px)
    _prepare(mapping, inverse=True, tolerance_px=tolerance_px)
    if source.x_px or source.y_px or target.x_px or target.y_px:
        raise MappingError('raster domains must have zero origin')
    if any(value != int(value) for value in [source.width_px, source.height_px,
                                           target.width_px, target.height_px]):
        raise MappingError('raster dimensions must be integral')
    mask = np.asarray(mask, dtype=bool)
    if mask.shape != (int(source.height_px), int(source.width_px)):
        raise MappingError('mask shape does not match source domain')
    sy, sx = np.nonzero(mask)
    if len(sx):
        output = _project(matrix, np.column_stack((sx, sy)))
        valid = _inside(output, target)
        if not valid.any():
            return None
        if not valid.all():
            raise MappingError('partially clipped repair support')
    yy, xx = np.indices((int(target.height_px), int(target.width_px)))
    sample = _project(np.linalg.inv(matrix), np.column_stack((xx.ravel(), yy.ravel())))
    sample = np.floor(sample + .5).astype(int)
    valid = _inside(sample, source)
    result = np.zeros(xx.size, dtype=bool)
    result[valid] = mask[sample[valid, 1], sample[valid, 0]]
    return result.reshape(xx.shape)


def orientation_transform(width: int, height: int, orientation: int):
    matrices = {
        1: ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
        2: ((-1, 0, width - 1), (0, 1, 0), (0, 0, 1)),
        3: ((-1, 0, width - 1), (0, -1, height - 1), (0, 0, 1)),
        4: ((1, 0, 0), (0, -1, height - 1), (0, 0, 1)),
        5: ((0, 1, 0), (1, 0, 0), (0, 0, 1)),
        6: ((0, -1, height - 1), (1, 0, 0), (0, 0, 1)),
        7: ((0, -1, height - 1), (-1, 0, width - 1), (0, 0, 1)),
        8: ((0, 1, 0), (-1, 0, width - 1), (0, 0, 1)),
    }
    if orientation not in matrices or width <= 0 or height <= 0:
        raise MappingError('invalid dimensions or EXIF orientation')
    target_width, target_height = (height, width) if orientation >= 5 else (width, height)
    return CoordinateTransform(source_space='active_sensor', target_space='preview',
        matrix=matrices[orientation],
        source_domain=Rectangle(width_px=width, height_px=height),
        target_domain=Rectangle(width_px=target_width, height_px=target_height))
