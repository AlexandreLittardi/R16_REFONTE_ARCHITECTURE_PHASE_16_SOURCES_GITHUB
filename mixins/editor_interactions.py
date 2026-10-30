"""Explicit desktop editor gestures, without left-button canvas panning conflicts."""
import tkinter as tk
from application.routing_commands import MoveRoutingArea
from ui.tab_ids import TabId
from ui.gesture_policy import LeftGesture, press_intent, drag_intent

class EditorInteractionsMixin:
    def on_left_press(self,event):
        idx=self._get_active_tab_index();x=self.canvas.canvasx(event.x);y=self.canvas.canvasy(event.y)
        intent=press_intent(idx, path_mode=self.path_mode,
            polygon_index=self.active_polygon_idx)
        if intent in (LeftGesture.INSTALLATION_POLYGON,LeftGesture.INSTALLATION_CANVAS):
            self._canvas_pan_start=None
            # Polygon is chosen in its list; drag vertices or its interior to transform it.
            if intent==LeftGesture.INSTALLATION_POLYGON:
                poly=self.roof_polygons[self.active_polygon_idx]
                self._polygon_vertex=next((i for i,p in enumerate(poly['points']) if abs(p[0]*self.zoom_level-x)<8 and abs(p[1]*self.zoom_level-y)<8),None)
                self._begin_canvas_edit('installation:routing-area')
                self.polygon_drag_mode='vertex' if self._polygon_vertex is not None else 'move'
                self.polygon_drag_start_pt=(x,y)
                self.polygon_drag_initial_points=[tuple(p) for p in poly['points']]
                return
            # Bypass only the pan wrapper, retaining the existing zone resize tool.
            from mixins.canvas_grid import CanvasGridMixin
            return CanvasGridMixin.on_left_press(self,event)
        # A left gesture edits objects; navigation uses the shared middle button.
        # This replaces the three passthrough handlers in WorkspaceImprovements.
        self._canvas_pan_start = None
        return super().on_left_press(event)

    def on_left_drag(self,event):
        intent=drag_intent(self._get_active_tab_index(),
            polygon_drag_mode=self.polygon_drag_mode,
            polygon_index=self.active_polygon_idx)
        if intent in (LeftGesture.INSTALLATION_POLYGON,LeftGesture.INSTALLATION_CANVAS):
            if intent==LeftGesture.INSTALLATION_POLYGON:
                x,y=self.polygon_drag_start_pt
                dx=(self.canvas.canvasx(event.x)-x)/self.zoom_level;dy=(self.canvas.canvasy(event.y)-y)/self.zoom_level
                command=MoveRoutingArea(self.active_polygon_idx,
                    tuple(tuple(p) for p in self.polygon_drag_initial_points),
                    dx,dy,vertex=getattr(self,'_polygon_vertex',None))
                updated,events=command.execute(self.roof_polygons)
                if updated is not None:
                    self.roof_polygons=updated
                    bus=getattr(self,'_project_events',None)
                    if bus is None:
                        self._invalidate_cable_routes()  # legacy standalone controllers
                    else:
                        for emitted in events:
                            bus.emit(emitted)
                    self.draw_grid()
                return
            from mixins.canvas_grid import CanvasGridMixin
            return CanvasGridMixin.on_left_drag(self,event)
        return super().on_left_drag(event)

    def on_left_release(self,event):
        previous=len(self.measures)
        try:
            if self._get_active_tab_index()==TabId.INSTALLATION:
                from mixins.canvas_grid import CanvasGridMixin
                result=CanvasGridMixin.on_left_release(self,event)
            else:
                result=super().on_left_release(event)
            if len(self.measures)>previous:
                self.measures[-1]['axis']=getattr(self,'dimension_mode','aligned');self.draw_grid()
            return result
        finally:
            # Every move, resize, routing-area drag or Ctrl paint stroke has
            # one before/after history boundary, even on early-return paths.
            self._finish_canvas_edit()

    def _on_diagram_list_select(self,event):
        self.diagram_selected_nodes={self._diagram_list_ids[i] for i in self.lst_diagram_nodes.curselection()}
        self.diagram_selected_node=next(iter(self.diagram_selected_nodes),None);self.draw_grid()

    def _delete_selected_diagram_node(self):
        from domain.diagram_commands import delete_nodes
        selected=getattr(self,'diagram_selected_nodes',set()) or {self.diagram_selected_node}
        edit=delete_nodes(self.diagram_nodes,self.diagram_links,selected)
        if not self._apply_diagram_edit(edit):
            return
        self.diagram_selected_nodes=set();self.diagram_selected_node=None
        self._refresh_diagram_list();self.draw_grid()

    def _on_zone_combo_selected(self,event):
        self.path_mode='select';self.roof_mode='select'
        return super()._on_zone_combo_selected(event)
