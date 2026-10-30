"""Snapshot preparation without importing Tkinter or invoking the editor.

Large energy/shadow payloads are shared between adjacent history records when
unchanged. Historic R16 list/tuple and image/view formats are left intact.
"""
from domain.serialization import fingerprint, serial

LARGE_FIELDS = ('hourly_consumption_profile', 'hourly_weather_profile',
                'hourly_pv_kwh', 'self_consumption_summary', 'bess_summary',
                'two_bess_summary', 'shadow_simulation_results')


def make_history_payload(raw, previous=None):
    previous = previous or {}
    data = serial({k: v for k, v in raw.items() if k not in LARGE_FIELDS})
    for key in LARGE_FIELDS:
        if key in raw:
            data[key] = previous[key] if key in previous and raw[key] == previous[key] else serial(raw[key])
    for key in LARGE_FIELDS:
        if key in data and key in previous and data[key] == previous[key]:
            data[key] = previous[key]
    return data


def history_signature(data, view, image):
    """Undo/redo records represent edits, not viewport navigation.

    View settings are still retained as part of each record for restoration,
    but zooming/panning alone cannot append a new history entry.
    """
    return fingerprint((data, id(image)))
