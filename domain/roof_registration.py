"""Roof-photo registration calculations independent of Tkinter and canvas zoom.

Survey geometry is stored in original image-space pixels. Camera zoom never
changes it. Photograph offsets are also original-image pixel coordinates.
"""
import math


def shifted_photo_offset(offset, dx, dy, zoom):
    """Apply a canvas-screen displacement to the original-image offset."""
    if not all(math.isfinite(float(v)) for v in (*offset, dx, dy, zoom)) or zoom <= 0:
        raise ValueError('Photo displacement and zoom must be finite; zoom must be positive.')
    return (float(offset[0]) + dx / zoom, float(offset[1]) + dy / zoom)


def calibrated_scale(p1, p2, reference_mm):
    """Return pixels/mm, rejecting short and non-finite reference geometry."""
    try:
        length = float(reference_mm)
        dist = math.dist(p1, p2)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('Invalid calibration coordinates or length.') from exc
    if not math.isfinite(length) or length <= 0:
        raise ValueError('Reference length must be positive and finite.')
    if not math.isfinite(dist) or dist <= 5:
        raise ValueError('Reference segment is too short.')
    result = dist / length
    if not math.isfinite(result) or result <= 0:
        raise ValueError('Invalid calibration scale.')
    return result


def replacement_scale_factor(existing_px_per_mm, new_px_per_mm):
    """Scale a new photograph to an existing survey without moving zones."""
    if not all(math.isfinite(float(v)) and v > 0 for v in (existing_px_per_mm, new_px_per_mm)):
        raise ValueError('Calibration scales must be finite and positive.')
    result = existing_px_per_mm / new_px_per_mm
    if not math.isfinite(result) or result <= 0:
        raise ValueError('Invalid image rescaling factor.')
    return result
