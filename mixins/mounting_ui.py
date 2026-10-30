"""Interactive mounting plan and transactional, live module configurator."""
import copy
import math
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from geometry_layout import inside
from mounting import (default_config, validate_config, axes, fixings, inverse,
                      transform, dimension_geometry, resize_fixings,
                      station_positions, set_fixing_position)
from mounting_drawing import geometry, dimension, draw_tk, write_svg, write_schedule
from mounting_plan_pdf import write_plan_pdf
from mounting_quantities import fixing_inventory, move_linked_stations
from mixins.mounting_edges_ui import MountingEdgesMixin
from mixins.mounting_view import MountingViewMixin
from mixins.mounting_chantier import MountingChantierMixin


class MountingMixin(MountingViewMixin,MountingEdgesMixin,MountingChantierMixin):
    def _build_mounting_tab(self):
        self.tab_mounting=ttk.Frame(self.ribbon_notebook,padding=5)
        self.ribbon_notebook.add(self.tab_mounting,text='Mounting')
        self.mounting_mode='select';self._mounting_pending=[]
        self._mounting_selected_dimension=None;self._mounting_selected_live_dimension=None
        self._mounting_selected_fixing=None
        self._mounting_drag=None;self._mounting_items={}
        self._mounting_menus={}

        def group(key,label):
            button=ttk.Menubutton(self.tab_mounting,text=label)
            menu=tk.Menu(button,tearoff=False)
            button.configure(menu=menu);button.pack(side='left',padx=4)
            self._mounting_menus[key]=menu
            return menu

        menu=group('selection','Selection')
        menu.add_command(label='Selection mode',command=lambda:self._set_mounting_mode('select'))
        menu.add_separator()
        menu.add_command(label='All modules',command=self._select_all_mounting)
        menu.add_command(label='Boundary modules',command=self._select_boundary_panels)

        menu=group('fixings','Clamps')
        menu.add_command(label='Configure mounting...',command=self._open_mounting_config)
        menu.add_command(label='Clamp footprint dimensions...',command=self._open_fixing_dimensions)
        menu.add_command(label='Edit selected clamp position...',command=self._edit_mounting_fixing)
        menu.add_separator()
        menu.add_cascade(label='Edges',menu=self._build_mounting_edges_menu(menu))
        menu.add_separator()
        menu.add_command(label='Remove mounting from selected modules',command=self._remove_mounting_config)

        menu=group('dimensions','Dimensions')
        for axis,label in (('aligned','Aligned'),('horizontal','Horizontal'),('vertical','Vertical')):
            menu.add_command(label='Dimension '+label.lower(),command=lambda a=axis:self._set_mounting_mode(a))
        menu.add_separator()
        menu.add_command(label='Dimension selected modules',command=self._mounting_auto_dimensions)
        menu.add_command(label='Dimension the selected clamp',command=self._mounting_dimension_fixing)
        menu.add_separator()
        menu.add_command(label='Edit dimension label...',accelerator='F2',command=self._mounting_edit_dimension_label)
        menu.add_command(label='Restore calculated label',command=self._mounting_reset_dimension_label)
        menu.add_command(label='Delete / hide selected dimension',accelerator='Delete',command=self._mounting_delete)
        menu.add_command(label='Show all hidden dimensions',command=self._mounting_restore_dimensions)

        menu=group('view','View')
        menu.add_command(label='Fit drawing',command=self._fit_mounting)
        menu.add_separator()
        menu.add_command(label='Zoom in',command=lambda:self._mounting_zoom(1.3))
        menu.add_command(label='Zoom out',command=lambda:self._mounting_zoom(1/1.3))

        menu=group('export','Export')
        menu.add_command(label='Full drawing PDF A3 (vector)',command=lambda:self._export_mounting('plan_pdf'))
        menu.add_command(label='Contact points per module (CSV)',command=lambda:self._export_mounting('csv'))
        menu.add_command(label='Physical clamp schedule (CSV)',command=lambda:self._export_mounting('bom'))
        menu.add_command(label='Physical clamp coordinates (CSV)',command=lambda:self._export_mounting('physical'))
        menu.add_command(label='Installation PDF package (A3)',command=lambda:self._export_mounting('pdf'))

        menu=group('site','Installation drawing')
        self._build_mounting_chantier_menu(menu)

        menu=group('edit','Edit')
        menu.add_command(label='Undo',accelerator='Ctrl+Z',command=self.undo_project,state='disabled')
        menu.add_command(label='Redo',accelerator='Ctrl+Y',command=self.redo_project,state='disabled')

    def _mounting_active(self):
        return hasattr(self,'tab_mounting') and self._get_active_tab_index()==self.ribbon_notebook.index(self.tab_mounting)

    def _build_main_area(self):
        super()._build_main_area()
        self.mounting_status=ttk.Label(self.canvas_frame,wraplength=1200,justify='left',padding=6)
        self._build_mounting_inspector()
        # UnifiedNavigationMixin owns the shared middle-button bindings.
        # Keep the legacy methods callable for compatibility/regression tests.
        self.canvas.bind('<Delete>',self._mounting_delete)
        self.canvas.bind('<BackSpace>',self._mounting_delete)
        self.canvas.bind('<F2>',self._mounting_edit_dimension_label)
        self.canvas.bind('<ButtonRelease-3>',self._mounting_context_menu,add='+')
        self.canvas.bind('<Double-Button-1>',self._mounting_double_click)
        self.canvas.bind('<Configure>',self._mounting_resize,add='+')

    def _mounting_resize(self,event=None):
        if self._mounting_active():
            self.mounting_status.configure(wraplength=max(260,self.canvas.winfo_width()-20))
            job=getattr(self,'_mounting_resize_job',None)
            if job:self.root.after_cancel(job)
            self._mounting_resize_job=self.root.after_idle(self._refresh_mounting_viewport)

    def _on_ribbon_tab_changed(self,event):
        active=self._mounting_active()
        if hasattr(self,'mounting_status'):
            if active:
                self.mounting_status.pack(side='bottom',fill='x',before=self.canvas)
                self.mounting_inspector.pack(side='bottom',fill='x',before=self.canvas)
            else:
                self.mounting_status.pack_forget()
                self.mounting_inspector.pack_forget()
        if not active:
            self._cancel_mounting_view_jobs()
            self._mounting_pending=[];self._mounting_drag=None
        result=super()._on_ribbon_tab_changed(event)
        if active:
            self.stats_frame.place_forget()
            if not getattr(self,'_mounting_visited',False):
                self._mounting_visited=True
                self.root.after_idle(lambda:self._fit_mounting() if self._mounting_active() else None)
        return result

    def draw_grid(self):
        if not self._mounting_active():return super().draw_grid()
        if hasattr(self,'canvas'):self._render_mounting_plan()

    def _mounting_ready(self):
        if self.px_per_mm<=0 or not self.roof_zones:
            messagebox.showinfo('Mounting','Calibrate the drawing and define roof areas in Installation Area, then place the modules in Layout.',parent=self.root)
            return False
        return True

    def _mounting_update_status(self):
        if not hasattr(self,'mounting_status'):return
        configured=sum(bool(i['config']) for i in self._mounting_items.values())
        count=sum(len(i['fixings']) for i in self._mounting_items.values())
        if self.px_per_mm<=0 or not self.roof_zones:
            text='Calibrate the drawing and define installation areas to show dimensions in mm.'
        elif self.mounting_mode=='origin':
            text='Site datum: click a point on the drawing (snaps to module corners within 10 px). Esc to cancel.'
        elif self.mounting_mode!='select':
            text=('Dimensioning: '+('1. Click the first point.' if not self._mounting_pending else
                '2. Click the second point.' if len(self._mounting_pending)==1 else '3. Click the dimension label position.')+
                ' Snapping: corners and clamp centers. Esc: cancel.')
        else:
            text=(f'{configured}/{len(self.panels)} modules configured · {count} clamp contact points · '
                  f'{len(self.selected_panel_coords)} selected · Click / Shift+click: select; drag a clamp: adjust; middle-drag: pan.')
            if len(self.selected_panel_coords)==1:
                chosen=next((i for i in self._mounting_items.values() if i['coord'] in self.selected_panel_coords),None)
                if chosen and chosen['config'] and chosen['config'].get('top_offsets_mm') is not None:
                    if math.dist(chosen['poly'][0],chosen['poly'][3])*self.zoom_level<155:
                        text+=' Zoom in on the selected module to see dimensions A/B/C.'
            if self._mounting_selected_live_dimension is not None:
                text+=' Selected dimension: F2 to edit text, Delete to hide (geometry unchanged).'
            elif self._mounting_selected_dimension is not None:
                text+=' Selected dimension: F2 to edit text, Delete to remove (geometry unchanged).'
            if self._mounting_selected_fixing:
                uid,index=self._mounting_selected_fixing
                item=self._mounting_items.get(uid)
                if item and index<len(item['fixings']):
                    text+=f" P{item['number']} / F{index+1} : {item['fixings'][index]['position_mm']:.1f} mm from the start of the clamped edge."
                    f=item['fixings'][index]
                    text+=f" Actual footprint: {f['length_mm']:g} x {f['width_mm']:g} mm."
                    if f['kind']!='standard':text+=f" {f['reference']} ({'manual' if f['forced'] else 'automatic'})."
        rules=self.mounting_plan.get('edge_rules',{})
        if rules.get('enabled') and self.px_per_mm>0:
            inventory=getattr(self,'_mounting_inventory',None) or fixing_inventory(self._mounting_items,self.px_per_mm,rules.get('max_gap_mm',50))
            text+=(f" Physical clamps: end {inventory['pieces_by_kind'].get('edge',0)}, "
                   f"intermediate {inventory['pieces_by_kind'].get('intermediate',0)}, "
                   f"total {inventory['pieces_total']} ({inventory['points_total']} contacts).")
        if any(i['issue'] for i in self._mounting_items.values()):text+=' Module dimensions changed: reconfigure the flagged modules!'
        self.mounting_status.configure(text=text)
        self._mounting_sync_inspector()

    def _set_mounting_mode(self,mode):
        if mode!='select' and not self._mounting_ready():return
        self.mounting_mode=mode;self._mounting_pending=[];self._mounting_drag=None
        self._mounting_selected_dimension=None;self._mounting_selected_live_dimension=None
        self.canvas.configure(cursor='' if mode=='select' else 'crosshair')
        self.draw_grid()

    def _select_all_mounting(self):
        self.selected_panel_coords=set(self.panels);self._set_mounting_mode('select')

    def _mounting_point(self,event):
        return (self.canvas.canvasx(event.x)/self.zoom_level,self.canvas.canvasy(event.y)/self.zoom_level)

    def _mounting_snap(self,point):
        candidates=[]
        for uid,item in self._mounting_items.items():
            for index,p in enumerate(item['poly']):candidates.append((p,dict(uid=uid,kind='corner',index=index)))
            for f in item['fixings']:
                candidates.append((f['point'],dict(uid=uid,kind='fixing',index=f['index'])))
                for index,p in enumerate(f['world_polygon']):
                    candidates.append((p,dict(uid=uid,kind='fixing_corner',index=f['index']*4+index)))
        best=min(candidates,key=lambda pair:math.dist(pair[0],point),default=None)
        return best if best and math.dist(best[0],point)*self.zoom_level<=10 else (point,None)

    def _mounting_hit_fixing(self,point):
        # A shared clamp has one footprint centered on the joint. Hit-testing
        # the old per-panel footprints misses that center at high zoom.
        inventory=getattr(self,'_mounting_inventory',None)
        if inventory:
            hits=[]
            preferred=self.selected_panel_coords
            for piece in inventory['physical_fixings']:
                if inside(point,piece['world_polygon']):
                    for uid,index in piece['contacts']:
                        rank=0 if self._mounting_items[uid]['coord'] in preferred else 1
                        hits.append((rank,math.dist(piece['point'],point),uid,index))
            if hits:
                _,_,uid,index=min(hits)
                return uid,index
        hits=[(math.dist(f['point'],point),uid,f['index']) for uid,item in self._mounting_items.items()
              for f in item['fixings'] if inside(point,f['world_polygon'])]
        if hits:
            best=min(hits);return best[1],best[2]
        candidates=[(math.dist(f['point'],point),uid,f['index']) for uid,item in self._mounting_items.items() for f in item['fixings']]
        best=min(candidates,default=None)
        return (best[1],best[2]) if best and best[0]*self.zoom_level<=10 else None

    def _mounting_move_station(self,uid,index,value):
        """Commit compatible paired clamp positions together, or none at all."""
        plan=move_linked_stations(self._mounting_items,self.mounting_plan,
            getattr(self,'_mounting_inventory',None) or {'shared_pairs':[]},uid,index,value)
        # Validate the complete scene before changing the app state. A failed
        # paired edit must not desynchronize the shared physical clamp.
        proposed=geometry(self,plan)
        problems=[i['issue'] for i in proposed.values() if i['issue']]
        if problems:raise ValueError(problems[0])
        old_pairs={frozenset((p['a'],p['b'])) for p in
                   (getattr(self,'_mounting_inventory',None) or {}).get('shared_pairs',[])}
        if old_pairs:
            rules=plan.get('edge_rules') or {}
            newer=fixing_inventory(proposed,self.px_per_mm,rules.get('max_gap_mm',50))
            current={frozenset((p['a'],p['b'])) for p in newer['shared_pairs']}
            if not old_pairs.issubset(current):
                raise ValueError('The new position would split a shared clamp.')
        self.mounting_plan=plan

    def on_left_press(self,event):
        if not self._mounting_active():return super().on_left_press(event)
        self.canvas.focus_set();point=self._mounting_point(event)
        if self.mounting_mode=='origin':
            self._mounting_define_origin(point);return 'break'
        if self.mounting_mode!='select':
            if len(self._mounting_pending)<2:
                snapped,ref=self._mounting_snap(point)
                if self._mounting_pending:
                    _,_,length=dimension_geometry(self._mounting_pending[0][0],snapped,point,self.mounting_mode)
                    if length<1e-8:return 'break'
                self._mounting_pending.append((snapped,ref));self._mounting_update_status()
            else:
                (p1,r1),(p2,r2)=self._mounting_pending
                self.mounting_plan['dimensions'].append(dict(p1=p1,p2=p2,ref1=r1,ref2=r2,label=point,axis=self.mounting_mode))
                self._mounting_pending=[];self.draw_grid()
            return 'break'
        self._mounting_selected_dimension=None;self._mounting_selected_live_dimension=None
        self._mounting_drag=None
        self._mounting_press_screen=(event.x,event.y);self._mounting_drag_started=False
        # Shift is exclusively a panel-selection gesture, including over a
        # fixing footprint or a dimension. Never arm a geometry edit here.
        if event.state & 0x0001:
            self._mounting_selected_fixing=None
            coord=next((i['coord'] for i in reversed(list(self._mounting_items.values())) if inside(point,i['poly'])),None)
            if coord is None:
                hit=self._mounting_hit_fixing(point)
                if hit:coord=self._mounting_items[hit[0]]['coord']
            if coord is not None:
                if coord in self.selected_panel_coords:self.selected_panel_coords.remove(coord)
                else:self.selected_panel_coords.add(coord)
            self.draw_grid();return 'break'
        hit=self._mounting_hit_fixing(point)
        self._mounting_selected_fixing=hit
        if hit:
            self._record_history()
            uid,index=hit;item=self._mounting_items[uid]
            self.selected_panel_coords={item['coord']}
            config=copy.deepcopy(self.mounting_plan['panels'][uid])
            local=inverse(item['poly'],config['width_mm'],config['height_mm'],point)
            along_y=axes(config)[2]
            offset=local[1 if along_y else 0]-item['fixings'][index]['position_mm']
            self._mounting_drag=('fixing',hit,config,offset)
        else:
            self._mounting_select_dimension_at(event,allow_drag=True)
            if self._mounting_selected_dimension is None and self._mounting_selected_live_dimension is None:
                coord=next((i['coord'] for i in reversed(list(self._mounting_items.values())) if inside(point,i['poly'])),None)
                self.selected_panel_coords={coord} if coord is not None else set()
        self.draw_grid();return 'break'

    def _mounting_select_dimension_at(self,event,allow_drag=False):
        # Canvas coordinates are scroll-aware; look for annotation and live
        # dimension tags on lines, arrowheads, labels *and white label plates*.
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        overlaps=self.canvas.find_overlapping(x-5,y-5,x+5,y+5)
        for ident in reversed(overlaps):
            tags=self.canvas.gettags(ident)
            saved=next((t for t in tags if t.startswith('dimension:')),None)
            live=next((t for t in tags if t.startswith('live-dimension:')),None)
            if saved is not None:
                index=int(saved.split(':',1)[1])
                if not 0<=index<len(self.mounting_plan['dimensions']):continue
                self._mounting_selected_dimension=index
                self._mounting_selected_live_dimension=None
                if allow_drag:
                    self._record_history()
                    self._mounting_drag=('dimension',index,None)
                return True
            if live is not None:
                self._mounting_selected_dimension=None
                self._mounting_selected_live_dimension=live.split(':',1)[1]
                self._mounting_selected_fixing=None
                return True
        return False

    def _mounting_context_menu(self,event):
        if not self._mounting_active():return
        if getattr(self,'_mounting_right_start',None) is None:return 'break'
        start=self._mounting_right_start;self._mounting_right_start=None
        if math.dist(start,(event.x,event.y))>5:return 'break'  # right-drag pans
        self._mounting_selected_dimension=None;self._mounting_selected_live_dimension=None
        self._mounting_select_dimension_at(event)
        self._draw_mounting_annotations();self._mounting_update_status()
        menu=tk.Menu(self.canvas,tearoff=False)
        has_dimension=(self._mounting_selected_dimension is not None or
                       self._mounting_selected_live_dimension is not None)
        menu.add_command(label='Edit label...',command=self._mounting_edit_dimension_label,
                         state='normal' if has_dimension else 'disabled')
        menu.add_command(label='Restore calculated label',command=self._mounting_reset_dimension_label,
                         state='normal' if has_dimension else 'disabled')
        menu.add_separator()
        menu.add_command(label='Delete / hide this dimension',command=self._mounting_delete,
                         state='normal' if has_dimension else 'disabled')
        menu.add_command(label='Show hidden dimensions',command=self._mounting_restore_dimensions,
                         state='normal' if self.mounting_plan.get('hidden_dimensions') else 'disabled')
        try:menu.tk_popup(event.x_root,event.y_root)
        finally:menu.grab_release()
        return 'break'

    def on_left_drag(self,event):
        if not self._mounting_active():return super().on_left_drag(event)
        point=self._mounting_point(event)
        if self._mounting_drag:
            if not self._mounting_drag_started:
                if math.dist((event.x,event.y),self._mounting_press_screen)<4:return 'break'
                self._mounting_drag_started=True
            kind,target,original=self._mounting_drag[:3]
            if kind=='dimension':self.mounting_plan['dimensions'][target]['label']=point
            else:
                uid,index=target;item=self._mounting_items[uid];c=copy.deepcopy(original)
                x,y=inverse(item['poly'],c['width_mm'],c['height_mm'],point)
                length,_,along_y=axes(c)
                position=(y if along_y else x)-self._mounting_drag[3]
                half=item['fixings'][index]['length_mm']/2
                value=round(max(half,min(length-half,position)),1)
                try:self._mounting_move_station(uid,index,value)
                except ValueError:return 'break'
            self.draw_grid()
        return 'break'

    def on_left_release(self,event):
        if not self._mounting_active():return super().on_left_release(event)
        self._mounting_drag=None;self._queue_history();return 'break'

    def _on_canvas_motion(self,event):
        if not self._mounting_active():return super()._on_canvas_motion(event)
        self.canvas.delete('mounting_preview')
        if self.px_per_mm>0 and hasattr(self,'_mounting_cursor_label'):
            from mounting_drawing import site_origin
            origin,confirmed=site_origin(self,getattr(self,'_mounting_items',{}))
            px=self._mounting_point(event)
            self._mounting_cursor_label.configure(text=f"Souris : X {(px[0]-origin[0])/self.px_per_mm:.1f} / Y {(px[1]-origin[1])/self.px_per_mm:.1f} mm")
        if self.mounting_mode=='select':return
        point,ref=self._mounting_snap(self._mounting_point(event))
        shapes=[]
        if self._mounting_pending:
            p1=self._mounting_pending[0][0]
            if len(self._mounting_pending)==1:
                shapes=[dict(kind='line',points=[p1,point],color='#111111',width=2)]
            else:
                dimension(shapes,p1,self._mounting_pending[1][0],self._mounting_point(event),self.mounting_mode,self.px_per_mm,11/self.zoom_level,'#111111')
        if ref:shapes.append(dict(kind='cross',point=point,size=6/self.zoom_level,color='#333333'))
        before=set(self.canvas.find_all());draw_tk(self.canvas,shapes,self.zoom_level)
        for ident in set(self.canvas.find_all())-before:self.canvas.addtag_withtag('mounting_preview',ident)

    def _on_escape_key(self,event=None):
        if self._mounting_active():
            self._set_mounting_mode('select');return 'break'
        return super()._on_escape_key(event)

    def _mounting_pan_start(self,event):
        if self._mounting_active():self.canvas.scan_mark(event.x,event.y)

    def _mounting_pan_drag(self,event):
        if self._mounting_active():
            self.canvas.scan_dragto(event.x,event.y,gain=1)
            self._set_mounting_viewport(self.canvas.canvasx(0),self.canvas.canvasy(0))
            self._mounting_background(fast=True);self._draw_mounting_legend();self._schedule_mounting_image_quality()

    def on_right_press(self,event):
        if self._mounting_active():
            self._mounting_right_start=(event.x,event.y)
            return 'break'
        return super().on_right_press(event)

    def on_right_drag(self,event):
        if self._mounting_active():return 'break'
        return super().on_right_drag(event)

    def _zoom_at_pointer(self,event,delta):
        if self._mounting_active():return self._queue_mounting_zoom(1.2 if delta>0 else 1/1.2,event)
        return super()._zoom_at_pointer(event,delta)

    def _mounting_dimension_default_label(self):
        # The displayed text is computed from the current geometry; changing
        # its presentation must never modify an endpoint, an offset or a fixing.
        index=self._mounting_selected_dimension
        if index is not None and 0<=index<len(self.mounting_plan['dimensions']):
            from mounting_drawing import resolve_point
            d=self.mounting_plan['dimensions'][index]
            a=resolve_point(d,1,self._mounting_items)
            b=resolve_point(d,2,self._mounting_items)
            if a is None or b is None:return 'Missing reference'
            return f'{dimension_geometry(a,b,d["label"],d["axis"])[2]/self.px_per_mm:.1f} mm'
        live=self._mounting_selected_live_dimension
        if live is None:return None
        from mounting_drawing import construction_shapes
        plan=dict(self.mounting_plan,hidden_dimensions=[],dimension_labels={})
        shapes=construction_shapes(self,self._mounting_items,font=11/self.zoom_level,
            selected=self.selected_panel_coords,selected_fixing=self._mounting_selected_fixing,
            plan=plan)
        return next((s['text'] for s in shapes if s.get('dim_id')==live and s['kind']=='text'),None)

    def _mounting_edit_dimension_label(self,event=None):
        if not self._mounting_active():return
        index=self._mounting_selected_dimension
        live=self._mounting_selected_live_dimension
        if index is None and live is None:return 'break'
        computed=self._mounting_dimension_default_label()
        if index is not None:
            d=self.mounting_plan['dimensions'][index]
            current=d.get('text_override',computed)
        else:
            current=self.mounting_plan.setdefault('dimension_labels',{}).get(live,computed)
        result=simpledialog.askstring('Dimension label',
            'Displayed text (160 characters maximum).\nGeometry and installation values are NOT changed.\n'
            'Leave blank to restore the calculated value.',
            initialvalue=current or '',parent=self.root)
        if result is None:return 'break'
        value=result.strip()
        if len(value)>160 or any(ch in value for ch in '\r\n\x00'):
            messagebox.showerror('Invalid label','Enter a single line (160 characters maximum).',parent=self.root)
            return 'break'
        if (index is not None and (value or None)==self.mounting_plan['dimensions'][index].get('text_override')
            or live is not None and value==self.mounting_plan.get('dimension_labels',{}).get(live,'')):
            return 'break'
        self._record_history()
        if index is not None:
            d=self.mounting_plan['dimensions'][index]
            if value:d['text_override']=value
            else:d.pop('text_override',None)
        else:
            labels=self.mounting_plan.setdefault('dimension_labels',{})
            if value:labels[live]=value
            else:labels.pop(live,None)
        self._draw_mounting_annotations();self._mounting_update_status();self._queue_history()
        return 'break'

    def _mounting_reset_dimension_label(self,event=None):
        if not self._mounting_active():return
        index=self._mounting_selected_dimension;live=self._mounting_selected_live_dimension
        if index is not None and 'text_override' in self.mounting_plan['dimensions'][index]:
            self._record_history();self.mounting_plan['dimensions'][index].pop('text_override',None)
        elif live is not None and live in self.mounting_plan.get('dimension_labels',{}):
            self._record_history();self.mounting_plan['dimension_labels'].pop(live,None)
        else:return 'break'
        self._draw_mounting_annotations();self._mounting_update_status();self._queue_history()
        return 'break'

    def _mounting_delete(self,event=None):
        if not self._mounting_active():return
        index=self._mounting_selected_dimension
        live=self._mounting_selected_live_dimension
        if index is None and live is None:return 'break'
        self._record_history()
        if index is not None and 0<=index<len(self.mounting_plan['dimensions']):
            del self.mounting_plan['dimensions'][index]
        elif live is not None:
            hidden=self.mounting_plan.setdefault('hidden_dimensions',[])
            if live not in hidden:hidden.append(live)
        self._mounting_selected_dimension=None;self._mounting_selected_live_dimension=None
        self.draw_grid();self._queue_history();return 'break'

    def _mounting_restore_dimensions(self):
        if not self._mounting_active():return
        if not self.mounting_plan.get('hidden_dimensions'):return
        self._record_history()
        self.mounting_plan['hidden_dimensions']=[]
        self._mounting_selected_live_dimension=None
        self.draw_grid();self._queue_history()

    def _remove_mounting_config(self):
        for coord in self.selected_panel_coords:self.mounting_plan['panels'].pop(self.panel_uids.get(coord),None)
        self._mounting_selected_fixing=None;self._mounting_selected_live_dimension=None;self.draw_grid()

    def _edit_mounting_fixing(self):
        if not self._mounting_selected_fixing:
            messagebox.showinfo('Clamp','Click a clamp on the drawing.',parent=self.root);return
        uid,index=self._mounting_selected_fixing
        if uid not in self._mounting_items or not self._mounting_items[uid]['config']:return
        c=copy.deepcopy(self.mounting_plan['panels'][uid]);f=fixings(c)[index]
        pair=c['count']==6 and c.get('top_offsets_mm') is not None
        axis='top edge of the module' if axes(c)[2] else 'left edge of the module'
        station='ABC'[index//2] if pair else f'F{index+1}'
        value=simpledialog.askfloat('Clamp position',
            f'{station} : distance from the {axis} (mm)' + (' ; moves the left/right pair' if pair else ''),
            initialvalue=f['position_mm'],parent=self.root)
        if value is None:return
        try:self._mounting_move_station(uid,index,value)
        except ValueError as exc:messagebox.showerror('Invalid position',str(exc),parent=self.root);return
        self.draw_grid()

    def _mounting_double_click(self,event):
        if not self._mounting_active() or self.mounting_mode!='select':return
        # Tk dispatches Double-Button instead of the second ButtonPress.
        if event.state & 0x0001:return self.on_left_press(event)
        # Always re-hit-test: Tk does not guarantee a second ButtonPress event
        # for a double-click, and the selected dimension may be stale.
        self._mounting_select_dimension_at(event)
        if (self._mounting_selected_dimension is not None or
                self._mounting_selected_live_dimension is not None):
            self._mounting_edit_dimension_label()
        elif self._mounting_selected_fixing:self._edit_mounting_fixing()
        else:self._open_mounting_config()
        return 'break'

    def _mounting_auto_dimensions(self):
        if not self._mounting_ready():return
        if not self.selected_panel_coords:
            messagebox.showinfo('Dimensions','Select at least one module.',parent=self.root);return
        for uid,item in self._mounting_items.items():
            if item['coord'] not in self.selected_panel_coords or not item['config'] or item['issue']:continue
            c=item['config'];length,cross,along_y=axes(c)
            offset=120
            # In ABC mode the 3 saved associative dimensions are each from
            # the upper edge, with no ambiguity about consecutive gaps.
            if c['count']==6 and c.get('top_offsets_mm') is not None and along_y:
                for j,name in enumerate('ABC'):
                    f=item['fixings'][j*2]
                    r1=dict(uid=uid,kind='corner',index=0)
                    r2=dict(uid=uid,kind='fixing',index=f['index'])
                    if any(d.get('auto')=='abc-top' and d.get('ref1')==r1 and d.get('ref2')==r2
                           for d in self.mounting_plan['dimensions']):continue
                    p1=item['poly'][0];p2=f['point']
                    label=transform(item['poly'],c['width_mm'],c['height_mm'],(-180-80*j,f['position_mm']/2))
                    self.mounting_plan['dimensions'].append(dict(p1=p1,p2=p2,ref1=r1,ref2=r2,
                        label=label,axis='aligned',auto='abc-top'))
                continue
            # Dimension the actual positions, including independent manual edits.
            for side in range(2):
                fs=[f for f in item['fixings'] if f['side']==side]
                start=(side*cross,0) if along_y else (0,side*cross)
                end=(side*cross,length) if along_y else (length,side*cross)
                endpoints=([(transform(item['poly'],c['width_mm'],c['height_mm'],start),
                            dict(uid=uid,kind='corner',index=(side if along_y else side*3)))]+
                           [(f['point'],dict(uid=uid,kind='fixing',index=f['index'])) for f in fs]+
                           [(transform(item['poly'],c['width_mm'],c['height_mm'],end),
                             dict(uid=uid,kind='corner',index=(3-side if along_y else 1+side)))])
                for (p1,r1),(p2,r2) in zip(endpoints,endpoints[1:]):
                    # Avoid duplicates on repeated command use.
                    if any(d.get('auto') and d.get('ref1')==r1 and d.get('ref2')==r2 for d in self.mounting_plan['dimensions']):continue
                    local1=inverse(item['poly'],c['width_mm'],c['height_mm'],p1)
                    local2=inverse(item['poly'],c['width_mm'],c['height_mm'],p2)
                    mid=tuple((local1[i]+local2[i])/2 for i in (0,1))
                    label_local=(side*cross+(-offset if side==0 else offset),mid[1]) if along_y else (mid[0],side*cross+(-offset if side==0 else offset))
                    self.mounting_plan['dimensions'].append(dict(p1=p1,p2=p2,ref1=r1,ref2=r2,
                        label=transform(item['poly'],c['width_mm'],c['height_mm'],label_local),axis='aligned',auto=True))
        self.draw_grid()

    def _export_mounting(self,kind):
        if not self._mounting_ready():return
        extension='csv' if kind in ('bom','physical') else 'pdf' if kind=='plan_pdf' else kind
        name='_nomenclature' if kind=='bom' else '_pinces_physiques' if kind=='physical' else '_montage'
        path=filedialog.asksaveasfilename(parent=self.root,title='Export mounting drawing',defaultextension='.'+extension,
            initialfile=self.project_name+name+'.'+extension,filetypes=[(extension.upper(),'*.'+extension)])
        if not path:return
        try:
            if kind=='bom':
                from mounting_quantities import write_inventory_csv
                write_inventory_csv(self,path)
            elif kind=='physical':
                from mounting_quantities import write_physical_schedule_csv
                write_physical_schedule_csv(self,path)
            elif kind=='plan_pdf':
                write_plan_pdf(self,path)
            elif kind=='pdf':
                from mounting_installer import write_installer_pdf
                write_installer_pdf(self,path)
            else:(write_svg if kind=='svg' else write_schedule)(self,path)
        except Exception as exc:messagebox.showerror('Export failed',str(exc),parent=self.root);return
        messagebox.showinfo('Export complete','Mounting file saved.',parent=self.root)

    def _mounting_dimension_fixing(self):
        selected=self._mounting_selected_fixing
        if not selected:
            messagebox.showinfo('Dimension a clamp','Select a clamp on the drawing.',parent=self.root);return
        uid,index=selected;item=self._mounting_items.get(uid)
        if not item or index>=len(item['fixings']):return
        points=item['fixings'][index]['world_polygon']
        for a,b in ((0,1),(1,2)):
            ref1=dict(uid=uid,kind='fixing_corner',index=index*4+a)
            ref2=dict(uid=uid,kind='fixing_corner',index=index*4+b)
            if any(d.get('auto')=='fixing-size' and d.get('ref1')==ref1 and d.get('ref2')==ref2 for d in self.mounting_plan['dimensions']):continue
            p1,p2=points[a],points[b];length=math.dist(p1,p2)
            normal=(-(p2[1]-p1[1])/length,(p2[0]-p1[0])/length)
            label=tuple((p1[i]+p2[i])/2-24/self.zoom_level*normal[i] for i in (0,1))
            self.mounting_plan['dimensions'].append(dict(p1=p1,p2=p2,ref1=ref1,ref2=ref2,
                                                        label=label,axis='aligned',auto='fixing-size'))
        self.draw_grid()

    def _open_fixing_dimensions(self):
        if not self._mounting_ready():return
        if self.mounting_plan.get('edge_rules',{}).get('enabled'):
            self._open_mounting_edges();return
        configured={uid:item for uid,item in self._mounting_items.items() if item['config']}
        if not configured:
            self._open_mounting_config();return
        existing=getattr(self,'_mounting_size_dialog',None)
        if existing and existing.winfo_exists():existing.lift();return
        selected=[uid for uid,item in configured.items() if item['coord'] in self.selected_panel_coords]
        base=copy.deepcopy(configured[selected[0] if selected else next(iter(configured))]['config'])
        win=tk.Toplevel(self.root);self._mounting_size_dialog=win
        win.title('Actual clamp footprint');win.transient(self.root);win.grab_set()
        body=ttk.Frame(win,padding=12);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Clamp footprint on drawing',font=('Arial',13,'bold')).pack(anchor='w')
        ttk.Label(body,text='Lf: length parallel to the clamped edge. lf: width perpendicular to it.\nThe gray rectangle shows the actual footprint at the same scale as the module.',justify='left').pack(anchor='w',pady=7)
        form=ttk.Frame(body);form.pack(fill='x')
        variables={}
        for i,(key,label) in enumerate((('clamp_length_mm','Length Lf (mm)'),('clamp_width_mm','Width lf (mm)'))):
            ttk.Label(form,text=label).grid(row=0,column=i*2,padx=6,pady=5,sticky='w')
            var=tk.StringVar(value=f'{base[key]:g}');variables[key]=var
            ttk.Entry(form,textvariable=var,width=12).grid(row=0,column=i*2+1,padx=6,pady=5)
        previews=ttk.Frame(body);previews.pack(fill='both',expand=True,pady=10)
        previews.columnconfigure(0,weight=1);previews.columnconfigure(1,weight=1);previews.rowconfigure(1,weight=1)
        canvases=[]
        for i,title in enumerate(('Mounting: clamp and module at the same scale','Enlarged detail: clamp footprint')):
            ttk.Label(previews,text=title).grid(row=0,column=i,sticky='w',padx=6)
            cv=tk.Canvas(previews,background='#ffffff',highlightthickness=1,highlightbackground='#aaaaaa',width=380,height=320)
            cv.grid(row=1,column=i,sticky='nsew',padx=6,pady=5);canvases.append(cv)
        status=ttk.Label(body,wraplength=1000,justify='left');status.pack(fill='x',pady=5)
        ttk.Label(body,text='Changing these dimensions preserves offsets A/B, the clamp count and their positions on the drawing.\nDimensions are saved in the project and used in the drawing and PDF/CSV exports.',wraplength=1000,justify='left').pack(fill='x',pady=6)
        buttons=ttk.Frame(body);buttons.pack(fill='x');apply_buttons=[];last={}

        def render(*args):
            for cv in canvases:cv.delete('all')
            last.clear()
            try:
                c=copy.deepcopy(base)
                for key,var in variables.items():c[key]=float(var.get().replace(',','.'))
                c=validate_config(c);last['config']=c
            except (ValueError,TypeError) as exc:
                status.configure(text=str(exc),foreground='#333333')
                for button in apply_buttons:button.state(['disabled'])
                return
            for button in apply_buttons:button.state(['!disabled'])
            if not selected:apply_buttons[0].state(['disabled'])
            w,h=c['width_mm'],c['height_mm'];cv=canvases[0]
            local_fixings=fixings(c)
            shapes=[dict(kind='polygon',points=[(0,0),(w,0),(w,h),(0,h)],fill='#ffffff',color='#111111',width=2)]
            shapes += [dict(kind='polygon',points=f['polygon'],fill='#888888',color='#111111',width=1) for f in local_fixings]
            points=[(0,0),(w,h)]+[p for f in local_fixings for p in f['polygon']]
            left,top=min(p[0] for p in points),min(p[1] for p in points)
            right,bottom=max(p[0] for p in points),max(p[1] for p in points)
            z=min(max(10,cv.winfo_width()-60)/(right-left),max(10,cv.winfo_height()-60)/(bottom-top))
            offset=(cv.winfo_width()/2-(left+right)/2*z,cv.winfo_height()/2-(top+bottom)/2*z)
            draw_tk(cv,shapes,z,offset)
            # Enlarged detail has its own view scale; dimensions remain in mm.
            cv=canvases[1];length,width=c['clamp_length_mm'],c['clamp_width_mm']
            z=min(max(10,cv.winfo_width()-180)/length,max(10,cv.winfo_height()-160)/width)
            offset=((cv.winfo_width()-length*z)/2,(cv.winfo_height()-width*z)/2)
            shapes=[dict(kind='polygon',points=[(0,0),(length,0),(length,width),(0,width)],fill='#888888',color='#111111',width=2)]
            dimension(shapes,(0,0),(length,0),(length/2,-35/z),'aligned',1,11/z)
            dimension(shapes,(length,0),(length,width),(length+45/z,width/2),'aligned',1,11/z)
            draw_tk(cv,shapes,z,offset)
            status.configure(text=f'Actual footprint: {length:g} x {width:g} mm. The clamp keeps this footprint on the drawing and follows zoom and module rotation.',foreground='#222222')

        def apply(all_panels):
            if 'config' not in last:return
            c=last['config'];targets=list(configured) if all_panels else selected
            try:
                updated=resize_fixings(self.mounting_plan,targets,c['clamp_length_mm'],c['clamp_width_mm'])
            except ValueError as exc:
                status.configure(text=str(exc),foreground='#333333');return
            self._record_history();self.mounting_plan=updated
            win.destroy();self.draw_grid();self._record_history()

        for label,all_panels in ((f'Apply to selection ({len(selected)})',False),(f'Apply to all ({len(configured)})',True)):
            button=ttk.Button(buttons,text=label,command=lambda a=all_panels:apply(a));button.pack(side='left',padx=4);apply_buttons.append(button)
        ttk.Button(buttons,text='Cancel',command=win.destroy).pack(side='right')
        for var in variables.values():var.trace_add('write',render)
        for cv in canvases:cv.bind('<Configure>',render)
        self._fit_dialog(win,1120,700);win.after_idle(render)

    def _open_mounting_config(self):
        if not self._mounting_ready() or not self.panels:return
        existing=getattr(self,'_mounting_dialog',None)
        if existing and existing.winfo_exists():existing.lift();return
        selected=[i for i in self._mounting_items.values() if i['coord'] in self.selected_panel_coords]
        config=copy.deepcopy(next((i['config'] for i in selected if i['config']),None) or self.mounting_plan.get('template') or default_config(self.panel_width_mm,self.panel_height_mm))
        config.update(width_mm=self.panel_width_mm,height_mm=self.panel_height_mm)
        config['positions']={}
        win=tk.Toplevel(self.root);self._mounting_dialog=win;win.title('Mounting — clamp settings')
        win.transient(self.root);win.grab_set()
        content=ttk.Frame(win,padding=12);content.pack(fill='both',expand=True)
        ttk.Label(content,text=f'Project module: {self.panel_width_mm:g} × {self.panel_height_mm:g} mm',font=('Arial',12,'bold')).pack(anchor='w')
        help_text=tk.StringVar(master=win)
        ttk.Label(content,textvariable=help_text,justify='left',wraplength=1000).pack(anchor='w',pady=6)
        edge_active=self.mounting_plan.get('edge_rules',{}).get('enabled',False)
        if edge_active:
            ttk.Label(content,text='Active sizes depend on end/intermediate clamp types, configured under Clamps / Edges. The Lf/lf fields below apply to uniform mode.',wraplength=1000).pack(anchor='w')
        form=ttk.Frame(content);form.pack(fill='x');variables={}
        fields=[('a_mm','A (mm)'),('b_mm','B (mm)'),('clamp_length_mm','Clamp length Lf (mm)'),('clamp_width_mm','Clamp width lf (mm)')]
        for j,(key,label) in enumerate(fields):
            field_label=ttk.Label(form,text=label)
            field_label.grid(row=j//2,column=(j%2)*2,sticky='w',padx=5,pady=3)
            var=tk.StringVar(value=f'{config[key]:g}');variables[key]=var
            entry=ttk.Entry(form,textvariable=var,width=12)
            entry.grid(row=j//2,column=(j%2)*2+1,sticky='ew',padx=5,pady=3)
            var._entry=entry
            var._label=field_label
        # Six points = three independent vertical station positions, each
        # measured from the *same upper edge*, A / B / C (not three gaps).
        abc_frame=ttk.Frame(content);abc_frame.pack(fill='x',pady=(3,5))
        initial_offsets=station_positions(config)
        if config['count'] != 6:
            length,_,_=axes(config)
            initial_offsets=[config['a_mm'],length/2,length-config['b_mm']]
        abc_vars={}
        for j,name in enumerate('ABC'):
            ttk.Label(abc_frame,text=f'{name} — from top (mm)').grid(row=0,column=j*2,sticky='w',padx=5)
            var=tk.StringVar(master=win,value=f'{initial_offsets[j]:.1f}')
            abc_vars[name]=var
            ttk.Entry(abc_frame,textvariable=var,width=12).grid(row=0,column=j*2+1,sticky='w',padx=(0,16))
        edge=tk.StringVar(value='Long sides' if config['edge']=='long' else 'Short sides')
        count=tk.StringVar(value=str(config['count']))
        ttk.Label(form,text='Clamped edges').grid(row=2,column=0,sticky='w',padx=5)
        ttk.Combobox(form,textvariable=edge,values=['Long sides','Short sides'],state='readonly',width=18).grid(row=2,column=1,padx=5,pady=3)
        ttk.Label(form,text='Number of clamps').grid(row=2,column=2,padx=5)
        ttk.Combobox(form,textvariable=count,values=['4','6','8','10','12'],state='readonly',width=10).grid(row=2,column=3,padx=5)
        preview=tk.Canvas(content,background='#ffffff',highlightthickness=1,highlightbackground='#aaaaaa',height=300)
        preview.pack(fill='both',expand=True,pady=8)
        status=ttk.Label(content,wraplength=900,justify='left');status.pack(fill='x')
        ttk.Label(content,text='Initial values are geometric, not manufacturer specifications. Six-point A/B/C stations indicate clamping axes, not drilling holes. Check module clamp zones, rails, mechanical strength and actual parts before installation.',wraplength=1000,justify='left',foreground='#555555').pack(fill='x',pady=6)
        buttons=ttk.Frame(content);buttons.pack(fill='x')
        last={};apply_buttons=[]

        def render(*args):
            preview.delete('all');last.clear()
            six=count.get()=='6'
            if six:
                abc_frame.pack(fill='x',pady=(3,5),before=preview)
                for key in ('a_mm','b_mm'):
                    variables[key]._entry.grid_remove();variables[key]._label.grid_remove()
                help_text.set('Six clamps: A, B and C are three INDEPENDENT distances from the top edge '
                              '(axes of left/right pairs). A < B < C in mm. '
                              'Both clamps in each pair move together.')
            else:
                abc_frame.pack_forget()
                for key in ('a_mm','b_mm'):
                    variables[key]._entry.grid();variables[key]._label.grid()
                help_text.set('Standard mounting: A is the start offset, B is the end offset, '
                              'and C is the calculated regular spacing. Two points on opposite sides per row.')
            try:
                draft=dict(config,edge='long' if edge.get()=='Long sides' else 'short',count=int(count.get()),positions={})
                for key,var in variables.items():draft[key]=float(var.get().replace(',','.'))
                if six:
                    draft['top_offsets_mm']=[float(abc_vars[key].get().replace(',','.')) for key in 'ABC']
                    if not axes(draft)[2]:
                        raise ValueError('To measure A/B/C from the top, choose vertical clamped edges: long sides in portrait, short sides in landscape.')
                else:
                    draft.pop('top_offsets_mm',None)
                c=validate_config(draft,footprint=not edge_active)
                example=next(iter(selected),next(iter(self._mounting_items.values())))
                preview_plan=dict(self.mounting_plan,panels=dict(self.mounting_plan['panels'],**{example['uid']:c}))
                previous=self.mounting_plan['panels'].get(example['uid'])
                if previous and previous['count']!=c['count']:
                    preview_rules=copy.deepcopy(self.mounting_plan.get('edge_rules',{}))
                    preview_rules.get('overrides',{}).pop(example['uid'],None)
                    preview_plan['edge_rules']=preview_rules
                preview_item=geometry(self,preview_plan)[example['uid']]
                if preview_item['issue']:raise ValueError(preview_item['issue'])
                last['config']=c
            except (ValueError,TypeError) as exc:
                status.configure(text=str(exc),foreground='#333333')
                for b in apply_buttons:b.state(['disabled'])
                return
            for b in apply_buttons:b.state(['!disabled'])
            if not selected:apply_buttons[0].state(['disabled'])
            w,h=c['width_mm'],c['height_mm'];length,cross,along_y=axes(c)
            display_w,display_h=(w,h) if along_y else (h,w)
            z=min(max(50,preview.winfo_width()-200)/display_w,max(50,preview.winfo_height()-100)/display_h)
            offset=((preview.winfo_width()-display_w*z)/2,(preview.winfo_height()-display_h*z)/2)
            shapes=[dict(kind='polygon',points=[(0,0),(w,0),(w,h),(0,h)],fill='#ffffff',color='#111111',width=2)]
            fixing_shapes=[]
            for f in preview_item['fixings']:
                fixing_shapes.append(dict(kind='polygon',points=f['polygon'],fill='#202020' if f['kind']=='edge' else '#888888',color='#111111',width=1))
                x,y=f['x'],f['y'];shift=32/z
                fixing_shapes.append(dict(kind='text',point=(x+(-shift if f['side']==0 else shift),y) if along_y else (x,y+(-shift if f['side']==0 else shift)),
                    text='F'+str(f['index']+1),font=10/z,color='#111111',background=True))
            stations=station_positions(c)
            if six:
                for j,name in enumerate('ABC'):
                    stop=stations[j]
                    p1,p2=((0,0),(0,stop)) if along_y else ((0,0),(stop,0))
                    label=(-(65+45*j)/z,stop/2) if along_y else (stop/2,-(65+45*j)/z)
                    dimension(shapes,p1,p2,label,'aligned',1,10/z,prefix=name+' = ')
            else:
                chain=[0]+stations+[length]
                for j,(a,b) in enumerate(zip(chain,chain[1:])):
                    p1,p2=((0,a),(0,b)) if along_y else ((a,0),(b,0))
                    label=(-65/z,(a+b)/2) if along_y else ((a+b)/2,-65/z)
                    dimension(shapes,p1,p2,label,'aligned',1,10/z,prefix=('A = ' if j==0 else 'B = ' if j==len(chain)-2 else 'C = '))
            shapes+=fixing_shapes
            if not along_y:
                for shape in shapes:
                    if 'points' in shape:shape['points']=[(y,x) for x,y in shape['points']]
                    if 'point' in shape:shape['point']=tuple(reversed(shape['point']))
            draw_tk(preview,shapes,z,offset)
            cval=(length-c['a_mm']-c['b_mm'])/(c['count']//2-1) if not six else None
            note=(f'6 clamps · A = {stations[0]:.1f} · B = {stations[1]:.1f} · C = {stations[2]:.1f} mm from the top edge.'
                  if six else f'{c["count"]} clamps · {c["count"]//2} stations · spacing C = {cval:.1f} mm.')
            if c['edge']=='long' and c['count']==4:
                note+=' NEG21C.20 reference (model to be confirmed): 440–540 mm offsets, according to the manual diagram and rails.'
            status.configure(text=note,foreground='#222222')

        def apply(all_panels):
            if 'config' not in last:return
            targets=set(self.panels) if all_panels else set(self.selected_panel_coords)
            c=last['config'];candidate=copy.deepcopy(self.mounting_plan)
            affected={self.panel_uids[coord] for coord in targets}
            for coord in targets:
                uid=self.panel_uids[coord];previous=candidate['panels'].get(uid)
                if previous and previous['count']!=c['count']:
                    candidate.get('edge_rules',{}).get('overrides',{}).pop(uid,None)
                candidate['panels'][uid]=copy.deepcopy(c)
            issues=[f"P{item['number']} : {item['issue']}" for uid,item in geometry(self,candidate).items() if uid in affected and item['issue']]
            if issues:
                messagebox.showerror('Incompatible mounting','\n'.join(issues[:3]),parent=win);return
            # One project undo step, irrespective of how long the dialog stayed open.
            self._record_history()
            self.mounting_plan=candidate;self.mounting_plan['template']=copy.deepcopy(c)
            self.mounting_plan['dimensions']=[d for d in self.mounting_plan['dimensions']
                if not (d.get('auto') and (d.get('ref1') or {}).get('uid') in affected)]
            self._mounting_selected_fixing=None;self._mounting_selected_dimension=None
            win.destroy();self.draw_grid();self._record_history()

        for label,all_panels in ((f'Apply to selection ({len(selected)})',False),(f'Apply to all ({len(self.panels)})',True)):
            b=ttk.Button(buttons,text=label,command=lambda a=all_panels:apply(a));b.pack(side='left',padx=4);apply_buttons.append(b)
        ttk.Button(buttons,text='Cancel',command=win.destroy).pack(side='right')
        for var in list(variables.values())+list(abc_vars.values())+[edge,count]:var.trace_add('write',render)
        preview.bind('<Configure>',render)
        self._fit_dialog(win,1080,790);win.after_idle(render)
