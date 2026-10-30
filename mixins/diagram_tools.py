"""Onglet Schéma Unifilaire : génère automatiquement un schéma
Strings -> MPPT -> Onduleurs à partir des données de stringing/MPPT déjà
définies, et permet de l'ajuster manuellement (déplacer, ajouter des
éléments personnalisés, relier librement deux éléments)."""

import math
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, filedialog
import webbrowser

NODE_COLORS = {
    "inverter": "#FF9800",
    "mppt": "#039BE5",
    "string": "#43A047",
    "custom": "#8E24AA",
}

NODE_W = 150
NODE_H = 46

# Diagram text is deliberately screen-sized, not zoom-sized.  The boxes have a
# minimum on-screen footprint so labels remain readable when the canvas is zoomed out.
DIAGRAM_FONT_LABEL = 9
DIAGRAM_FONT_DETAIL = 8
DIAGRAM_FONT_DISTANCE = 9
DIAGRAM_MIN_SCREEN_W = 150
DIAGRAM_MIN_SCREEN_H = 46
DIAGRAM_COLLISION_GAP = 14
LINK_STYLES = {
    'solid': ('Solid line', ()),
    'dashed': ('Dashed line', (7, 4)),
    'dotted': ('Dotted line', (2, 4)),
    'dashdot': ('Dash-dot line', (8, 3, 2, 3)),
}


