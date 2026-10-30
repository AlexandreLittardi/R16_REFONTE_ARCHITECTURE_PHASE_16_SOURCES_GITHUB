"""A defensive, UI-independent representation of an R16 schema-v2 document.

This is an incremental boundary. It deliberately preserves unknown JSON fields,
legacy keys, and the existing on-disk schema. The Tkinter application remains
the live editor until each domain is migrated behind explicit commands.
"""
from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping

from domain.schema import SCHEMA_VERSION
from domain.serialization import fingerprint


@dataclass(frozen=True, init=False)
class ProjectDocument:
    _data: dict

    def __init__(self, data: Mapping):
        if not isinstance(data, Mapping):
            raise TypeError('ProjectDocument requires a mapping.')
        version = data.get('schema_version', 1)
        if not isinstance(version, int) or not 1 <= version <= SCHEMA_VERSION:
            raise ValueError('Unsupported project schema version.')
        # Copy on ingress and egress: no widget or service may mutate this state
        # by editing a nested list or dictionary obtained from it.
        object.__setattr__(self, '_data', deepcopy(dict(data)))

    def snapshot(self) -> dict:
        return deepcopy(self._data)

    @property
    def schema_version(self) -> int:
        return self._data.get('schema_version', 1)

    @property
    def signature(self) -> str:
        return fingerprint(self._data)

    def replace(self, **changes):
        updated = self.snapshot()
        updated.update(deepcopy(changes))
        return type(self)(updated)

    def get(self, key, default=None):
        return deepcopy(self._data.get(key, default))
