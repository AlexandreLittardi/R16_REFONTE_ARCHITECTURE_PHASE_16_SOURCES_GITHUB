"""UI-agnostic lifecycle of one pointer-edit history transaction.

A user gesture is either open or closed. Its owner is explicit, so nested
callbacks cannot accidentally close an unrelated transaction. Project state,
Tk and history records are deliberately not stored here.
"""
from dataclasses import dataclass


@dataclass
class EditTransactionGate:
    owner: str | None = None

    @property
    def active(self):
        return self.owner is not None

    def begin(self, owner):
        if not isinstance(owner, str) or not owner:
            raise ValueError('An edit transaction needs a nonempty owner')
        if self.active:
            return False
        self.owner = owner
        return True

    def finish(self, owner=None):
        if not self.active or (owner is not None and owner != self.owner):
            return False
        self.owner = None
        return True

    def abort(self):
        self.owner = None
