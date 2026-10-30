"""Determine project consistency work without changing application state.

Paint/zoom must not be a way to commit domain state. These checks are cheap
and pure; the Tk adapter applies the plan at actual application boundaries.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ReconciliationPlan:
    panel_ids: bool
    shadow_result: bool
    wiring: bool

    @property
    def needed(self):
        return self.panel_ids or self.shadow_result or self.wiring


def plan_reconciliation(*, panel_coords, uid_coords, shadow_has_result,
                        shadow_source, current_shadow_source,
                        topology_signature, diagram_signature):
    """Compute pending repairs without mutating or copying project collections.

    ``shadow_has_result`` is deliberately separate from its signature because
    an empty cached result should not be rewritten on every edit.
    """
    return ReconciliationPlan(
        panel_ids=set(panel_coords) != set(uid_coords),
        shadow_result=bool(shadow_has_result) and shadow_source != current_shadow_source,
        wiring=topology_signature != diagram_signature,
    )
