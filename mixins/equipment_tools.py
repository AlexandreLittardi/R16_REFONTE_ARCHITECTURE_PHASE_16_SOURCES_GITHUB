"""Gestion des equipements et repartition des strings dans les MPPT."""

import csv
import json
import math
import os
import sys
import tkinter as tk
from sort_utils import natural_sort_key
from tkinter import filedialog, messagebox, simpledialog, ttk
from project_validation import string_label
from domain.mppt_edits import propose_mppt_assignment, interpret_equipment_drop

try:
    import io
    from PIL import Image, ImageDraw, ImageTk, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False



class EquipmentToolsMixin:
    def _on_block_selected_equip(self, event):
        val = self.combo_blocks_equip.get()
        self.active_block_name = val if val != 'No Block' else None
        self.combo_blocks.set(val)
        self._update_equipment_panel_from_active()

    def _update_equipment_panel_from_active(self):
        self.entry_mppt_count.delete(0, tk.END)
        self.entry_strings_per_mppt.delete(0, tk.END)

        if not self.active_block_name or self.active_block_name not in self.blocks:
            self._set_mppt_capacity_label('Strings: - / -', 'black')
            return

        block = self.blocks[self.active_block_name]
        self.entry_mppt_count.insert(0, str(block.get("mppt_count", 2)))
        self.entry_strings_per_mppt.insert(0, str(block.get("max_strings_per_mppt", 1)))

        self._refresh_block_capacity_label()

    def _refresh_block_capacity_label(self):
        if not hasattr(self, "lbl_block_capacity"):
            return
        if not self.active_block_name or self.active_block_name not in self.blocks:
            self._set_mppt_capacity_label('Strings: - / -', 'black')
            return

        block = self.blocks[self.active_block_name]
        mppt_count = block.get("mppt_count", 2)
        strings_per_mppt = block.get("max_strings_per_mppt", 1)
        capacity = mppt_count * strings_per_mppt
        used = self._get_block_string_count(self.active_block_name)

        color = "#C62828" if used > capacity else "#2E7D32"
        self._set_mppt_capacity_label(f"Strings: {used} / {capacity}", color)

    def _set_mppt_capacity_label(self, label, color):
        self.lbl_block_capacity.config(text=label, foreground=color)
        dialog_label = getattr(self, 'lbl_mppt_dialog_capacity', None)
        if dialog_label is not None and dialog_label.winfo_exists():
            dialog_label.config(text=label, foreground=color)

    def _apply_block_equipment(self):
        if not self.active_block_name or self.active_block_name not in self.blocks:
            messagebox.showwarning('Warning', 'Select a block.')
            return

        try:
            mppt_count = int(self.entry_mppt_count.get())
            strings_per_mppt = int(self.entry_strings_per_mppt.get())
            if mppt_count <= 0 or strings_per_mppt <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror('Error', 'Invalid MPPT count or strings per MPPT.')
            return

        self.blocks[self.active_block_name]["mppt_count"] = mppt_count
        self.blocks[self.active_block_name]["max_strings_per_mppt"] = strings_per_mppt
        self._notify_wiring_change('inverter:capacity')
        self._refresh_block_capacity_label()
        self._refresh_equipment_tree()

    def _on_mppt_current_string_changed(self, event=None):
        string_id = self.combo_mppt_current_string.get()
        if string_id not in self.strings:
            return
        self.active_string_id = string_id
        self.combo_strings.set(string_id)
        self._update_string_listbox()
        if hasattr(self, 'equip_tree') and self.equip_tree.exists(f'string::{string_id}'):
            self.equip_tree.selection_set(f'string::{string_id}')
            self.equip_tree.see(f'string::{string_id}')
        self.draw_grid()

    def export_mppt_csv(self):
        """Export every nonempty string, including unassigned strings, in a readable CSV."""
        string_ids = [sid for sid in self._get_sorted_string_keys() if self.strings.get(sid)]
        if not string_ids:
            messagebox.showwarning('Warning', 'No strings to export.')
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension='.csv', filetypes=[('CSV files', '*.csv')],
            title='Export MPPT assignments as CSV')
        if not filepath:
            return
        try:
            self._prune_mppt_assignments()
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as output:
                writer = csv.writer(output, delimiter=';')
                writer.writerow(['Block', 'MPPT', 'String', 'Panel count',
                                 'Panel numbers', 'Cable length (m)', 'Cable route'])
                for sid in string_ids:
                    assignment = self.string_mppt_assignment.get(sid, {})
                    coords = self.strings[sid]
                    length_mm, via_network = self.compute_cable_length_mm(sid)
                    writer.writerow([
                        assignment.get('block') or self._get_string_block(sid) or '',
                        assignment.get('mppt', 'Unassigned'), sid, len(coords),
                        ', '.join(str(self.panels.get(coord, '')) for coord in coords),
                        f'{length_mm / 1000:.2f}' if length_mm is not None else '',
                        ('Network' if via_network else 'Direct') if length_mm is not None else '',
                    ])
            messagebox.showinfo('Success', f'MPPT CSV exported:\n{filepath}')
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror('Error', f'Unable to export MPPT CSV:\n{exc}')

    def _get_block_string_count(self, block_name):
        """Nombre de strings connectées (au moins un panneau) à ce bloc/onduleur."""
        count = 0
        for coords in self.strings.values():
            if not coords:
                continue
            for (r, c) in coords:
                if self.panel_blocks.get((r, c)) == block_name:
                    count += 1
                    break
        return count

    # ========================================================
    # RÉPARTITION DES STRINGS DANS LES MPPT
    # ========================================================

    def _get_string_block(self, string_id):
        """Retourne le nom du bloc (onduleur) auquel appartient la string, ou None."""
        coords = self.strings.get(string_id, [])
        for coord in coords:
            b = self.panel_blocks.get(coord)
            if b:
                return b
        return None

    def _prune_mppt_assignments(self):
        """Remove assignments to deleted strings, blocks or invalid MPPTs."""
        before=self.string_mppt_assignment
        cleaned = {}
        for sid, assign in self.string_mppt_assignment.items():
            coords = self.strings.get(sid)
            if not coords:
                continue
            block_name = assign.get("block")
            mppt_idx = assign.get("mppt")
            block = self.blocks.get(block_name)
            if not block:
                continue
            if not (isinstance(mppt_idx, int) and 1 <= mppt_idx <= block.get("mppt_count", 2)):
                continue
            cleaned[sid] = assign
        self.string_mppt_assignment = cleaned
        if cleaned != before:
            self._notify_wiring_change('mppt:prune')

    def _assign_string_to_mppt(self, string_id, block_name, mppt_idx, show_errors=True):
        """Tente d'affecter une string à un MPPT donné, en respectant la capacité et
        la règle : toutes les strings d'un même MPPT doivent avoir le même nombre de panneaux."""
        proposal = propose_mppt_assignment(
            self.string_mppt_assignment, self.strings, self.blocks,
            string_id, block_name, mppt_idx)
        if proposal.error:
            if show_errors:
                if proposal.error == 'empty_string':
                    messagebox.showwarning('Warning', 'This string has no panels.')
                elif proposal.error == 'missing_block':
                    messagebox.showerror('Error', 'Inverter block not found.')
                elif proposal.error == 'invalid_mppt':
                    messagebox.showerror('Error', 'Invalid MPPT number.')
                elif proposal.error == 'different_panel_counts':
                    messagebox.showerror(
                        'Incompatible',
                        'Strings assigned to the same MPPT must have the same panel count '
                        f'({proposal.existing_panel_count} ≠ {len(self.strings[string_id])}).')
                elif proposal.error == 'mppt_full':
                    messagebox.showerror('Capacity reached', 'This MPPT has reached its string capacity.')
            return False
        changed = proposal.assignments != self.string_mppt_assignment
        if changed:
            self.string_mppt_assignment = proposal.assignments
            self._notify_wiring_change('mppt:assign')
        return True

    def _unassign_string_from_mppt(self, string_id):
        if self.string_mppt_assignment.pop(string_id, None) is not None:
            self._notify_wiring_change('mppt:unassign')

    def _clear_mppt_assignments(self):
        if not self.string_mppt_assignment:
            return
        if messagebox.askyesno('Confirm', 'Clear all string assignments to MPPTs?'):
            self.string_mppt_assignment = {}
            self._notify_wiring_change('mppt:clear')
            self._refresh_equipment_tree()

    def _auto_distribute_strings_to_mppt(self):
        """Distribue les strings dans l'ordre naturel (String 1, 2, 3...) :
        d'abord 1 string par MPPT en partant du MPPT 1, puis, s'il reste des
        strings, une 2e (ou plus, selon max_strings_per_mppt) en repartant du
        DERNIER MPPT vers le premier, pour concentrer le surplus en fin de
        rangée (ex. String 11 va sur MPPT 10 plutôt que de revenir sur MPPT 1).
        Deux strings d'un même MPPT doivent toujours avoir le même nombre de
        panneaux ; comme les strings de même longueur se suivent dans l'ordre
        naturel, cette règle est respectée naturellement."""
        if not self.blocks:
            messagebox.showwarning('Warning', 'No inverter block is defined.')
            return

        self._prune_mppt_assignments()

        new_assignment = {}
        unassigned = []

        all_sorted_keys = self._get_sorted_string_keys()
        order_index = {s: i for i, s in enumerate(all_sorted_keys)}

        sorted_blocks = sorted(self.blocks.items(), key=lambda kv: natural_sort_key(kv[0]))

        for block_name, block in sorted_blocks:

            strings_in_block = [
                sid for sid, coords in self.strings.items()
                if coords and self._get_string_block(sid) == block_name
            ]

            if not strings_in_block:
                continue

            mppt_count = max(1, int(block.get("mppt_count", 2)))
            max_per_mppt = max(1, int(block.get("max_strings_per_mppt", 1)))

            # Tri naturel des strings de ce bloc : String 1, String 2...
            strings_in_block.sort(key=lambda s: order_index.get(s, 0))

            mppts = {mppt: [] for mppt in range(1, mppt_count + 1)}
            remaining = list(strings_in_block)

            # ---------------------------------------------------------
            # 1. Une string par MPPT, dans l'ordre naturel, en partant
            #    du MPPT 1 (String 1 -> MPPT 1, String 2 -> MPPT 2, ...)
            # ---------------------------------------------------------
            for mppt in range(1, mppt_count + 1):
                if not remaining:
                    break
                mppts[mppt].append(remaining.pop(0))

            # ---------------------------------------------------------
            # 2. Strings en trop : on repart du DERNIER MPPT vers le
            #    premier pour ajouter une 2e string (ou plus), sans
            #    jamais dépasser max_per_mppt et en respectant la
            #    compatibilité du nombre de panneaux.
            # ---------------------------------------------------------
            while remaining:
                placed = False
                for mppt in range(mppt_count, 0, -1):
                    if len(mppts[mppt]) >= max_per_mppt:
                        continue
                    if not mppts[mppt]:
                        continue

                    first_sid = mppts[mppt][0]
                    if len(self.strings[first_sid]) != len(self.strings[remaining[0]]):
                        continue

                    mppts[mppt].append(remaining.pop(0))
                    placed = True
                    break

                if not placed:
                    break

            # Strings restantes = impossible à placer
            unassigned.extend(remaining)

            # Génération finale des affectations
            for mppt, sids in mppts.items():
                # Sécurité absolue : ne jamais dépasser max_per_mppt
                for sid in sids[:max_per_mppt]:
                    new_assignment[sid] = {
                        "block": block_name,
                        "mppt": mppt
                    }

        changed=new_assignment!=self.string_mppt_assignment
        self.string_mppt_assignment = new_assignment
        if changed:self._notify_wiring_change('mppt:auto_distribute')
        self._refresh_equipment_tree()

        if unassigned:
            messagebox.showwarning(
                'Incomplete distribution',
                'Some strings could not be assigned:\n'
                + ", ".join(unassigned)
            )
        else:
            messagebox.showinfo(
                'Distribution complete',
                'All strings have been assigned to MPPTs.'
            )

    def _refresh_equipment_tree(self):
            if not hasattr(self, "equip_tree"):
                return

            self._prune_mppt_assignments()
            tree = self.equip_tree

            # 1. Mémoriser l'état d'ouverture (ouvert/fermé) de tous les nœuds existants
            open_states = {}
            for item_id in tree.get_children():
                # Mémoriser l'état du bloc/groupe principal
                open_states[item_id] = tree.item(item_id, "open")
                # Mémoriser l'état des sous-nœuds (ex: MPPTs)
                for child_id in tree.get_children(item_id):
                    open_states[child_id] = tree.item(child_id, "open")

            # 2. Vider l'arbre
            children = tree.get_children()
            if children:
                tree.delete(*children)

            # 3. Reconstruire l'arbre en réappliquant les états mémorisés
            #    (tri naturel des blocs/onduleurs : INV1, INV2, INV3... au lieu
            #    de l'ordre d'insertion dans le dict self.blocks)
            sorted_blocks = sorted(self.blocks.items(), key=lambda kv: natural_sort_key(kv[0]))
            for block_name, block in sorted_blocks:
                block_iid = f"block::{block_name}"
                mppt_count = block.get("mppt_count", 2)
                max_per_mppt = max(1, block.get("max_strings_per_mppt", 1))
                capacity = mppt_count * max_per_mppt
                used = self._get_block_string_count(block_name)
                over = used > capacity

                # Utiliser l'état mémorisé ou True par défaut s'il s'agit d'un nouveau nœud
                is_block_open = open_states.get(block_iid, True)

                placement_flag = "📍" if block_name in getattr(self, "inverter_positions", {}) else '⚠️ inverter not placed'

                tree.insert(
                    "", tk.END, iid=block_iid,
                    text=f"🔌 {block_name}  —  {used}/{capacity} strings  {placement_flag}",
                    open=is_block_open, tags=("block", "over") if over else ("block",)
                )

                for m in range(1, mppt_count + 1):
                    mppt_iid = f"mppt::{block_name}::{m}"
                    assigned_here = sorted(
                        (sid for sid, a in self.string_mppt_assignment.items()
                         if a.get("block") == block_name and a.get("mppt") == m),
                        key=natural_sort_key
                    )
                    panel_count = len(self.strings.get(assigned_here[0], [])) if assigned_here else None
                    label = f"▸ MPPT {m}   ({len(assigned_here)}/{max_per_mppt})"
                    if panel_count is not None:
                        label += f"  —  {panel_count} panels/string"

                    is_mppt_open = open_states.get(mppt_iid, True)

                    tree.insert(block_iid, tk.END, iid=mppt_iid, text=label, open=is_mppt_open, tags=("mppt",))

                    for sid in assigned_here:
                        n = len(self.strings.get(sid, []))
                        length_label = self._format_cable_length_label(sid)
                        tree.insert(
                            mppt_iid, tk.END, iid=f"string::{sid}",
                            text=f"⚡ {string_label(sid)}  —  {n} panels{length_label}", tags=("string",)
                        )

            assigned_sids = set(self.string_mppt_assignment.keys())
            unassigned = [
                sid for sid in self._get_sorted_string_keys()
                if self.strings.get(sid) and sid not in assigned_sids
            ]
            if unassigned:
                is_unassigned_open = open_states.get("unassigned", True)
                tree.insert("", tk.END, iid="unassigned", text='⏳ Strings not assigned to an MPPT', open=is_unassigned_open, tags=("block",))
                for sid in unassigned:
                    n = len(self.strings[sid])
                    b = self._get_string_block(sid) or 'no block'
                    length_label = self._format_cable_length_label(sid)
                    tree.insert(
                        "unassigned", tk.END, iid=f"string::{sid}",
                        text=f"⚡ {string_label(sid)}  —  {n} panels  ({b}){length_label}", tags=("string",)
                    )

    def _format_cable_length_label(self, string_id):
        """Formate la longueur de câble string -> onduleur pour l'arbre équipement,
        ex. '  —  🔌 12.4 m' ou '  —  🔌 8.1 m (direct, pas de chemin)'."""
        if not hasattr(self, "compute_cable_length_mm"):
            return ""
        length_mm, via_network = self.compute_cable_length_mm(string_id)
        if length_mm is None:
            return ""
        length_m = length_mm / 1000.0
        suffix = "" if via_network else ' (direct, no path)'
        return f"  —  🔌 {length_m:.1f} m{suffix}"

    def _on_equip_tree_press(self, event):
        row = self.equip_tree.identify_row(event.y)
        self._equip_drag_item = row if row.startswith("string::") else None

    def _on_equip_tree_release(self, event):
        drag_item = getattr(self, '_equip_drag_item', None)
        self._equip_drag_item = None
        if not drag_item:
            return
        tree = self.equip_tree
        target = tree.identify_row(event.y)
        target_parent = tree.parent(target) if target.startswith('string::') else None
        drop = interpret_equipment_drop(drag_item, target, target_parent)
        if drop is None:
            return
        if drop.action == 'choose_mppt':
            messagebox.showinfo('Info', 'Drop the string directly onto a specific MPPT.')
        elif drop.action == 'unassign':
            self._run_project_edit('equipment:mppt-drop', self._unassign_string_from_mppt,
                                   drop.string_id)
            self._refresh_equipment_tree()
        elif drop.action == 'assign':
            changed = self._run_project_edit('equipment:mppt-drop',
                                             self._assign_string_to_mppt,
                                             drop.string_id, drop.block_name, drop.mppt_idx)
            if changed:
                self._refresh_equipment_tree()

    # ========================================================
    # ONGLET OMBRE PYLÔNE
    # ========================================================
