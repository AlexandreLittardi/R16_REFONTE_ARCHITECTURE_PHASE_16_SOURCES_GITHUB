"""Single-line diagram interaction: select, drag, group moves and layout."""
import tkinter as tk
from tkinter import ttk
from diagram_layout import arrange
from domain.diagram_commands import move_nodes, position_nodes
from view_navigation import place_viewport, zoom_view, viewport_center

class DiagramEditorMixin:
    def _build_tab_diagram_tools(self):
        super()._build_tab_diagram_tools()
        ttk.Button(self.tab_diagram,text='Reflow diagram',command=self._reflow_diagram).pack(side='left',padx=3)
        ttk.Button(self.tab_diagram,text='Fit diagram',command=self._fit_diagram).pack(side='left',padx=3)
        ttk.Button(self.tab_diagram,text='Show electrical values',command=self._toggle_diagram_electrical).pack(side='left',padx=3)

    def _build_main_area(self):
        super()._build_main_area()
        self.canvas.bind('<ButtonRelease-3>',self.on_right_release)

    def on_left_press(self, event):
        if self._get_active_tab_index() != 7 or self.diagram_link_mode:
            return super().on_left_press(event)
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        hit = self._hit_test_diagram_node(x, y)
        additive = bool(getattr(event, 'state', 0) & 0x0005)
        current = set(getattr(self, 'diagram_selected_nodes', set())) if additive else set()
        if hit is not None:
            current.add(hit)
        self.diagram_selected_nodes = current
        self.diagram_selected_node = next(iter(current), None)
        self._diagram_left_drag = (
            (x, y, {key: (self.diagram_nodes[key]['x'], self.diagram_nodes[key]['y'])
                    for key in current}) if hit is not None else None
        )
        if self._diagram_left_drag is not None:
            self._begin_diagram_gesture()
        self.draw_grid()
        return 'break'

    def on_left_drag(self, event):
        if self._get_active_tab_index() != 7 or self.diagram_link_mode:
            return super().on_left_drag(event)
        drag = getattr(self, '_diagram_left_drag', None)
        if drag:
            x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            self._preview_diagram_move(drag[2],
                                       (x-drag[0])/self.zoom_level,
                                       (y-drag[1])/self.zoom_level)
        return 'break'

    def on_left_release(self, event):
        if self._get_active_tab_index() != 7 or self.diagram_link_mode:
            return super().on_left_release(event)
        self._diagram_left_drag = None
        self._finish_diagram_gesture()
        return 'break'

    def on_right_press(self,event):
        if self._get_active_tab_index()!=7:return super().on_right_press(event)
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        selected=set(getattr(self,'diagram_selected_nodes',set()))
        hit=self._hit_test_diagram_node(x,y)
        self._diagram_right={'start':(x,y),'selected':selected,'add':bool(event.state&0x0005),'hit':hit}
        # A right drag from an already selected block moves that selection.
        if hit in selected and not self._diagram_right['add']:
            self._diagram_right['original']={k:(self.diagram_nodes[k]['x'],self.diagram_nodes[k]['y']) for k in selected}
            self._begin_diagram_gesture()
        return 'break'

    def on_right_drag(self,event):
        if self._get_active_tab_index()!=7:return super().on_right_drag(event)
        state=getattr(self,'_diagram_right',None)
        if not state:return 'break'
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y);x0,y0=state['start']
        if 'original' in state:
            self._preview_diagram_move(state['original'],
                                       (x-x0)/self.zoom_level,
                                       (y-y0)/self.zoom_level)
        else:
            self.canvas.delete('diagram_selection_box')
            self.canvas.create_rectangle(x0,y0,x,y,outline='#2E5B86',width=1,tags='diagram_selection_box')
        return 'break'

    def on_right_release(self,event):
        if self._get_active_tab_index()!=7:
            self.last_drag_cell=None
            # Non-diagram Ctrl+right strokes are handled by CanvasGrid.
            self._finish_canvas_edit('layout:ctrl-erase')
            return
        state=getattr(self,'_diagram_right',None);self._diagram_right=None
        self._finish_diagram_gesture()
        self.canvas.delete('diagram_selection_box')
        if not state:return
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y);x0,y0=state['start']
        if 'original' not in state:
            selected=state['selected'] if state['add'] else set()
            if abs(x-x0)+abs(y-y0)<5:
                if state['hit']:
                    if state['add'] and state['hit'] in selected:selected.remove(state['hit'])
                    else:selected.add(state['hit'])
            else:
                left,right=sorted((x0/self.zoom_level,x/self.zoom_level));top,bottom=sorted((y0/self.zoom_level,y/self.zoom_level))
                for key,node in self.diagram_nodes.items():
                    w,h=self._diagram_node_size(key)
                    if left<=node['x']+w/2 and right>=node['x']-w/2 and top<=node['y']+h/2 and bottom>=node['y']-h/2:selected.add(key)
            self.diagram_selected_nodes=selected;self.diagram_selected_node=next(iter(selected),None)
        self.draw_grid()

    def _apply_diagram_edit(self, edit, *, invalidate_layout=False, record_after=True):
        """One user edit = one history boundary, independent of canvas painting."""
        if not edit.changed:
            return False
        if getattr(self, '_guard_ready', False) and not getattr(self, '_restoring', False):
            self._record_history()  # capture any preceding unsaved edit
        self.diagram_nodes, self.diagram_links = edit.nodes, edit.links
        if invalidate_layout:
            self._diagram_layout_applied = None
        if record_after and getattr(self, '_guard_ready', False) and not getattr(self, '_restoring', False):
            self._record_history()
        return True

    def _begin_diagram_gesture(self):
        if getattr(self, '_guard_ready', False):
            self._record_history()
        self._diagram_gesture_active = True

    def _preview_diagram_move(self, originals, dx, dy):
        edit = move_nodes(self.diagram_nodes, self.diagram_links, originals, dx, dy)
        if edit.changed:
            # No intermediate undo snapshots: the whole drag is one edit.
            self.diagram_nodes = edit.nodes
            self.draw_grid()
        return edit.changed

    def _finish_diagram_gesture(self):
        if getattr(self, '_diagram_gesture_active', False):
            self._diagram_gesture_active = False
            if getattr(self, '_guard_ready', False):
                self._record_history()

    def _diagram_node_size(self,key):
        from tkinter.font import Font
        label=self.diagram_nodes[key].get('label',key)
        metrics=self._diagram_node_metric_lines(key)
        cache=getattr(self,'_diagram_size_cache',None)
        if cache is None:cache=self._diagram_size_cache={}
        signature=(label,tuple(metrics),self.diagram_nodes[key].get('type'))
        saved=cache.get(key)
        if saved and saved[0]==signature:return saved[1]
        if not hasattr(self,'_diagram_measure_font'):self._diagram_measure_font=Font(root=self.root,family='Arial',size=10)
        font=self._diagram_measure_font
        width=max(280,max((font.measure(t) for t in [label]+metrics),default=0)+35)
        size=width,(82 if self.diagram_nodes[key].get('type')=='string' else 62)+19*len(metrics)
        cache[key]=(signature,size)
        return size

    def _diagram_saved_route_labels(self):
        """Opening a drawing reads current saved routes; it never runs the router."""
        plan=getattr(self,'electrical_route_plan_3d',{}) or {}
        if not plan.get('routes'):return {}
        if plan.get('source_signature')!=self._route_signature():return {}
        return {sid:f'A+B {rec["loop_length_m"]:.1f} m'
                for sid,rec in plan['routes'].items()
                if isinstance(rec.get('loop_length_m'),(int,float))}

    def _diagram_layout_signature(self):
        return (tuple((k,self._diagram_node_size(k)) for k in self.diagram_nodes),
                tuple((l['a'],l['b']) for l in self.diagram_links if l.get('auto')),self.diagram_show_electrical)

    def _reflow_diagram(self):
        sizes={k:self._diagram_node_size(k) for k in self.diagram_nodes}
        positions=arrange(self.diagram_nodes,self.diagram_links,sizes)
        self._apply_diagram_edit(position_nodes(self.diagram_nodes, self.diagram_links, positions))
        self._diagram_layout_applied=self._diagram_layout_signature();self.draw_grid()

    def _diagram_screen_node_size(self, node_id):
        # Boxes and text share the same zoom. A screen-size minimum used to
        # trigger collision repair on every redraw and destroy the saved layout.
        zoom = max(.02, float(self.zoom_level))
        width, height = self._diagram_node_size(node_id)
        return width * zoom, height * zoom

    def _prepare_diagram_layout(self):
        """Reconcile layout before paint, never while emitting canvas primitives.

        User positions survive redraw/zoom. Re-layout only for a new topology or
        when explicitly requested via Reflow, preserving the legacy signature.
        """
        signature = self._diagram_layout_signature()
        if (getattr(self, '_restoring', False)
                or getattr(self, '_diagram_layout_applied', None) == signature):
            return False
        sizes = {key: self._diagram_node_size(key) for key in self.diagram_nodes}
        edit = position_nodes(self.diagram_nodes, self.diagram_links,
                              arrange(self.diagram_nodes, self.diagram_links, sizes))
        if edit.changed:
            self.diagram_nodes = edit.nodes
        self._diagram_layout_applied = signature
        return edit.changed

    def _draw_diagram(self):
        """Paint the precomputed single-line model; no geometry or history edits."""
        from mixins.diagram_tools import NODE_COLORS, LINK_STYLES
        from project_validation import natural
        zoom = max(.02, float(self.zoom_level))
        sizes = {key: self._diagram_node_size(key) for key in self.diagram_nodes}
        route_labels = self._diagram_saved_route_labels()
        canvas = self.canvas
        def font(size, bold=False):
            return ('Arial', max(2, round(size * zoom)), 'bold' if bold else 'normal')

        for inv in sorted((k for k in self.diagram_nodes if k.startswith('inv::')), key=natural):
            block = inv.split('::', 1)[1]
            keys = [inv] + [k for k in self.diagram_nodes if k.startswith('mppt::' + block + '::')]
            keys += ['str::' + sid for sid, allocation in self.string_mppt_assignment.items()
                     if allocation.get('block') == block and 'str::' + sid in self.diagram_nodes]
            left = min(self.diagram_nodes[k]['x'] - sizes[k][0] / 2 for k in keys) - 18
            top = min(self.diagram_nodes[k]['y'] - sizes[k][1] / 2 for k in keys) - 45
            right = max(self.diagram_nodes[k]['x'] + sizes[k][0] / 2 for k in keys) + 18
            bottom = max(self.diagram_nodes[k]['y'] + sizes[k][1] / 2 for k in keys) + 18
            canvas.create_rectangle(left*zoom, top*zoom, right*zoom, bottom*zoom,
                                    fill='#F1F5F9', outline='#CBD5E1')
            canvas.create_text((left+12)*zoom, (top+18)*zoom, anchor='w',
                               text=block + '  |  Strings > MPPT > Inverter',
                               fill='#334155', font=font(13, True))

        for link in self.diagram_links:
            a, b = link.get('a'), link.get('b')
            if a not in self.diagram_nodes or b not in self.diagram_nodes:
                continue
            first, second = self.diagram_nodes[a], self.diagram_nodes[b]
            ax, ay, bx, by = first['x']*zoom, first['y']*zoom, second['x']*zoom, second['y']*zoom
            aw, bw = sizes[a][0]*zoom, sizes[b][0]*zoom
            direction = 1 if bx >= ax else -1
            start, end = ax + direction*aw/2, bx - direction*bw/2
            lane = (start + end)/2
            auto = link.get('auto')
            dash = () if auto else LINK_STYLES.get(link.get('style', 'dashed'), LINK_STYLES['dashed'])[1]
            canvas.create_line(start, ay, lane, ay, lane, by, end, by,
                               fill='#78909C' if auto else '#D32F2F', width=max(1, 2*zoom), dash=dash)
            label = link.get('distance_label', '')
            if auto and a.startswith('str::'):
                label = route_labels.get(a.split('::', 1)[1], 'A+B: calculate in Cabling')
            elif not label and isinstance(link.get('distance_m'), (int, float)) and link['distance_m'] > 0:
                label = f"{link['distance_m']:.1f} m"
            if label:
                canvas.create_text((start+lane)/2, ay-12*zoom, text=label,
                                   fill='#455A64', font=font(9))

        selected = getattr(self, 'diagram_selected_nodes', set())
        for key, node in self.diagram_nodes.items():
            x, y = node['x']*zoom, node['y']*zoom
            width, height = sizes[key][0]*zoom, sizes[key][1]*zoom
            top = y-height/2
            active = key in selected or key == getattr(self, 'diagram_selected_node', None)
            canvas.create_rectangle(x-width/2, top, x+width/2, y+height/2,
                fill=NODE_COLORS.get(node.get('type'), '#607D8B'),
                outline='#0055FF' if active else '#263238', width=2 if active else 1)
            metrics = self._diagram_node_metric_lines(key)
            is_string = node.get('type') == 'string' and key.startswith('str::')
            label = str(node.get('label', key)).split(' | ')[0]
            label_y = top+17*zoom if metrics or is_string else y
            canvas.create_text(x, label_y, text=label, fill='white', font=font(10, True),
                               width=max(1, width-12*zoom))
            if is_string:
                length = self._get_string_length_m(key.split('::', 1)[1])
                text = 'Module chain: scale not set' if length is None else f'Module chain ~ {length:.1f} m'
                canvas.create_text(x, top+36*zoom, text=text, fill='#FFEB3B', font=font(9),
                                   width=max(1, width-12*zoom))
            start = 65 if is_string else 42
            for index, text in enumerate(metrics):
                canvas.create_text(x, top+(start+19*index)*zoom, text=text,
                                   fill='white', font=font(9), width=max(1, width-12*zoom))

        if not self.diagram_nodes:
            canvas.create_text(30, 40, anchor='nw',
                text='No diagram yet. Use Auto generate after assigning strings to MPPT inputs.',
                fill='#616161', font=('Arial', 10), width=max(200, canvas.winfo_width()-60))
        # Keep the camera stable while editing: recomputing a scrollregion with
        # an origin at zero can otherwise jump the view after every drag.
        region = place_viewport(canvas, canvas.canvasx(0), canvas.canvasy(0))
        if region:
            self.total_w, self.total_h = region[2]-region[0], region[3]-region[1]

    def generate_diagram_auto(self):
        if getattr(self, '_guard_ready', False):
            self._record_history()
        self._diagram_layout_applied = None
        result = super().generate_diagram_auto()
        # Keep unassigned strings visible, rather than silently dropping them.
        added = False
        for sid, members in self.strings.items():
            key = 'str::' + sid
            if members and key not in self.diagram_nodes:
                self.diagram_nodes[key] = {'type':'string', 'label':f'{sid} ({len(members)} panels) - unassigned',
                                          'x':0, 'y':0}
                added = True
        if added:
            self._diagram_layout_applied = None
            self._refresh_diagram_list()
            self.draw_grid()
        self._fit_diagram()
        if getattr(self, '_guard_ready', False):
            self._record_history()
        return result

    def _zoom_at_pointer(self, event, delta):
        if self._get_active_tab_index() not in (1, 7):
            return super()._zoom_at_pointer(event, delta)
        old = float(self.zoom_level)
        factor = 1.15 if delta > 0 else 1/1.15
        zoom_view(self, min(5., max(.03, old * factor)), event.x, event.y)
        return 'break'

    def _zoom_button_change(self, factor):
        if self._get_active_tab_index() not in (1, 7):
            return super()._zoom_button_change(factor)
        zoom_view(self, min(5., max(.03, self.zoom_level * factor)),
                  self.canvas.winfo_width()/2, self.canvas.winfo_height()/2)

    def _reset_zoom(self):
        if self._get_active_tab_index() not in (1, 7):
            return super()._reset_zoom()
        zoom_view(self, 1., self.canvas.winfo_width()/2, self.canvas.winfo_height()/2)

    def _fit_diagram(self):
        self._auto_fit = False
        if self._get_active_tab_index() != 7:
            return
        if self.canvas.winfo_width() < 5 or self.canvas.winfo_height() < 5:
            return
        self.draw_grid()
        if not self.diagram_nodes:
            return
        sizes = {key: self._diagram_node_size(key) for key in self.diagram_nodes}
        x0 = min(node['x'] - sizes[k][0] / 2 for k, node in self.diagram_nodes.items()) - 65
        y0 = min(node['y'] - sizes[k][1] / 2 for k, node in self.diagram_nodes.items()) - 80
        x1 = max(node['x'] + sizes[k][0] / 2 for k, node in self.diagram_nodes.items()) + 65
        y1 = max(node['y'] + sizes[k][1] / 2 for k, node in self.diagram_nodes.items()) + 50
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        self.zoom_level = max(.03, min(3., (width - 30) / max(1, x1 - x0),
                                         (height - 30) / max(1, y1 - y0)))
        self.draw_grid()
        place_viewport(self.canvas, (x0+x1)/2*self.zoom_level - width/2,
                      (y0+y1)/2*self.zoom_level - height/2)

    def _on_ribbon_tab_changed(self, event):
        active_idx = self._get_active_tab_index()
        previous_idx = getattr(self, '_navigation_previous_tab', None)
        # The main drawing surface is shared across tabs, but its camera is not.
        if previous_idx in (1, 7) and previous_idx != active_idx:
            center = viewport_center(self.canvas)
            setattr(self, '_view_camera_' + str(previous_idx),
                    (center[0]/max(.001, self.zoom_level),
                     center[1]/max(.001, self.zoom_level)))
        active = active_idx == 7
        was_active = getattr(self, '_diagram_tab_active', False)
        self._diagram_tab_active = active
        if active and not was_active:
            self._diagram_return_zoom = self.zoom_level
            self.zoom_level = getattr(self, '_diagram_view_zoom', 1.)
        elif was_active and not active:
            self._diagram_view_zoom = self.zoom_level
            self.zoom_level = getattr(self, '_diagram_return_zoom', 1.)
        self._navigation_previous_tab = active_idx
        result = super()._on_ribbon_tab_changed(event)
        if active_idx in (1, 7) and previous_idx != active_idx:
            # ttk sidebar packing changes the canvas width asynchronously.
            # Finalise geometry before restoring an anchored camera.
            self.canvas.update_idletasks()
            saved = getattr(self, '_view_camera_' + str(active_idx), None)
            if saved is not None:
                def restore_camera(tab=active_idx, world_center=saved):
                    if self._get_active_tab_index() == tab:
                        place_viewport(self.canvas,
                            world_center[0]*self.zoom_level - self.canvas.winfo_width()/2,
                            world_center[1]*self.zoom_level - self.canvas.winfo_height()/2)
                restore_camera()
                # ttk repacks the diagram sidebar after NotebookTabChanged.
                # Restore a second time once geometry negotiations settle.
                self.root.after_idle(restore_camera)
            elif active and self.diagram_nodes:
                # Fit only on first visit; do not repeat on every edit/tab switch.
                self.root.after_idle(lambda: self._fit_diagram()
                    if self._get_active_tab_index() == 7 else None)
            if active_idx == 1 and hasattr(self, '_refresh_installation_photo'):
                self._refresh_installation_photo()
        return result
