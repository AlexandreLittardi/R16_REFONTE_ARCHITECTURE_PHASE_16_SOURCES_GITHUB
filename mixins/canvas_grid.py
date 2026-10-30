"""Interactions souris sur le canvas et dessin de la grille de panneaux."""

import csv
import json
import math
import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from constants import STRING_COLORS, BLOCK_COLORS
from ui.tab_ids import TabId
from ui.gesture_hit_testing import zone_at_point, zone_resize_handle, dimension_label_at
from domain.installation_edits import translate_zones, resize_zone, new_zone
from domain.roof_registration import shifted_photo_offset

try:
    import io
    from PIL import Image, ImageDraw, ImageTk, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class CanvasGridMixin:
    def on_left_press(self, event):
        tab_idx = self._get_active_tab_index()
        if tab_idx == TabId.INSTALLATION and self.roof_mode == 'move_image':
            self._begin_canvas_edit('installation:photo-offset')
            self._roof_image_drag_last = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            self.canvas.configure(cursor='fleur')
            return 'break'
        is_ctrl = bool(event.state & 0x0004)
        is_shift = bool(event.state & 0x0001)
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)

        self.drag_occurred = False
        self.pending_toggle_zone = None
        self.pending_single_select_zone = None

        # PathsToolsMixin owns roof polygons, distance markers and Cabling
        # path clicks.  CanvasGrid only dispatches the shared mouse position.
        if self._handle_path_canvas_press(tab_idx, cx, cy):
            return

        if tab_idx == TabId.INSTALLATION and self.roof_mode == "select" and not is_ctrl:
            hit_measure = dimension_label_at(self.measures, cx, cy, self.zoom_level)
            if hit_measure is not None:
                lx, ly = self.measures[hit_measure]["label"]
                self._begin_canvas_edit('installation:dimension-label')
                self.measure_drag_idx = hit_measure
                self.measure_drag_delta = (lx - cx / self.zoom_level, ly - cy / self.zoom_level)
                return

        # Si Ctrl est appuyé DANS L'ONGLET TOIT UNIQUEMENT : possibilité de Grab/Déplacer une zone
        if tab_idx == TabId.INSTALLATION and is_ctrl:
            hit_zone = zone_at_point(self.roof_zones, cx, cy, self.zoom_level)

            if hit_zone is not None:
                if is_shift:
                    self.selected_zone_indices.add(hit_zone)
                elif hit_zone not in self.selected_zone_indices:
                    self.selected_zone_indices = {hit_zone}
                self.active_zone_idx = hit_zone

                self._update_zone_entries_from_active()
                self._begin_canvas_edit('installation:zone')
                self.zone_drag_mode = "move"
                self.zone_drag_start_pt = (cx, cy)
                self.zone_drag_initial_rects = {
                    i: (self.roof_zones[i]["x1"], self.roof_zones[i]["y1"],
                        self.roof_zones[i]["x2"], self.roof_zones[i]["y2"])
                    for i in self.selected_zone_indices if 0 <= i < len(self.roof_zones)
                }
                self.draw_grid()
                return

        if tab_idx == TabId.INSTALLATION:  # Onglet Toit & Échelle
            if self.roof_mode in ["scale", "zone", "measure"]:
                self.temp_draw_start = (cx, cy)
            elif self.roof_mode == "select":
                # Vérification des poignées de la zone active (resize)
                if self.active_zone_idx is not None and 0 <= self.active_zone_idx < len(self.roof_zones):
                    z = self.roof_zones[self.active_zone_idx]
                    handle = zone_resize_handle(z, cx, cy, self.zoom_level)
                    if handle is not None:
                        self._begin_canvas_edit('installation:zone')
                        self.zone_drag_mode = handle
                        self.zone_drag_start_pt = (cx, cy)
                        self.zone_drag_initial_rect = (min(z["x1"], z["x2"]), min(z["y1"], z["y2"]),
                                                      max(z["x1"], z["x2"]), max(z["y1"], z["y2"]))
                        return

                # Hit test pour sélection et déplacement
                hit_zone = zone_at_point(self.roof_zones, cx, cy, self.zoom_level)

                if hit_zone is not None:
                    if is_shift:
                        if hit_zone in self.selected_zone_indices:
                            self.pending_toggle_zone = hit_zone
                        else:
                            self.selected_zone_indices.add(hit_zone)
                        self.active_zone_idx = hit_zone
                    else:
                        if hit_zone not in self.selected_zone_indices:
                            self.selected_zone_indices = {hit_zone}
                            self.active_zone_idx = hit_zone
                        else:
                            self.pending_single_select_zone = hit_zone
                            self.active_zone_idx = hit_zone

                    self._update_zone_entries_from_active()
                    self._begin_canvas_edit('installation:zone')
                    self.zone_drag_mode = "move"
                    self.zone_drag_start_pt = (cx, cy)
                    self.zone_drag_initial_rects = {
                        i: (self.roof_zones[i]["x1"], self.roof_zones[i]["y1"],
                            self.roof_zones[i]["x2"], self.roof_zones[i]["y2"])
                        for i in self.selected_zone_indices if 0 <= i < len(self.roof_zones)
                    }
                    self.draw_grid()
                else:
                    if not is_shift:
                        self.selected_zone_indices.clear()
                        self.active_zone_idx = None
                        self._update_zone_combo()
                        self.draw_grid()
            return

        if tab_idx == TabId.LAYOUT and self.layout_mode == "place_inverter":  # Onglet Layout & Blocs : placement d'un onduleur
            img_x, img_y = cx / self.zoom_level, cy / self.zoom_level
            self._place_pending_inverter_at(img_x, img_y)
            return

        if tab_idx == TabId.SINGLE_LINE:
            # DiagramEditorMixin owns all selection and dragging. This base
            # handler only receives link-mode clicks from its super() call.
            if not self.diagram_link_mode:
                return
            hit = self._hit_test_diagram_node(cx, cy)
            if hit:
                if self.diagram_link_first is None:
                    self.diagram_link_first = hit
                else:
                    if hit != self.diagram_link_first:
                        dist = simpledialog.askfloat("Distance", 'Cable length (m):', initialvalue=0.0, parent=self.root)
                        if dist is not None and dist >= 0:
                            from domain.diagram_commands import add_manual_link
                            edit=add_manual_link(self.diagram_nodes,self.diagram_links,
                                self.diagram_link_first,hit,style=self.diagram_link_style,
                                distance_m=dist)
                            self._apply_diagram_edit(edit)
                    self._cancel_diagram_link_mode()
                self.draw_grid()
            return

        if tab_idx == TabId.SHADOW:  # Onglet Ombre Pylône
            img_x, img_y = cx / self.zoom_level, cy / self.zoom_level
            if self.shadow_mode == "place_pylon":
                self._place_shadow_image_point('obstacle', img_x, img_y)
            elif self.shadow_mode == "place_ref":
                self._place_shadow_image_point('reference', img_x, img_y)
            return

        cell = self._get_cell_coords(event)

        if tab_idx == TabId.LAYOUT and is_shift and not is_ctrl:
            if cell in self.panels:
                if cell in self.selected_panel_coords:
                    self.selected_panel_coords.remove(cell)
                else:
                    self.selected_panel_coords.add(cell)
                orientation = self.panel_orientations.get(cell, {})
                self._set_layout_orientation_entries(
                    orientation.get("tilt_deg", self.panel_tilt_deg),
                    orientation.get("azimuth_deg", self.panel_azimuth_deg))
            else:
                self.selected_panel_coords.clear()
            self.draw_grid()
            return

        if is_ctrl and cell is not None:
            if tab_idx in (TabId.LAYOUT, TabId.STRINGING):
                self._begin_canvas_edit('layout:ctrl-paint')
            self.last_drag_cell = cell
            self._handle_ctrl_click_add(cell)
        else:
            # Never start canvas navigation with the left button.
            self.canvas.config(cursor="")

    def on_left_drag(self, event):
        tab_idx = self._get_active_tab_index()
        if tab_idx == TabId.INSTALLATION and self.roof_mode == 'move_image':
            if self._roof_image_drag_last is not None:
                x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
                dx, dy = x - self._roof_image_drag_last[0], y - self._roof_image_drag_last[1]
                self.roof_image_offset = shifted_photo_offset(
                    self.roof_image_offset, dx, dy, self.zoom_level)
                self._roof_image_drag_last = (x, y)
                # Move only the raster image; zones, panels and annotations stay fixed.
                self.canvas.move('roof_background', dx, dy)
            return 'break'
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)

        if self.measure_drag_idx is not None:
            self.measures[self.measure_drag_idx]["label"] = (
                cx / self.zoom_level + self.measure_drag_delta[0],
                cy / self.zoom_level + self.measure_drag_delta[1],
            )
            self.draw_grid()
            return

        if self.layout_mode == "place_inverter":
            return

        if self.zone_drag_mode and (self.active_zone_idx is not None or self.selected_zone_indices):
            x0, y0 = self.zone_drag_start_pt
            dx = (cx - x0) / self.zoom_level
            dy = (cy - y0) / self.zoom_level
            if math.hypot(cx - x0, cy - y0) > 3:
                self.drag_occurred = True

            if self.zone_drag_mode == "move" and self.zone_drag_initial_rects:
                for i, fields in translate_zones(self.zone_drag_initial_rects, dx, dy).items():
                    if 0 <= i < len(self.roof_zones):
                        self.roof_zones[i].update(fields)
            elif self.zone_drag_mode.startswith("resize_") and self.active_zone_idx is not None:
                fields = resize_zone(
                    self.zone_drag_initial_rect, self.zone_drag_mode, dx, dy,
                    zoom=self.zoom_level, px_per_mm=self.px_per_mm)
                self.roof_zones[self.active_zone_idx].update(fields)

            self._update_zone_entries_from_active()
            self._recalculate_zone_grids()
            self.draw_grid()
            return

        if tab_idx == TabId.INSTALLATION:  # Onglet Toit
            if self.temp_draw_start and self.roof_mode in ["scale", "zone", "measure"]:
                self.draw_grid()
                x0, y0 = self.temp_draw_start
                if self.roof_mode == "scale":
                    self.canvas.create_line(x0, y0, cx, cy, fill="#000000", width=1, arrow=tk.BOTH)
                elif self.roof_mode == "zone":
                    self.canvas.create_rectangle(x0, y0, cx, cy, outline="#00FF00", width=2, dash=(4, 4))
                elif self.roof_mode == "measure":
                    z=self.zoom_level
                    self._draw_dimension({'p1':(x0/z,y0/z),'p2':(cx/z,cy/z),
                        'label':((x0+cx)/2/z,(y0+cy)/2/z-14/z),
                        'axis':getattr(self,'dimension_mode','aligned')},z)
            return

        # Routing-area dragging is owned by EditorInteractionsMixin and
        # application.routing_commands; the old direct-mutation branch here
        # was unreachable through the application's gesture dispatch.

        if tab_idx == TabId.SINGLE_LINE:
            # Legacy direct mutation bypassed phase-4 copy-on-write diagram
            # commands and Undo/Redo. DiagramEditor handles normal dragging;
            # the only call reaching here is the link-mode no-op.
            return

        is_ctrl = bool(event.state & 0x0004)
        cell = self._get_cell_coords(event)

        if is_ctrl and cell is not None:
            if cell != self.last_drag_cell:
                self.last_drag_cell = cell
                self._handle_ctrl_click_add(cell)
        # Plain left drag does not move the canvas; use middle drag instead.

    def on_left_release(self, event):
        if self._get_active_tab_index() == TabId.INSTALLATION and self.roof_mode == 'move_image':
            self._roof_image_drag_last = None
            self.draw_grid()  # update scroll extents after the drag
            self._finish_canvas_edit('installation:photo-offset')
            return 'break'
        if self.measure_drag_idx is not None:
            self.measure_drag_idx = None
            self._finish_canvas_edit('installation:dimension-label')
            return
        tab_idx = self._get_active_tab_index()

        if tab_idx == TabId.INSTALLATION and self.polygon_drag_mode:
            self.polygon_drag_mode = None
            self.polygon_drag_start_pt = None
            self.polygon_drag_initial_points = None
            return

        if tab_idx == TabId.SINGLE_LINE:
            self.diagram_drag_node = None
            self.diagram_drag_start = None
            self.diagram_drag_orig = None
            return

        if tab_idx == TabId.INSTALLATION:
            if not getattr(self, "drag_occurred", False):
                if getattr(self, "pending_toggle_zone", None) is not None:
                    pz = self.pending_toggle_zone
                    if pz in self.selected_zone_indices:
                        self.selected_zone_indices.remove(pz)
                        if self.active_zone_idx == pz:
                            self.active_zone_idx = next(iter(self.selected_zone_indices)) if self.selected_zone_indices else None
                elif getattr(self, "pending_single_select_zone", None) is not None:
                    pz = self.pending_single_select_zone
                    self.selected_zone_indices = {pz}
                    self.active_zone_idx = pz

                self._update_zone_entries_from_active()
                self._update_zone_combo()

            self.pending_toggle_zone = None
            self.pending_single_select_zone = None
            self.drag_occurred = False

            if self.temp_draw_start and self.roof_mode in ["scale", "zone", "measure"]:
                cx = self.canvas.canvasx(event.x)
                cy = self.canvas.canvasy(event.y)
                x0, y0 = self.temp_draw_start

                img_x0, img_y0 = x0 / self.zoom_level, y0 / self.zoom_level
                img_cx, img_cy = cx / self.zoom_level, cy / self.zoom_level

                if self.roof_mode == "scale":
                    dist_px = math.hypot(img_cx - img_x0, img_cy - img_y0)
                    if dist_px > 5:
                        default_len = self.scale_length_mm if self.scale_length_mm > 0 else 1000.0
                        real_len = simpledialog.askfloat(
                            'Scale', 'Enter the real length of the drawn segment (mm):',
                            initialvalue=default_len, parent=self.root)
                        if real_len is not None and real_len > 0:
                            was_aligned = self._run_project_edit(
                                'installation:calibration', self._apply_scale_reference,
                                (img_x0, img_y0), (img_cx, img_cy), real_len)
                            if was_aligned:
                                messagebox.showinfo('Image aligned',
                                    'Replacement photograph resized to the existing project scale. '
                                    'Dimensions and survey geometry have been preserved.',
                                    parent=self.root)
                            elif self.roof_zones:
                                messagebox.showinfo('Dimensions recalculated',
                                    'Measurements and zone dimensions have been recalculated '
                                    'from the new scale. Check panel capacity and regenerate '
                                    'the layout if necessary.', parent=self.root)
                    self.roof_mode = "select"

                elif self.roof_mode == "measure":
                    if math.hypot(img_cx - img_x0, img_cy - img_y0) > 3:
                        def add_measure():
                            self.measures.append({"p1": (img_x0, img_y0), "p2": (img_cx, img_cy),
                                                  "label": ((img_x0 + img_cx) / 2,
                                                            (img_y0 + img_cy) / 2 - 12 / self.zoom_level),
                                                  "axis": getattr(self, 'dimension_mode', 'aligned')})
                        self._run_project_edit('installation:add-measure', add_measure)
                    self.roof_mode = "select"

                elif self.roof_mode == "zone":
                    if abs(img_cx - img_x0) > 10 / self.zoom_level and abs(img_cy - img_y0) > 10 / self.zoom_level:
                        zone = new_zone(
                            (img_x0, img_y0), (img_cx, img_cy),
                            zone_id=len(self.roof_zones) + 1,
                            px_per_mm=self.px_per_mm,
                            align_x=self.combo_align_x.get(),
                            align_y=self.combo_align_y.get())
                        self.roof_zones.append(zone)
                        # Creating a zone is the commit boundary for its grid.
                        self._recalculate_zone_grids()

                self.temp_draw_start = None
                self.draw_grid()
                return

        self.zone_drag_mode = None
        self.zone_drag_start_pt = None
        self.zone_drag_initial_rect = None
        self.zone_drag_initial_rects = {}
        self.canvas.config(cursor="")
        self.last_drag_cell = None

    def on_right_press(self, event):
        tab_idx = self._get_active_tab_index()
        if tab_idx == TabId.INSTALLATION and event.state & 0x0004:
            cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            for index in range(len(self.measures)-1,-1,-1):
                measure=self.measures[index]
                p1,p2=(measure['p1'],measure['p2']) if isinstance(measure,dict) else measure
                label=(measure.get('label') if isinstance(measure,dict) else None)
                candidates=[p1,p2,label or ((p1[0]+p2[0])/2,(p1[1]+p2[1])/2)]
                if any(abs(cx-x*self.zoom_level)<14 and abs(cy-y*self.zoom_level)<14
                       for x,y in candidates):
                    self._run_project_edit('installation:remove-measure',
                                           self.measures.pop, index)
                    self.draw_grid();return
        if self._handle_path_canvas_right_press(tab_idx, event):
            return

        is_ctrl = bool(event.state & 0x0004)
        cell = self._get_cell_coords(event)

        if cell is None:
            return

        if is_ctrl:
            if tab_idx in (TabId.LAYOUT, TabId.STRINGING):
                self._begin_canvas_edit('layout:ctrl-erase')
            self.last_drag_cell = cell
            self._handle_ctrl_click_remove(cell)

    def on_right_drag(self, event):
        is_ctrl = bool(event.state & 0x0004)
        cell = self._get_cell_coords(event)
        if is_ctrl and cell is not None and cell != self.last_drag_cell:
            self.last_drag_cell = cell
            self._handle_ctrl_click_remove(cell)

    # ========================================================
    # ACTIONS CTRL CLIC
    # ========================================================

    def _handle_ctrl_click_add(self, cell):
        if cell is None:
            return

        tab_idx = self._get_active_tab_index()

        if tab_idx == TabId.LAYOUT:  # Layout
            if cell not in self.panels:
                if self.var_block_paint_only.get():
                    return
                self.panels[cell] = self._get_next_available_panel_number()

            if self.active_block_name:
                self.panel_blocks[cell] = self.active_block_name
            elif cell in self.panel_blocks:
                del self.panel_blocks[cell]

            if hasattr(self, '_reconcile_project_state'):
                self._reconcile_project_state()
            self.draw_grid()

        elif tab_idx == TabId.STRINGING:  # Stringing
            if cell in self.panels:
                self.add_panel_to_string(cell)

    def _handle_ctrl_click_remove(self, cell):
        if cell is None:
            return

        tab_idx = self._get_active_tab_index()
        if tab_idx == TabId.LAYOUT:
            if cell in self.panels:
                del self.panels[cell]
                self.panel_orientations.pop(cell, None)
                self.selected_panel_coords.discard(cell)
                if cell in self.panel_blocks:
                    del self.panel_blocks[cell]
                self._clean_deleted_panels_from_strings()
                if hasattr(self, '_reconcile_project_state'):
                    self._reconcile_project_state()
                self.draw_grid()
        elif tab_idx == TabId.STRINGING:
            self.remove_panel_from_strings(cell)

    # ========================================================
    # ZOOM UNIFIÉ SUR SOURIS ET BOUTONS
    # ========================================================

    def _zoom_at_pointer(self, event, delta):
        old_zoom = self.zoom_level
        if delta > 0:
            new_zoom = min(5.0, old_zoom * 1.15)
        else:
            new_zoom = max(0.2, old_zoom / 1.15)

        if old_zoom == new_zoom:
            return

        x_canvas = self.canvas.canvasx(event.x)
        y_canvas = self.canvas.canvasy(event.y)

        self.zoom_level = new_zoom
        self.cell_size_px = max(10, int(40 * self.zoom_level))

        self.draw_grid()

        scale = new_zoom / old_zoom
        new_x = x_canvas * scale - event.x
        new_y = y_canvas * scale - event.y

        self.canvas.xview_moveto(max(0.0, min(1.0, new_x / max(1, self.total_w))))
        self.canvas.yview_moveto(max(0.0, min(1.0, new_y / max(1, self.total_h))))

    # ========================================================
    # GESTION DES BLOCS
    # ========================================================

    def create_new_block(self):
        name = simpledialog.askstring('New Block', 'Unique block name:', parent=self.root)
        if not name or not name.strip():
            return
        name = name.strip()
        if name in self.blocks:
            messagebox.showwarning('Warning', 'This block already exists.')
            return

        color = BLOCK_COLORS[len(self.blocks) % len(BLOCK_COLORS)]
        self.blocks[name] = {"color": color, "mppt_count": 2, "max_strings_per_mppt": 1}
        self._notify_wiring_change('inverter:create')
        self._update_combo_blocks()
        self.combo_blocks.set(name)
        self.active_block_name = name
        self._update_equipment_panel_from_active()

    def delete_active_block(self):
        if not self.active_block_name:
            return
        if messagebox.askyesno('Confirm', f"Delete block '{self.active_block_name}' ?"):
            del self.blocks[self.active_block_name]
            self.panel_blocks = {k: v for k, v in self.panel_blocks.items() if v != self.active_block_name}
            self._notify_wiring_change('inverter:delete')
            self.active_block_name = None
            self._update_combo_blocks()
            self.draw_grid()

    def _update_combo_blocks(self):
        values = ['No Block'] + list(self.blocks.keys())
        self.combo_blocks["values"] = values
        self.combo_blocks_equip["values"] = values
        if self.active_block_name not in self.blocks:
            self.active_block_name = None
            self.combo_blocks.set('No Block')
            self.combo_blocks_equip.set('No Block')
        else:
            self.combo_blocks_equip.set(self.active_block_name)
        self._update_equipment_panel_from_active()

    def _on_block_selected(self, event):
        val = self.combo_blocks.get()
        self.active_block_name = val if val != 'No Block' else None
        self.combo_blocks_equip.set(val)
        self._update_equipment_panel_from_active()

    # ========================================================
    # DESSIN & RENDU CANVAS
    # ========================================================

    def _get_grid_bounds(self):
        m = self.margin_cells
        if not self.panels:
            return (-m, m, -m, m)
        rows = [r for r, c in self.panels.keys()]
        cols = [c for r, c in self.panels.keys()]
        return (min(min(rows) - m, -m), max(max(rows) + m, m),
                min(min(cols) - m, -m), max(max(cols) + m, m))

    def _get_string_display_color(self, string_id, color):
            """Retourne la couleur d'affichage d'une string selon le toggle de focus (Onglet Stringing ou Matériel)."""
            tab_idx = self._get_active_tab_index()

            # Onglet 3 : Stringing
            if tab_idx == TabId.STRINGING:
                if getattr(self, "var_dim_inactive_strings", None) and self.var_dim_inactive_strings.get():
                    if string_id != self.active_string_id:
                        return "#B0B0B0"

            # Onglet 4 : Matériel
            elif tab_idx == 4:
                if getattr(self, "var_dim_mppt_strings", None) and self.var_dim_mppt_strings.get():
                    selected_item = self.equip_tree.selection() if hasattr(self, "equip_tree") else ()
                    if selected_item:
                        item_id = selected_item[0]
                        active_mppt_strings = set()

                        # Si un MPPT est sélectionné : garder visibles toutes ses strings
                        if item_id.startswith("mppt::"):
                            _, block_name, mppt_idx_str = item_id.split("::")
                            mppt_idx = int(mppt_idx_str)
                            active_mppt_strings = {
                                sid for sid, assign in self.string_mppt_assignment.items()
                                if assign.get("block") == block_name and assign.get("mppt") == mppt_idx
                            }
                        # Si un Bloc est sélectionné : garder visibles toutes les strings du bloc
                        elif item_id.startswith("block::"):
                            block_name = item_id.split("::", 1)[1]
                            active_mppt_strings = {
                                sid for sid, assign in self.string_mppt_assignment.items()
                                if assign.get("block") == block_name
                            }
                        # Si une String est directement sélectionnée
                        elif item_id.startswith("string::"):
                            active_mppt_strings = {item_id.split("::", 1)[1]}
                        elif item_id == "unassigned":
                            active_mppt_strings = {
                                sid for sid in self.strings if sid not in self.string_mppt_assignment
                            }

                        if string_id not in active_mppt_strings:
                            return "#B0B0B0"

            return color

    def _is_inactive_string_dimmed(self, string_id):
        """Indique si une string doit être visuellement grisée."""
        return (
            getattr(self, "var_dim_inactive_strings", None) is not None
            and self.var_dim_inactive_strings.get()
            and string_id != self.active_string_id
        )

    def draw_grid(self):
        self._refresh_block_capacity_label()

        self.canvas.delete("all")
        tab_idx = self._get_active_tab_index()
        zoom = self.zoom_level

        max_w = 1920
        max_h = 1080

        # Installation Area: the camera may zoom far into an aerial photograph.
        # Render only its visible tile at large scales, not a giant full raster.
        if HAS_PIL and self.roof_pil_img and tab_idx == TabId.INSTALLATION:
            self._draw_installation_photo(zoom)
            ox, oy = self.roof_image_offset
            max_w = max(max_w, (self.roof_pil_img.width+ox)*zoom)
            max_h = max(max_h, (self.roof_pil_img.height+oy)*zoom)
        elif HAS_PIL and self.roof_pil_img and tab_idx not in (6, 7, 9, 10):
            # Layout/Stringing/Cabling/Shadow used to allocate a full photo at
            # each zoom level (potentially >2 GB at zoom 5): use the same
            # viewport-limited tile as Installation Area.
            self._draw_installation_photo(zoom)
            ox, oy = self.roof_image_offset
            max_w = max(max_w, (self.roof_pil_img.width + ox) * zoom)
            max_h = max(max_h, (self.roof_pil_img.height + oy) * zoom)

        # Rendu spécifique Onglet Toit & Échelle
        if tab_idx == TabId.INSTALLATION:
            if HAS_PIL and self.roof_pil_img:
                if self.roof_polygons:
                    # The overlay is in survey coordinates; unlike the photo,
                    # it is intentionally unaffected by photograph registration.
                    from math import floor, ceil
                    crop = self._installation_photo_crop(zoom)
                    overlay = self._compute_polygon_overlay(zoom, viewport=crop)
                    if overlay is not None:
                        self.roof_overlay_tk_img = ImageTk.PhotoImage(overlay)
                        origin = (0,0) if crop is None else (crop[0]*zoom,crop[1]*zoom)
                        self.canvas.create_image(*origin, image=self.roof_overlay_tk_img, anchor=tk.NW)
                # Traçage échelle
                if self.scale_p1 and self.scale_p2:
                    x1, y1 = self.scale_p1[0] * zoom, self.scale_p1[1] * zoom
                    x2, y2 = self.scale_p2[0] * zoom, self.scale_p2[1] * zoom
                    self.canvas.create_line(x1, y1, x2, y2, fill="#000000", width=1, arrow=tk.BOTH)
                    self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2 - 10,
                                            text=f"{self.scale_length_mm:.0f} mm", fill="#000000", font=("Times New Roman", 10))

                # Traçage des mesures manuelle
                if self.px_per_mm > 0:
                    for measure in self.measures:
                        if isinstance(measure, dict):
                            p1, p2 = measure["p1"], measure["p2"]
                            label = measure["label"]
                        else:
                            p1, p2 = measure
                            label = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 - 12 / zoom)
                        self._draw_dimension(measure if isinstance(measure, dict) else
                                             {'p1':p1,'p2':p2,'label':label}, zoom)

                # Traçage des zones
                for idx, z in enumerate(self.roof_zones):
                    is_active = (idx == self.active_zone_idx)
                    is_selected = (idx in self.selected_zone_indices) or is_active
                    outline = "#0055FF" if is_selected else "#00AA00"
                    x1, y1 = min(z["x1"], z["x2"]) * zoom, min(z["y1"], z["y2"]) * zoom
                    x2, y2 = max(z["x1"], z["x2"]) * zoom, max(z["y1"], z["y2"]) * zoom

                    width_val = 3 if is_selected else 2
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline=outline, width=width_val)

                    orig_w_px = max(z["x1"], z["x2"]) - min(z["x1"], z["x2"])
                    orig_h_px = max(z["y1"], z["y2"]) - min(z["y1"], z["y2"])
                    w_str = f"{orig_w_px / self.px_per_mm:.0f}mm" if self.px_per_mm > 0 else f"{orig_w_px:.0f}px"
                    h_str = f"{orig_h_px / self.px_per_mm:.0f}mm" if self.px_per_mm > 0 else f"{orig_h_px:.0f}px"
                    self.canvas.create_text(x1 + 8, y1 + 10, anchor=tk.NW,
                                            text=f"Zone {z['id']} ({w_str} x {h_str})", fill=outline, font=("Arial", 9, "bold"))

                    if is_active:
                        hs = 5
                        for hx, hy in [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]:
                            self.canvas.create_rectangle(hx - hs, hy - hs, hx + hs, hy + hs, fill="#0055FF", outline="white")

                for idx, polygon in enumerate(self.roof_polygons):
                    coords = [(x * zoom, y * zoom) for x, y in polygon['points']]
                    color = '#1B5E20' if idx == self.active_polygon_idx else '#2E7D32'
                    if len(coords) >= 2:
                        flat = [v for xy in coords + [coords[0]] for v in xy]
                        self.canvas.create_line(*flat, fill=color, width=3 if idx == self.active_polygon_idx else 2)
                    for x, y in coords:
                        self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=color, outline='white')

                for marker in self.distance_markers:
                    self._draw_clearance_dimension(marker,zoom)

                self.total_w = max_w
                self.total_h = max_h
                min_x = min(0, self.roof_image_offset[0]*zoom)
                min_y = min(0, self.roof_image_offset[1]*zoom)
                from view_navigation import place_viewport
                self._navigation_world_content = (min_x, min_y, max_w, max_h)
                place_viewport(self.canvas, self.canvas.canvasx(0), self.canvas.canvasy(0),
                               content=self._navigation_world_content)
            # The Installation-area branch returns before the shared painter.
            # Preserve edit handles both with and without a roof photograph.
            self._draw_selected_polygon_handles(zoom, tab_idx)
            return

        # Rendu spécifique Onglet Cabling (chemins de câbles et points de rassemblement)
        if tab_idx == TabId.CABLING:
            if HAS_PIL and self.roof_pil_img:
                # Zone disponible coloriée = polygone(s) moins les zones occupées
                overlay = self._compute_polygon_overlay(zoom)
                if overlay is not None:
                    self.roof_overlay_tk_img = ImageTk.PhotoImage(overlay)
                    self.canvas.create_image(0, 0, image=self.roof_overlay_tk_img, anchor=tk.NW)

                # Contours des zones (toujours visibles, même sans polygone)
                for z in self.roof_zones:
                    x1, y1 = min(z["x1"], z["x2"]) * zoom, min(z["y1"], z["y2"]) * zoom
                    x2, y2 = max(z["x1"], z["x2"]) * zoom, max(z["y1"], z["y2"]) * zoom
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline="#616161", width=2)
                    self.canvas.create_text(x1 + 6, y1 + 8, anchor=tk.NW,
                                            text=f"Zone {z['id']}", fill="#424242", font=("Arial", 8, "bold"))

                # Contours des polygones
                for idx, poly in enumerate(self.roof_polygons):
                    is_active = (idx == self.active_polygon_idx)
                    color = "#1B5E20" if is_active else "#2E7D32"
                    pts = poly["points"]
                    scaled = [(x * zoom, y * zoom) for (x, y) in pts]
                    if len(scaled) >= 2:
                        flat = [coord for p in scaled for coord in p]
                        flat += [scaled[0][0], scaled[0][1]]  # fermeture du polygone
                        self.canvas.create_line(*flat, fill=color, width=3 if is_active else 2)
                    for (px, py) in scaled:
                        self.canvas.create_oval(px - 4, py - 4, px + 4, py + 4, fill=color, outline="white")
                    if scaled:
                        self.canvas.create_text(scaled[0][0] + 8, scaled[0][1] - 10,
                                                text=f"", fill=color,
                                                font=("Arial", 9, "bold"), anchor=tk.SW)

                # Marqueurs de mesure de distance entre les deux bords les plus proches du clic
                for marker in self.distance_markers:
                    self._draw_clearance_dimension(marker,zoom)

                # Réseau de chemins de câbles (routage préférentiel, Dijkstra)
                for idx, path in enumerate(self.cable_paths):
                    is_active = (idx == self.active_cable_path_idx)
                    color = "#E65100" if is_active else "#EF6C00"
                    pts = [(x * zoom, y * zoom) for (x, y) in path["points"]]
                    for i in range(len(pts) - 1):
                        self.canvas.create_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                                                fill=color, width=4 if is_active else 3)
                    for (px_, py_) in pts:
                        self.canvas.create_oval(px_ - 4, py_ - 4, px_ + 4, py_ + 4, fill=color, outline="white")

                # Points de rassemblement manuels des câbles par zone (les points
                # automatiques ne sont pas fixes : ils suivent la position de
                # l'onduleur et ne sont donc affichés qu'une fois les câbles calculés,
                # via _draw_cable_network_routes)
                for z in self.roof_zones:
                    if z.get("gather_point_manual") and z.get("gather_point"):
                        gx, gy = z["gather_point"][0] * zoom, z["gather_point"][1] * zoom
                        self.canvas.create_rectangle(gx - 6, gy - 6, gx + 6, gy + 6,
                                                     fill="#6A1B9A", outline="white", width=2)
                        self.canvas.create_text(gx, gy - 14, text=f"📍 Zone {z['id']}",
                                                fill="#6A1B9A", font=("Arial", 8, "bold"))

                if hasattr(self, "_draw_inverters"):
                    self._draw_inverters(zoom)

                if hasattr(self, "_draw_cable_network_routes"):
                    self._draw_cable_network_routes(zoom)

                self.total_w = max_w
                self.total_h = max_h
                self.canvas.config(scrollregion=(0, 0, max_w, max_h))
            return

        # Rendu spécifique Onglet Matériel (rien à dessiner : tout se passe
        # dans le panneau latéral)
        if tab_idx == 6:
            self.canvas.delete("all")
            self.canvas.create_text(
                20, 20, anchor=tk.NW,
                text='🧰 Enter project equipment in the side panel.',
                fill="#616161", font=("Arial", 11)
            )
            self.canvas.config(scrollregion=(0, 0, max_w, max_h))
            return

        # Rendu spécifique Onglet Schéma Unifilaire
        if tab_idx == TabId.SINGLE_LINE:
            if hasattr(self, "_draw_diagram"):
                self._draw_diagram()
            return

        # Rendu spécifique Onglet Ombre Pylône
        if tab_idx == TabId.SHADOW:
            if HAS_PIL and self.roof_pil_img:
                shadowed = self.shadow_result.get("shadowed", set()) if self.shadow_result else set()
                px_per_mm_eff = self.px_per_mm * zoom if self.px_per_mm > 0 else 0

                # Contours des zones + panneaux coloriés selon l'exposition à l'ombre
                if self.roof_zones and self.px_per_mm > 0:
                    # Zone grids are committed at edit/load/history boundaries.
                    # Painting shadows must not change persistent row ranges.
                    pw_px = self.panel_width_mm * px_per_mm_eff
                    ph_px = self.panel_height_mm * px_per_mm_eff

                    for z_idx, zone in enumerate(self.roof_zones):
                        x1 = min(zone["x1"], zone["x2"]) * zoom
                        y1 = min(zone["y1"], zone["y2"]) * zoom
                        x2 = max(zone["x1"], zone["x2"]) * zoom
                        y2 = max(zone["y1"], zone["y2"]) * zoom
                        z_height = zone.get("z_mm", 0.0)

                        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#616161", width=2)
                        self.canvas.create_text(
                            x1 + 6, y1 + 8, anchor=tk.NW,
                            text=f"Zone {zone['id']} (h={z_height:.0f}mm)",
                            fill="#424242", font=("Arial", 8, "bold")
                        )

                        rows = zone.get("rows", 0)
                        cols = zone.get("cols", 0)
                        row_base = zone.get("row_base", z_idx * 100)
                        off_x_px = zone.get("offset_x_mm", 0.0) * px_per_mm_eff
                        off_y_px = zone.get("offset_y_mm", 0.0) * px_per_mm_eff
                        grid_x1 = x1 + off_x_px
                        grid_y1 = y1 + off_y_px

                        shadow_pct = self.shadow_result.get("shadow_pct", {}) if self.shadow_result else {}
                        shadow_polygons = {
                            item["coord"]: item["polygon"]
                            for item in (self.shadow_result.get("shadow_polygons", []) if self.shadow_result else [])
                        }

                        for r in range(rows):
                            for c in range(cols):
                                coord = (row_base + r, c)
                                if not self._valid_zone_cell(zone, r, c):
                                    continue
                                if coord not in self.panels:
                                    continue
                                cx1 = grid_x1 + c * (pw_px+zone.get('gap_x_mm',0)*px_per_mm_eff)
                                cy1 = grid_y1 + r * (ph_px+zone.get('gap_y_mm',0)*px_per_mm_eff)
                                cx2, cy2 = cx1 + pw_px, cy1 + ph_px
                                corners = self._zone_rotate_rect(zone, cx1, cy1, cx2, cy2)
                                flat = [v for pt in corners for v in pt]
                                center_x, center_y = (sum(p[0] for p in corners)/4, sum(p[1] for p in corners)/4)

                                pct = shadow_pct.get(coord, 0.0)
                                self.canvas.create_polygon(*flat, fill="#FFF59D", outline="#78909C", width=1)

                                # Affichage géométrique de la surface réellement ombrée.
                                inter = shadow_polygons.get(coord)
                                if inter and pct > 0.01:
                                    flat_inter = []
                                    for px, py in inter:
                                        flat_inter.extend([px * zoom, py * zoom])
                                    if len(flat_inter) >= 6:
                                        self.canvas.create_polygon(
                                            *flat_inter, fill="#37474F", outline="#263238",
                                            width=1
                                        )

                                text_color = "#FFFFFF" if pct >= 50 else "#5D4037"
                                self.canvas.create_text(
                                    center_x, center_y,
                                    text=f"{self.panels[coord]}\n{pct:.1f}%",
                                    fill=text_color if pct >= 50 else "#5D4037",
                                    font=("Arial", min(60, max(7, int(pw_px / 4))), "bold"),
                                    justify=tk.CENTER,
                                    angle=zone.get("angle_deg", 0.0)
                                )

                # Traçage des segments d'ombre (un par hauteur de zone concernée)
                for (sx1, sy1, sx2, sy2) in self.shadow_result.get("segments", []) if self.shadow_result else []:
                    self.canvas.create_line(
                        sx1 * zoom, sy1 * zoom, sx2 * zoom, sy2 * zoom,
                        fill="#212121", width=3, dash=(6, 3)
                    )

                # Point de référence
                if self.pylon_ref_img_pos:
                    rx, ry = self.pylon_ref_img_pos[0] * zoom, self.pylon_ref_img_pos[1] * zoom
                    self.canvas.create_line(rx - 8, ry, rx + 8, ry, fill="#00838F", width=2)
                    self.canvas.create_line(rx, ry - 8, rx, ry + 8, fill="#00838F", width=2)
                    self.canvas.create_text(rx + 10, ry - 10, text='Reference', fill="#00838F",
                                            anchor=tk.W, font=("Arial", 8, "bold"))
                    if self.pylon_img_pos:
                        self.canvas.create_line(
                            rx, ry, self.pylon_img_pos[0] * zoom, self.pylon_img_pos[1] * zoom,
                            fill="#00838F", width=1, dash=(3, 3)
                        )

                # Marqueur du pylône
                if self.pylon_img_pos:
                    px_c, py_c = self.pylon_img_pos[0] * zoom, self.pylon_img_pos[1] * zoom
                    self.canvas.create_oval(px_c - 7, py_c - 7, px_c + 7, py_c + 7, fill="#D32F2F", outline="white", width=2)
                    self.canvas.create_text(
                        px_c + 10, py_c + 10, anchor=tk.NW,
                        text=f"Obstacle (H={self.pylon_height_mm:.0f}mm)",
                        fill="#D32F2F", font=("Arial", 9, "bold")
                    )

                # Bandeau d'information solaire
                res = self.shadow_result or {}
                if res.get("elevation") is not None:
                    max_pct = max(res.get("shadow_pct", {}).values(), default=0.0)
                    info_text = (
                        f"☀️ Azimuth {res['azimuth']:.0f}° — Elevation {res['elevation']:.1f}° — "
                        f"{len(res.get('shadowed', set()))} panel(s) affected — max {max_pct:.1f}%"
                    )
                else:
                    info_text = res.get("message") or 'Place the obstacle to preview its shadow.'
                self._draw_text_with_bg(10, 16, info_text, fill="#212121", anchor="w")

                self.total_w = max_w
                self.total_h = max_h
                self.canvas.config(scrollregion=(0, 0, max_w, max_h))
            return

        # ----------------------------------------------------
        # Rendu des Onglets Layout & Stringing
        # ----------------------------------------------------

        panel_to_string = {}
        sorted_keys = self._get_sorted_string_keys()
        for idx, str_id in enumerate(sorted_keys):
            coords = self.strings[str_id]
            color = STRING_COLORS[idx % len(STRING_COLORS)]
            for coord in coords:
                panel_to_string[coord] = (str_id, color)

        cell_centers = {}

        # MODE A: Grilles inscrites dans les zones définies
        if self.roof_zones and self.px_per_mm > 0:
            # Read only the previously committed grid projection.  A repaint
            # (including scroll/zoom) is never allowed to reassign row IDs.
            px_per_mm_eff = self.px_per_mm * zoom
            pw_px = self.panel_width_mm * px_per_mm_eff
            ph_px = self.panel_height_mm * px_per_mm_eff

            for z_idx, zone in enumerate(self.roof_zones):
                x1 = min(zone["x1"], zone["x2"]) * zoom
                y1 = min(zone["y1"], zone["y2"]) * zoom
                x2 = max(zone["x1"], zone["x2"]) * zoom
                y2 = max(zone["y1"], zone["y2"]) * zoom

                self.canvas.create_rectangle(x1, y1, x2, y2, outline="#1976D2", width=2, dash=(6, 4))
                self.canvas.create_text(x1 + 35, y1 + 12, text=f"Zone {zone['id']}", fill="#1976D2", font=("Arial", 9, "bold"))

                rows = zone.get("rows", 0)
                cols = zone.get("cols", 0)
                row_base = zone.get("row_base", z_idx * 100)
                off_x_px = zone.get("offset_x_mm", 0.0) * px_per_mm_eff
                off_y_px = zone.get("offset_y_mm", 0.0) * px_per_mm_eff

                grid_x1 = x1 + off_x_px
                grid_y1 = y1 + off_y_px

                for r in range(rows):
                    for c in range(cols):
                        coord = (row_base + r, c)
                        if not self._valid_zone_cell(zone, r, c):
                            continue
                        cx1 = grid_x1 + c * (pw_px+zone.get('gap_x_mm',0)*px_per_mm_eff)
                        cy1 = grid_y1 + r * (ph_px+zone.get('gap_y_mm',0)*px_per_mm_eff)
                        cx2 = cx1 + pw_px
                        cy2 = cy1 + ph_px

                        # Rotate the entire panel lattice about the installation zone centre.
                        corners = self._zone_rotate_rect(zone, cx1, cy1, cx2, cy2)
                        flat = [v for pt in corners for v in pt]
                        center_x, center_y = (sum(p[0] for p in corners)/4, sum(p[1] for p in corners)/4)
                        cell_centers[coord] = (center_x, center_y)
                        angle_disp = zone.get("angle_deg", 0.0)

                        if coord in self.panels:
                            panel_num = self.panels[coord]
                            block_name = self.panel_blocks.get(coord)

                            if block_name and block_name in self.blocks:
                                b_color = self.blocks[block_name]["color"]
                                self.canvas.create_polygon(*flat, fill="#FFFFFF", outline="#BDBDBD", width=1)

                                def _same_block(rr, cc, _bn=block_name):
                                    return self.panel_blocks.get((rr, cc)) == _bn

                                if not _same_block(row_base + r - 1, c):
                                    self.canvas.create_line(*corners[0], *corners[1], fill=b_color, width=4, dash=(6, 3))
                                if not _same_block(row_base + r + 1, c):
                                    self.canvas.create_line(*corners[3], *corners[2], fill=b_color, width=4, dash=(6, 3))
                                if not _same_block(row_base + r, c - 1):
                                    self.canvas.create_line(*corners[0], *corners[3], fill=b_color, width=4, dash=(6, 3))
                                if not _same_block(row_base + r, c + 1):
                                    self.canvas.create_line(*corners[1], *corners[2], fill=b_color, width=4, dash=(6, 3))
                            else:
                                self.canvas.create_polygon(*flat, fill="#FFFFFF", outline="#37474F", width=2)

                            if tab_idx in (3,4) and coord in panel_to_string and self._is_inactive_string_dimmed(panel_to_string[coord][0]):
                                self.canvas.create_polygon(*flat, fill="#E0E0E0", outline="#9E9E9E", width=1)

                            font_size = min(60, max(7, int(pw_px / 4)))
                            panel_string = panel_to_string.get(coord) if tab_idx in (3,4,8) else None
                            panel_is_dimmed = panel_string is not None and self._is_inactive_string_dimmed(panel_string[0])
                            panel_text_color = "#9E9E9E" if panel_is_dimmed else ("#1A237E" if coord in self.panel_blocks else "#212121")
                            if tab_idx != 3 or (panel_string and panel_string[0] == self.active_string_id):
                                self.canvas.create_text(
                                    center_x, center_y, text=str(panel_num),
                                    fill=panel_text_color, font=("Arial", font_size, "bold"), angle=angle_disp
                                )

                            if panel_string and coord == self.strings.get(panel_string[0],[None])[0]:
                                s_name, s_color = panel_string
                                s_color = self._get_string_display_color(s_name, s_color)
                                short_name = s_name.replace("String ", "S") if "String " in s_name else s_name[:3]
                                badge_w = max(22, int(pw_px * 0.55))
                                badge_h = max(16, int(ph_px * 0.30))
                                bx1, by1 = cx1 + 2, cy1 - badge_h - 3
                                bx2, by2 = bx1 + badge_w, by1 + badge_h

                                badge_corners = [
                                    self._zone_rotate_point(zone, center_x, center_y, px, py)
                                    for px, py in [(bx1, by1), (bx2, by1), (bx2, by2), (bx1, by2)]
                                ]
                                flat_badge = [v for pt in badge_corners for v in pt]
                                badge_cx, badge_cy = self._zone_rotate_point(
                                    zone, center_x, center_y, (bx1 + bx2) / 2, (by1 + by2) / 2
                                )

                                self.canvas.create_polygon(*flat_badge, fill=s_color, outline="")
                                self.canvas.create_text(
                                    badge_cx, badge_cy, text=short_name, fill="white",
                                    font=("Arial", min(60, max(9, int(badge_h * 0.68))), "bold"),
                                    angle=angle_disp
                                )
                        else:
                            self.canvas.create_polygon(*flat, fill="", outline="#90A4AE", width=1, dash=(3, 3))

        else:
            # MODE B: Mode Grille restreinte aux panneaux existants
            min_r, max_r, min_c, max_c = self._get_grid_bounds()
            self.min_r = min_r
            self.min_c = min_c

            cell_w = self.cell_size_px
            cell_h = int(cell_w * (self.panel_height_mm / self.panel_width_mm))
            self.cell_w = cell_w
            self.cell_h = cell_h

            offset_x = -min_c * cell_w
            offset_y = -min_r * cell_h

            for r in range(min_r, max_r):
                for c in range(min_c, max_c):
                    cx1 = offset_x + c * cell_w
                    cy1 = offset_y + r * cell_h
                    cx2, cy2 = cx1 + cell_w, cy1 + cell_h
                    coord = (r, c)
                    center_x = (cx1 + cx2) / 2
                    center_y = (cy1 + cy2) / 2
                    cell_centers[coord] = (center_x, center_y)

                    if coord in self.panels:
                        panel_num = self.panels[coord]
                        block_name = self.panel_blocks.get(coord)
                        if block_name and block_name in self.blocks:
                            b_color = self.blocks[block_name]["color"]
                            self.canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="#FFFFFF", outline="#BDBDBD", width=1)
                            def _same_block(rr, cc, _bn=block_name):
                                return self.panel_blocks.get((rr, cc)) == _bn
                            if not _same_block(r - 1, c):
                                self.canvas.create_line(cx1, cy1, cx2, cy1, fill=b_color, width=4, dash=(6, 3))
                            if not _same_block(r + 1, c):
                                self.canvas.create_line(cx1, cy2, cx2, cy2, fill=b_color, width=4, dash=(6, 3))
                            if not _same_block(r, c - 1):
                                self.canvas.create_line(cx1, cy1, cx1, cy2, fill=b_color, width=4, dash=(6, 3))
                            if not _same_block(r, c + 1):
                                self.canvas.create_line(cx2, cy1, cx2, cy2, fill=b_color, width=4, dash=(6, 3))
                        else:
                            self.canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="#FFFFFF", outline="#616161", width=2)

                        if tab_idx in (3,4) and coord in panel_to_string and self._is_inactive_string_dimmed(panel_to_string[coord][0]):
                            self.canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="#E0E0E0", outline="#9E9E9E", width=1)

                        panel_string = panel_to_string.get(coord) if tab_idx in (3,4,8) else None
                        panel_is_dimmed = panel_string is not None and self._is_inactive_string_dimmed(panel_string[0])
                        panel_text_color = "#9E9E9E" if panel_is_dimmed else ("#1A237E" if coord in self.panel_blocks else "#333333")
                        if tab_idx != 3 or (panel_string and panel_string[0] == self.active_string_id):
                            self.canvas.create_text(
                                center_x, center_y, text=str(panel_num),
                                fill=panel_text_color, font=("Arial", min(60, max(8, int(cell_w / 3.5))), "bold")
                            )

                        if panel_string and coord == self.strings.get(panel_string[0],[None])[0]:
                            s_name, s_color = panel_string
                            s_color = self._get_string_display_color(s_name, s_color)
                            short_name = s_name.replace("String ", "S") if "String " in s_name else s_name[:3]
                            badge_w = max(22, int(cell_w * 0.55))
                            badge_h = max(16, int(cell_h * 0.30))
                            bx1, by1 = cx1 + 2, cy1 - badge_h - 3
                            bx2, by2 = bx1 + badge_w, by1 + badge_h
                            self.canvas.create_rectangle(bx1, by1, bx2, by2, fill=s_color, outline="", width=0)
                            self.canvas.create_text((bx1 + bx2) / 2, (by1 + by2) / 2, text=short_name, fill="white",
                                                    font=("Arial", min(60, max(9, int(badge_h * 0.68))), "bold"))
                    else:
                        self.canvas.create_rectangle(cx1, cy1, cx2, cy2, fill="#FFFFFF", outline="#E0E0E0")

            max_w = max(max_w, (max_c - min_c) * cell_w + 100)
            max_h = max(max_h, (max_r - min_r) * cell_h + 100)

        # Lignes de Stringing
        for idx, str_id in enumerate(sorted_keys if tab_idx in (3,4,8) else []):
            coords = self.strings[str_id]
            color = self._get_string_display_color(str_id, STRING_COLORS[idx % len(STRING_COLORS)])
            for i in range(len(coords) - 1):
                c1 = coords[i]
                c2 = coords[i + 1]
                if c1 in cell_centers and c2 in cell_centers:
                    px1, py1 = cell_centers[c1]
                    px2, py2 = cell_centers[c2]
                    self.canvas.create_line(px1, py1, px2, py2, fill=color, width=4, capstyle=tk.ROUND)

        if hasattr(self, "_draw_inverters"):
            self._draw_inverters(zoom)

        if hasattr(self, "_draw_cable_network_routes"):
            self._draw_cable_network_routes(zoom)

        if tab_idx == TabId.LAYOUT:
            for coord in self.selected_panel_coords & self.panels.keys():
                corners = self._panel_rect(coord)
                if corners:
                    points = [value * zoom for corner in corners for value in corner]
                    self.canvas.create_polygon(*points, fill="", outline="#E91E63", width=4)
            
        self.total_w = max_w
        self.total_h = max_h
        from view_navigation import place_viewport
        ox, oy = self.roof_image_offset
        self._navigation_world_content = (min(0., ox*zoom), min(0., oy*zoom), max_w, max_h)
        place_viewport(self.canvas, self.canvas.canvasx(0), self.canvas.canvasy(0),
                       self._navigation_world_content)

        self._update_stats_display()

    def _draw_selected_polygon_handles(self, zoom, tab_idx):
        """Paint Installation-area edit handles in the main canvas renderer.

        Formerly an entire EditorInteractionsMixin.draw_grid override existed
        only for these four-pixel handles. They do not change project data.
        """
        idx=getattr(self, 'active_polygon_idx', None)
        if (tab_idx != 1 or getattr(self, 'path_mode', None) != 'select_polygon'
                or idx is None or not 0 <= idx < len(self.roof_polygons)):
            return
        for x,y in self.roof_polygons[idx]['points']:
            cx,cy=x*zoom,y*zoom
            self.canvas.create_rectangle(cx-4,cy-4,cx+4,cy+4,
                                         fill='white',outline='#222222',width=1)

    def _set_layout_orientation_entries(self, tilt, azimuth):
        for entry, value in ((self.entry_layout_tilt, tilt), (self.entry_layout_azimuth, azimuth)):
            entry.delete(0, tk.END)
            entry.insert(0, str(value))

    def apply_panel_orientation(self):
        try:
            tilt = float(self.entry_layout_tilt.get())
            azimuth = float(self.entry_layout_azimuth.get())
            if not math.isfinite(tilt) or not 0 <= tilt <= 90:
                raise ValueError("Tilt must be between 0° and 90°.")
            if not math.isfinite(azimuth) or not 0 <= azimuth < 360:
                raise ValueError("Azimuth must be between 0° and 360° (exclusive).")
        except ValueError as exc:
            messagebox.showerror("Invalid panel orientation", str(exc))
            return

        if self.selected_panel_coords:
            for coord in self.selected_panel_coords & self.panels.keys():
                self.panel_orientations[coord] = {"tilt_deg": tilt, "azimuth_deg": azimuth}
        else:
            self.panel_tilt_deg, self.panel_azimuth_deg = tilt, azimuth
            self.panel_orientations.clear()
        self.draw_grid()

    def _update_stats_display(self):
        nb_panels = len(self.panels)
        nb_strings = 0
        total_dist_px = 0.0

        for s_id, coords in self.strings.items():
            if len(coords) > 0:
                nb_strings += 1
                for i in range(len(coords) - 1):
                    p1 = self._get_panel_physical_center(coords[i])
                    p2 = self._get_panel_physical_center(coords[i+1])
                    total_dist_px += math.hypot(p2[0] - p1[0], p2[1] - p1[1])

        dist_m = 0.0
        if hasattr(self, "px_per_mm") and self.px_per_mm > 0:
            dist_m = (total_dist_px / self.px_per_mm) / 1000.0

        self.lbl_stats.config(
            text=f"Panels: {nb_panels}  |  Active strings: {nb_strings}  |  Total string length: {dist_m:.1f} m"
        )

    def center_view_on_origin(self):
        min_r, max_r, min_c, max_c = self._get_grid_bounds()
        tot_c = max_c - min_c
        tot_r = max_r - min_r
        if tot_c > 0 and tot_r > 0:
            self.canvas.xview_moveto(max(0.0, (-min_c) / tot_c - 0.1))
            self.canvas.yview_moveto(max(0.0, (-min_r) / tot_r - 0.1))

    def _get_cell_coords(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)

        if self.roof_zones and self.px_per_mm > 0:
            self._recalculate_zone_grids()
            px_per_mm_eff = self.px_per_mm * self.zoom_level
            pw_px = self.panel_width_mm * px_per_mm_eff
            ph_px = self.panel_height_mm * px_per_mm_eff

            for zone in self.roof_zones:
                rows = zone.get("rows", 0)
                cols = zone.get("cols", 0)
                if rows == 0 or cols == 0:
                    continue

                x1 = min(zone["x1"], zone["x2"]) * self.zoom_level
                y1 = min(zone["y1"], zone["y2"]) * self.zoom_level
                row_base = zone.get("row_base", 0)

                off_x_px = zone.get("offset_x_mm", 0.0) * px_per_mm_eff
                off_y_px = zone.get("offset_y_mm", 0.0) * px_per_mm_eff

                grid_x1 = x1 + off_x_px
                grid_y1 = y1 + off_y_px
                grid_x2 = grid_x1 + cols * pw_px
                grid_y2 = grid_y1 + rows * ph_px

                if grid_x1 <= cx <= grid_x2 and grid_y1 <= cy <= grid_y2:
                    c = int((cx - grid_x1) // pw_px)
                    r_local = int((cy - grid_y1) // ph_px)
                    c = max(0, min(cols - 1, c))
                    r_local = max(0, min(rows - 1, r_local))
                    return (row_base + r_local, c)

            return None

        return (int(cy // self.cell_h) + self.min_r, int(cx // self.cell_w) + self.min_c)

    def _get_active_tab_index(self):
        return self.ribbon_notebook.index(self.ribbon_notebook.select())

    # ========================================================
    # OMBRE PYLÔNE : CALCUL SOLAIRE & GÉOMÉTRIE
    # ========================================================
