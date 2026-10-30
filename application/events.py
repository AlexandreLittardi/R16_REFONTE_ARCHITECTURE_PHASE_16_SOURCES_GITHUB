"""Synchronous, dependency-free project events (not Tkinter bindings)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RoutingAreaChanged:
    index: int


@dataclass(frozen=True)
class ElectricalTopologyChanged:
    """An explicit, committed edit to strings, MPPTs or inverter blocks."""
    source: str


class EventBus:
    def __init__(self):
        self._listeners = []

    def subscribe(self, listener):
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def emit(self, event):
        for listener in tuple(self._listeners):
            listener(event)