class DiagramToolsMixin:
    # ========================================================
    # ONGLET RUBAN
    # ========================================================

    def _build_tab_diagram_tools(self):
        ttk.Button(
            self.tab_diagram, text='🔁 Auto generate (Strings → MPPT → Inverters)',
            command=self.generate_diagram_auto
        ).pack(side=tk.LEFT, padx=5)

        ttk.Separator(self.tab_diagram, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Button(
            self.tab_diagram, text='➕ Custom element', command=self._add_custom_diagram_node
        ).pack(side=tk.LEFT, padx=5)

        self.diagram_link_menu_button = ttk.Menubutton(self.tab_diagram, text='🔗 Custom links')
        links_menu = tk.Menu(self.diagram_link_menu_button, tearoff=0)
        for style, (label, _dash) in LINK_STYLES.items():
            links_menu.add_command(label=label, command=lambda s=style: self._toggle_diagram_link_mode(s))
        self.diagram_link_menu_button['menu'] = links_menu
        self.diagram_link_menu_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            self.tab_diagram, text='🗑️ Delete selected element', command=self._delete_selected_diagram_node
        ).pack(side=tk.LEFT, padx=5)

        ttk.Separator(self.tab_diagram, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        mb_zoom_diagram = ttk.Menubutton(self.tab_diagram, text="🔍 Zoom")
        menu_zoom_diagram = tk.Menu(mb_zoom_diagram, tearoff=0)
        menu_zoom_diagram.add_command(label='🔍 Zoom in (+)', command=lambda: self._zoom_button_change(1.2))
        menu_zoom_diagram.add_command(label='🔍 Zoom out (-)', command=lambda: self._zoom_button_change(1 / 1.2))
        menu_zoom_diagram.add_separator()
        menu_zoom_diagram.add_command(label='🎯 Reset (100%)', command=self._reset_zoom)
        mb_zoom_diagram["menu"] = menu_zoom_diagram
        mb_zoom_diagram.pack(side=tk.RIGHT, padx=5)

        ttk.Label(
            self.tab_diagram,
            text='Left drag: pan | Right drag: select | Right drag selected block: move group',
            font=("Arial", 8), foreground="#555555"
        ).pack(side=tk.LEFT, padx=10)

    # ========================================================
    # PANNEAU LATÉRAL
    # ========================================================

    def _build_side_panel_diagram(self):
        self.side_panel_diagram = ttk.Frame(self.main_container, width=260, padding=5)

        ttk.Label(
            self.side_panel_diagram, text='Diagram elements', font=("Arial", 10, "bold")
        ).pack(pady=5)

        self.lst_diagram_nodes = tk.Listbox(self.side_panel_diagram, selectmode=tk.EXTENDED, exportselection=False, height=24)
        self.lst_diagram_nodes.pack(fill=tk.BOTH, expand=True, pady=5)
        self.lst_diagram_nodes.bind("<<ListboxSelect>>", self._on_diagram_list_select)

        ttk.Button(
            self.side_panel_diagram, text='🗑️ Delete', command=self._delete_selected_diagram_node
        ).pack(fill=tk.X, pady=(0, 5))

        ttk.Label(
            self.side_panel_diagram,
            text="This list reflects the generated diagram. Add custom elements "
                 "(protective devices, switchboard, meter) with the toolbar, "
                 "then choose a custom link style and click two elements. "
                 "Enter equipment values in Home > Configuration. Shift/Ctrl-click to select several elements.",
            font=("Arial", 8), foreground="#555555", justify=tk.LEFT, wraplength=240
        ).pack(pady=5, fill=tk.X)

    # ========================================================
    # GÉNÉRATION AUTOMATIQUE
    # ========================================================

    def _export_site_single_line(self, batteries,language='en'):
        """Rebuild the site topology from the CURRENT project, not a saved image."""
        try:
            from single_line_516 import build_model, write_svg
            snapshot=self._collect_project_data()
            model=build_model(snapshot,batteries)
            path=filedialog.asksaveasfilename(
                parent=self.root,title='Export preliminary single-line diagram',
                initialfile=f'{self.project_name}_single_line_{batteries}_BESS_{language.upper()}.svg',
                defaultextension='.svg',filetypes=[('Vector diagram SVG','*.svg')])
            if not path:return
            write_svg(model,path,language=language)
            problems='\n'.join(model['issues'][:6]) or 'No inconsistency detected by the automatic checks.'
            messagebox.showinfo('Preliminary diagram exported',
                                f'{path}\n\nChecks: {problems}\n\nDesigner review and sign-off required.',
                                parent=self.root)
            webbrowser.open_new_tab(__import__('pathlib').Path(path).resolve().as_uri())
        except (ValueError,OSError,KeyError,TypeError) as exc:
            messagebox.showerror('Diagram not exported',str(exc),parent=self.root)

    def generate_diagram_auto(self):
        desired_ids = set()
        new_auto_links = []

        x_str, x_mppt, x_inv = 160, 520, 880
        string_step = 155 if self.diagram_show_electrical else 90
        mppt_step = 155 if self.diagram_show_electrical else 100
        y_cursor_inv = 60

        for block_name, block in self.blocks.items():
            inv_id = f"inv::{block_name}"
            desired_ids.add(inv_id)
            mppt_count = max(1, int(block.get("mppt_count", 2)))

            mppt_ids_here = [f"mppt::{block_name}::{m}" for m in range(1, mppt_count + 1)]
            block_top_y = y_cursor_inv
            y_cursor_mppt = block_top_y

            for m in range(1, mppt_count + 1):
                mppt_id = f"mppt::{block_name}::{m}"
                desired_ids.add(mppt_id)

                strs = [
                    sid for sid, a in self.string_mppt_assignment.items()
                    if a.get("block") == block_name and a.get("mppt") == m
                ]

                y_cursor_str = y_cursor_mppt
                for sid in strs:
                    s_node_id = f"str::{sid}"
                    desired_ids.add(s_node_id)
                    node = self.diagram_nodes.setdefault(s_node_id, {})
                    
                    n_panels = len(self.strings.get(sid, []))
                    label_text = f"⚡ {sid.replace('String ', 'S')} ({n_panels} panels)"

                    node.update({"x":x_str,"y":y_cursor_str,"type": "string", "label": label_text})
                    new_auto_links.append((s_node_id, mppt_id))
                    y_cursor_str += string_step

                mppt_node = self.diagram_nodes.setdefault(mppt_id, {})
                mppt_node.update({"x":x_mppt,"y":y_cursor_mppt+(max(1,len(strs))-1)*string_step/2,
                                  "type": "mppt", "label": f"MPPT {m}"})
                new_auto_links.append((mppt_id, inv_id))

                y_cursor_mppt += max(mppt_step, len(strs) * string_step)

            inv_node = self.diagram_nodes.setdefault(inv_id, {})
            inv_node.update({"x":x_inv,"y":(block_top_y+y_cursor_mppt)/2,
                             "type": "inverter", "label": f"🔌 {block_name}"})

            y_cursor_inv = y_cursor_mppt + 100

        # Nettoyage des noeuds auto obsolètes (plus présents dans les données actuelles)
        for node_id in list(self.diagram_nodes.keys()):
            if node_id.startswith(("inv::", "mppt::", "str::")) and node_id not in desired_ids:
                del self.diagram_nodes[node_id]

        # On garde les liens manuels valides, on régénère les liens auto
        self.diagram_links = [
            link for link in self.diagram_links
            if not link.get("auto") and link["a"] in self.diagram_nodes and link["b"] in self.diagram_nodes
            and not any(link[end].startswith(("str::", "mppt::")) for end in ("a", "b"))
        ]
        # Cable routing is an explicit Cabling operation. Generating a drawing
        # must remain fast even when no cable network has been calculated yet.
        for a, b in new_auto_links:
            self.diagram_links.append({"a": a, "b": b, "auto": True})

        self.diagram_selected_node = None
        self._resolve_diagram_collisions()
        self._refresh_diagram_list()
        self.draw_grid()

    # ========================================================
    # ÉDITION MANUELLE
    # ========================================================

    def _add_custom_diagram_node(self):
        from domain.diagram_commands import add_custom_node
        label = simpledialog.askstring(
            'Custom element', 'Element name (e.g. AC protection, switchboard, meter):', parent=self.root
        )
        if not label or not label.strip():
            return
        dist = simpledialog.askfloat(
            'Distance', f"Cable distance to element '{label}' (metres):",
            initialvalue=5.0, parent=self.root
        )
        if dist is None:
            dist = 0.0  # Legacy: cancelling the distance creates the node without cable length.
        node_id = f'custom::{self.diagram_next_custom_id}'
        edit = add_custom_node(self.diagram_nodes, self.diagram_links, node_id, label,
                               selected=self.diagram_selected_node,
                               style=self.diagram_link_style, distance_m=dist)
        if not self._apply_diagram_edit(edit, record_after=False):
            return
        self.diagram_next_custom_id += 1
        self.diagram_selected_node = node_id
        self._resolve_diagram_collisions()
        if getattr(self, '_guard_ready', False):
            self._record_history()
        self._refresh_diagram_list()
        self.draw_grid()

    def _toggle_diagram_link_mode(self, style='solid'):
        if style not in LINK_STYLES:
            return
        if self.diagram_link_mode and self.diagram_link_style == style:
            self._cancel_diagram_link_mode()
            return
        self.diagram_link_style = style
        self.diagram_link_mode = True
        self.diagram_link_first = None
        self.diagram_link_menu_button.configure(text=f'🔗 {LINK_STYLES[style][0]}: select two')

    def _cancel_diagram_link_mode(self):
        self.diagram_link_mode = False
        self.diagram_link_first = None
        self.diagram_link_menu_button.configure(text='🔗 Custom links')

    def _edit_diagram_electrical_specs(self):
        """Record STC module ratings and an optional nominal inverter AC rating."""
        dialog = tk.Toplevel(self.root)
        dialog.title('Electrical values in single-line diagram')
        dialog.transient(self.root)
        dialog.resizable(False, False)
        fields = (
            ('pmax_w', 'Module Pmax (W)'), ('voc_v', 'Module Voc (V)'),
            ('vmp_v', 'Module Vmp / Vmpp (V)'), ('isc_a', 'Module Isc (A)'),
            ('imp_a', 'Module Imp / Impp (A)'),
            ('inverter_ac_kw', 'Inverter nominal AC power (kW, optional)'),
        )
        body = ttk.Frame(dialog, padding=14)
        body.pack(fill=tk.BOTH, expand=True)
        ttk.Label(body, text='Module ratings at STC; values are multiplied by the actual panel count.',
                  wraplength=385).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 8))
        entries = {}
        for i, (key, label) in enumerate(fields, 1):
            ttk.Label(body, text=label).grid(row=i, column=0, sticky='w', pady=3)
            entry = ttk.Entry(body, width=16)
            value = self.diagram_electrical_specs.get(key)
            if value is not None:
                entry.insert(0, str(value))
            entry.grid(row=i, column=1, sticky='e', padx=(12, 0), pady=3)
            entries[key] = entry

        def from_equipment():
            categories = getattr(self, 'material_categories', {}) or {}
            modules = categories.get('modules', {}).get('rows', [])
            inverters = categories.get('inverters', {}).get('rows', [])
            if not modules:
                messagebox.showinfo('Electrical values', 'Enter a PV module in the equipment sheet first.', parent=dialog)
                return
            module = modules[0]
            column_keys = {'pmax_w': 'Pmax (W)', 'voc_v': 'Voc (V)', 'vmp_v': 'Vmp (V)',
                           'isc_a': 'Isc (A)', 'imp_a': 'Imp (A)'}
            for key, column in column_keys.items():
                if str(module.get(column, '')).strip():
                    entries[key].delete(0, tk.END)
                    entries[key].insert(0, str(module[column]))
            if inverters and str(inverters[0].get('Puissance (kVA)', '')).strip():
                # kVA cannot be converted to kW without a power factor.
                messagebox.showinfo('Electrical values',
                                    'The equipment sheet lists inverter kVA. Enter nominal AC kW separately.',
                                    parent=dialog)

        ttk.Button(body, text='Copy PV module from equipment sheet', command=from_equipment).grid(
            row=7, column=0, columnspan=2, sticky='w', pady=(12, 4))
        show = tk.BooleanVar(value=self.diagram_show_electrical)
        ttk.Checkbutton(body, text='Show electrical values on diagram', variable=show).grid(
            row=8, column=0, columnspan=2, sticky='w', pady=4)

        def save():
            parsed = {}
            try:
                for key, _label in fields:
                    raw = entries[key].get().strip()
                    if raw:
                        value = float(raw.replace(',', '.'))
                        if not math.isfinite(value) or value <= 0:
                            raise ValueError(f'{key} must be positive.')
                        parsed[key] = value
                if show.get() and any(key not in parsed for key in ('pmax_w', 'voc_v', 'vmp_v', 'isc_a', 'imp_a')):
                    raise ValueError('Enter all five PV module ratings to show electrical values.')
                if parsed.get('vmp_v', 0) > parsed.get('voc_v', float('inf')):
                    raise ValueError('Module Vmp must not exceed Voc.')
                if parsed.get('imp_a', 0) > parsed.get('isc_a', float('inf')):
                    raise ValueError('Module Imp must not exceed Isc.')
            except ValueError as exc:
                messagebox.showerror('Electrical values', str(exc), parent=dialog)
                return
            if getattr(self, '_guard_ready', False):
                self._record_history()
            self.diagram_electrical_specs = parsed
            self.diagram_show_electrical = show.get()
            if getattr(self, '_guard_ready', False):
                self._record_history()
            dialog.destroy()
            self.draw_grid()

        buttons = ttk.Frame(body)
        buttons.grid(row=9, column=0, columnspan=2, sticky='e', pady=(12, 0))
        ttk.Button(buttons, text='Cancel', command=dialog.destroy).pack(side=tk.RIGHT, padx=4)
        ttk.Button(buttons, text='Apply', command=save).pack(side=tk.RIGHT, padx=4)
        dialog.bind('<Escape>', lambda event: dialog.destroy())
        dialog.bind('<Return>', lambda event: save())
        dialog.grab_set()
        entries['pmax_w'].focus_set()

    def _toggle_diagram_electrical(self):
        if not self.diagram_show_electrical and not all(
                key in self.diagram_electrical_specs for key in ('pmax_w', 'voc_v', 'vmp_v', 'isc_a', 'imp_a')):
            self._edit_diagram_electrical_specs()
            return
        if getattr(self, '_guard_ready', False):
            self._record_history()
        self._diagram_layout_applied = None
        self.diagram_show_electrical = not self.diagram_show_electrical
        if getattr(self, '_guard_ready', False):
            self._record_history()
        self.draw_grid()

    def _diagram_node_metric_lines(self, node_id):
        """Use selected equipment for every string, MPPT and inverter."""
        if not self.diagram_show_electrical:return []
        from project_validation import number
        from engineering_inputs import module_for_string,ac_limit_kw
        if hasattr(self,'_project_snapshot'):
            signature=repr((self.strings,self.cable_string_params,self.material_categories,
                            self.equipment_links,self.electrical_design))
            cached=getattr(self,'_diagram_rating_cache',None)
            if not cached or cached[0]!=signature:
                project=self._project_snapshot();rated={}
                for sid,members in self.strings.items():
                    row=module_for_string(project,sid)
                    rated[sid]={key:number(row.get(column)) for key,column in
                        [('pmax_w','Pmax (W)'),('voc_v','Voc (V)'),('vmp_v','Vmp (V)'),('isc_a','Isc (A)'),('imp_a','Imp (A)')]}
                self._diagram_rating_cache=(signature,rated,project)
            _,rated,project=self._diagram_rating_cache
        else:
            rated={sid:self.diagram_electrical_specs for sid in self.strings};project=None
        def specs(sid):return rated.get(sid,{})
        def total(sids,key,series=False):
            values=[specs(sid).get(key) for sid in sids]
            if not values or any(v is None for v in values):return None
            return sum(v*(len(self.strings[sid]) if series else 1) for v,sid in zip(values,sids))
        def fmt(value):return '-' if value is None else f'{value:.2f}'
        if node_id.startswith('str::'):
            sid=node_id.split('::',1)[1];count=len(self.strings.get(sid,[]));row=specs(sid)
            return [f'Pdc {fmt(total([sid],"pmax_w",True)/1000 if total([sid],"pmax_w",True) is not None else None)} kW  |  Voc {fmt(total([sid],"voc_v",True))} V',
                    f'Vmp {fmt(total([sid],"vmp_v",True))} V  |  Isc {fmt(row.get("isc_a"))} A  Imp {fmt(row.get("imp_a"))} A']
        if node_id.startswith(('mppt::','inv::')):
            parts=node_id.split('::');block=parts[1]
            sids=[sid for sid,a in self.string_mppt_assignment.items()
                  if a.get('block')==block and self.strings.get(sid)
                  and (parts[0]=='inv' or str(a.get('mppt'))==parts[2])]
            if not sids:return ['No assigned strings']
            power=total(sids,'pmax_w',True)
            lines=[f'{len(sids)} strings | Pdc {fmt(power/1000 if power is not None else None)} kW']
            if parts[0]=='inv':
                try:pac=ac_limit_kw(project,block) if project else self.diagram_electrical_specs.get('inverter_ac_kw')
                except ValueError:pac=None
                lines.append(f'Nominal Pac {fmt(pac)} kW')
            else:
                def volts(key):
                    values=[specs(sid).get(key) for sid in sids]
                    if any(v is None for v in values):return '-'
                    values=[v*len(self.strings[sid]) for v,sid in zip(values,sids)]
                    return fmt(min(values)) if min(values)==max(values) else fmt(min(values))+'-'+fmt(max(values))
                lines += [f'Voc {volts("voc_v")} V | Vmp {volts("vmp_v")} V',
                          f'Isc sum {fmt(total(sids,"isc_a"))} A | Imp sum {fmt(total(sids,"imp_a"))} A']
            return lines
        return []


    def _diagram_screen_centres(self):
        """Canvas-space centres after applying zoom."""
        zoom = max(0.05, float(self.zoom_level))
        return {
            node_id: (float(node.get('x', 0.0)) * zoom,
                      float(node.get('y', 0.0)) * zoom)
            for node_id, node in self.diagram_nodes.items()
        }

    def _resolve_diagram_collisions(self):
        """Separate overlapping diagram blocks while preserving their columns.

        The automatic topology is column-based (strings -> MPPT -> inverter), so
        vertical displacement is the least disruptive correction.  Custom nodes
        are treated the same way.  Positions are stored back in logical canvas
        coordinates so links, hit testing and subsequent dragging stay coherent.
        """
        if len(self.diagram_nodes) < 2:
            return

        zoom = max(0.05, float(self.zoom_level))
        gap = DIAGRAM_COLLISION_GAP
        ids = list(self.diagram_nodes)
        sizes={node_id:self._diagram_screen_node_size(node_id) for node_id in ids}

        # A bounded relaxation is deterministic and sufficient for the small
        # number of columns used by the single-line diagram.
        for _pass in range(max(4, len(ids) * 2)):
            moved = False
            centres = self._diagram_screen_centres()

            # Process top-to-bottom, then left-to-right.  Earlier nodes keep their
            # location; later nodes are pushed down only as much as necessary.
            ordered = sorted(ids, key=lambda nid: (centres[nid][1], centres[nid][0], nid))
            placed = []
            for node_id in ordered:
                cx, cy = centres[node_id]
                w, h = sizes[node_id]

                while True:
                    collision = None
                    for other_id in placed:
                        ox, oy = centres[other_id]
                        ow, oh = sizes[other_id]
                        # A box placed exactly at the required gap can differ
                        # by a rounding bit at fractional zoom. Treat that
                        # boundary as clear, otherwise the loop keeps moving
                        # it to the same coordinate indefinitely.
                        x_overlap = abs(cx - ox) < (w + ow) / 2 + gap - 1e-7
                        y_overlap = abs(cy - oy) < (h + oh) / 2 + gap - 1e-7
                        if x_overlap and y_overlap:
                            collision = (other_id, oy, oh)
                            break
                    if collision is None:
                        break

                    _other_id, oy, oh = collision
                    cy = oy + (oh + h) / 2 + gap
                    centres[node_id] = (cx, cy)
                    moved = True

                placed.append(node_id)

            if moved:
                for node_id, (cx, cy) in centres.items():
                    self.diagram_nodes[node_id]['x'] = cx / zoom
                    self.diagram_nodes[node_id]['y'] = cy / zoom
            else:
                break

    def _hit_test_diagram_node(self, cx, cy):
        zoom = self.zoom_level
        for node_id, node in self.diagram_nodes.items():
            nx, ny = node["x"] * zoom, node["y"] * zoom
            w, h = self._diagram_screen_node_size(node_id)
            if nx - w / 2 <= cx <= nx + w / 2 and ny - h / 2 <= cy <= ny + h / 2:
                return node_id
        return None



    def _refresh_diagram_list(self):
        if not hasattr(self, "lst_diagram_nodes"):
            return
        self.lst_diagram_nodes.delete(0, tk.END)
        self._diagram_list_ids = []
        for node_id, node in self.diagram_nodes.items():
            self.lst_diagram_nodes.insert(tk.END, node.get("label", node_id))
            self._diagram_list_ids.append(node_id)

    def _get_string_length_m(self, sid):
        """Longueur cumulée (en m) du câblage d'une string, panneau à panneau.
        Retourne None si l'échelle n'est pas définie."""
        if self.px_per_mm <= 0:
            return None
        coords = self.strings.get(sid, [])
        px_dist = 0.0
        for i in range(len(coords) - 1):
            p1 = self._get_panel_physical_center(coords[i])
            p2 = self._get_panel_physical_center(coords[i + 1])
            px_dist += math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        return (px_dist / self.px_per_mm) / 1000.0

    # ========================================================
    # RENDU
    # ========================================================

