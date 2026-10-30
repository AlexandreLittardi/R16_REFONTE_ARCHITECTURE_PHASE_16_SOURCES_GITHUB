"""Explicit UI-neutral routing-area command.

A drag is computed from the gesture's original polygon. Intermediate invalid
shapes are rejected, preventing half-applied modifications and lost metadata.
"""
from dataclasses import dataclass
from domain.routing_geometry import update_routing_area
from application.events import RoutingAreaChanged


@dataclass(frozen=True)
class MoveRoutingArea:
    index: int
    start_points: tuple
    dx_px: float
    dy_px: float
    vertex: int | None = None

    def execute(self, areas):
        updated = update_routing_area(areas, self.index, self.start_points,
                                      self.dx_px, self.dy_px, self.vertex)
        if updated is None or updated == areas:
            return None, ()
        return updated, (RoutingAreaChanged(self.index),)
