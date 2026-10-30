"""Retained mounting canvas, pointer anchored zoom and deferred image quality."""
import math
from mounting_drawing import geometry,scene,annotations,bounds,draw_tk,construction_shapes
from mounting_quantities import fixing_inventory


class MountingViewMixin:
    def _render_mounting_plan(self):
        left,top=self.canvas.canvasx(0),self.canvas.canvasy(0)
        self.canvas.delete('all');self.canvas.configure(background='#ffffff')
        self._mounting_items=geometry(self)
        rules=self.mounting_plan.get('edge_rules',{})
        self._mounting_inventory=(fixing_inventory(self._mounting_items,self.px_per_mm,rules.get('max_gap_mm',50))
                                  if rules.get('enabled') and self.px_per_mm>0 else None)
        shapes=scene(self,self._mounting_items,selected=self.selected_panel_coords,
            selected_dimension=self._mounting_selected_dimension,selected_fixing=self._mounting_selected_fixing,construction=False,
            inventory=self._mounting_inventory)
        shapes=[s for s in shapes if s.get('role')!='legend']
        from mounting_drawing import construction_shapes
        auto=construction_shapes(self,self._mounting_items,font=11/self.zoom_level,
            selected=self.selected_panel_coords,selected_fixing=self._mounting_selected_fixing,
            selected_dimension=self._mounting_selected_live_dimension) if self.mounting_auto_cotes.get() else []
        self._mounting_world_bounds=bounds(shapes+auto)
        draw_tk(self.canvas,[s for s in shapes if s.get('tag') is None],self.zoom_level)
        self._mounting_drawn_zoom=self.zoom_level
        self._mounting_number_width=next((math.dist(i['poly'][0],i['poly'][1]) for i in self._mounting_items.values()),40.)
        self._mounting_number_digits=max((len(str(i['number'])) for i in self._mounting_items.values()),default=1)
        self._mounting_number_style=None
        self._set_mounting_viewport(left,top)
        self._update_mounting_numbers();self._draw_mounting_annotations()
        self._mounting_background();self._draw_mounting_legend();self._mounting_update_status()

    def _set_mounting_viewport(self,left,top):
        w,h=max(1,self.canvas.winfo_width()),max(1,self.canvas.winfo_height())
        x1,y1,x2,y2=(v*self.zoom_level for v in self._mounting_world_bounds)
        # Leave room around the current viewport so Tk never clamps a pointer
        # anchor merely because the plan is smaller than the canvas.
        region=(min(x1,left-w),min(y1,top-h),max(x2,left+2*w),max(y2,top+2*h))
        self._mounting_region=region
        self.total_w,self.total_h=region[2]-region[0],region[3]-region[1]
        self.canvas.configure(scrollregion=region)
        self.canvas.xview_moveto((left-region[0])/self.total_w)
        self.canvas.yview_moveto((top-region[1])/self.total_h)

    def _update_mounting_numbers(self):
        width=self._mounting_number_width*self.zoom_level
        size=max(7,int(width/4))
        sample='8'*self._mounting_number_digits
        measured=float(self.root.tk.call('font','measure',('Arial',size,'bold'),sample))
        if measured>width*.9:
            size=max(7,int(size*width*.9/max(1,measured)))
            measured=float(self.root.tk.call('font','measure',('Arial',size,'bold'),sample))
        state='normal' if measured<=width*.95 else 'hidden'
        style=(size,state)
        if style!=getattr(self,'_mounting_number_style',None):
            self.canvas.itemconfigure('mounting-number',font=('Arial',size,'bold'),state=state)
            self._mounting_number_style=style

    def _draw_mounting_annotations(self):
        self.canvas.delete('mounting_annotation')
        self.canvas.delete('mounting_live_dims')
        shapes=annotations(self.mounting_plan,self._mounting_items,self.px_per_mm,
            font=11/self.zoom_level,selected_dimension=self._mounting_selected_dimension)
        draw_tk(self.canvas,shapes,self.zoom_level)
        if getattr(self,'mounting_auto_cotes',None) is None or self.mounting_auto_cotes.get():
            live=construction_shapes(self,self._mounting_items,11/self.zoom_level,
                selected=self.selected_panel_coords,selected_fixing=self._mounting_selected_fixing,
                selected_dimension=self._mounting_selected_live_dimension)
            draw_tk(self.canvas,live,self.zoom_level,live=True)

    def _draw_mounting_legend(self):
        self.canvas.delete('mounting_legend')
        rules=self.mounting_plan.get('edge_rules',{})
        if not rules.get('enabled'):return
        inv=getattr(self,'_mounting_inventory',None)
        if inv is None:return
        text=(f"Clamps physiques : R {inv['pieces_by_kind'].get('edge',0)} | "
              f"I {inv['pieces_by_kind'].get('intermediate',0)} | Total {inv['pieces_total']} "
              f"({inv['points_total']} clamping contacts)")
        x,y=self.canvas.canvasx(12),self.canvas.canvasy(12)
        ident=self.canvas.create_text(x,y,text=text,anchor='nw',font=('Arial',10),fill='#303030',tags='mounting_legend')
        box=self.canvas.bbox(ident)
        bg=self.canvas.create_rectangle(box[0]-4,box[1]-3,box[2]+4,box[3]+3,fill='white',outline='',tags='mounting_legend')
        self.canvas.tag_lower(bg,ident)

    def _mounting_background(self,fast=False):
        """Mounting is a line drawing: never display a photographic underlay."""
        self.canvas.delete('mounting_background')

    def _schedule_mounting_image_quality(self):
        """No asynchronous image filtering is needed on a vector-only canvas."""
        job=getattr(self,'_mounting_quality_job',None)
        if job:self.root.after_cancel(job)
        self._mounting_quality_job=None

    def _refresh_mounting_viewport(self):
        self._mounting_resize_job=None
        if not self._mounting_active() or not hasattr(self,'_mounting_world_bounds'):return
        self._set_mounting_viewport(self.canvas.canvasx(0),self.canvas.canvasy(0))
        self._mounting_background(fast=True);self._draw_mounting_legend();self._schedule_mounting_image_quality()

    def _queue_mounting_zoom(self,factor,event):
        self._mounting_pending_zoom=getattr(self,'_mounting_pending_zoom',1.)*factor
        self._mounting_zoom_pointer=(event.x,event.y)
        if not getattr(self,'_mounting_zoom_job',None):
            self._mounting_zoom_job=self.root.after(16,self._flush_mounting_zoom)

    def _flush_mounting_zoom(self):
        self._mounting_zoom_job=None
        factor=getattr(self,'_mounting_pending_zoom',1.);self._mounting_pending_zoom=1.
        if self._mounting_active():self._mounting_zoom(factor,pointer=self._mounting_zoom_pointer)

    def _cancel_mounting_view_jobs(self):
        for name in ('_mounting_zoom_job','_mounting_quality_job','_mounting_resize_job'):
            job=getattr(self,name,None)
            if job:self.root.after_cancel(job)
            setattr(self,name,None)
        self._mounting_pending_zoom=1.

    def _mounting_zoom(self,factor,event=None,pointer=None):
        self._auto_fit=False
        if not hasattr(self,'_mounting_world_bounds'):self._render_mounting_plan()
        x,y=pointer or ((event.x,event.y) if event else (self.canvas.winfo_width()/2,self.canvas.winfo_height()/2))
        old=self.zoom_level;new=max(.01,min(20,old*factor))
        if abs(new-old)<1e-12:return
        source=(self.canvas.canvasx(x)/old,self.canvas.canvasy(y)/old)
        self.zoom_level=new
        self.canvas.delete('mounting_preview')
        self.canvas.scale('mounting_geometry',0,0,new/self._mounting_drawn_zoom,new/self._mounting_drawn_zoom)
        self._mounting_drawn_zoom=new
        self._set_mounting_viewport(source[0]*new-x,source[1]*new-y)
        self._update_mounting_numbers();self._draw_mounting_annotations()
        self._mounting_background(fast=True);self._draw_mounting_legend()
        self._schedule_mounting_image_quality()

    def _fit_mounting(self):
        self._auto_fit=False;self._cancel_mounting_view_jobs()
        if not hasattr(self,'_mounting_world_bounds'):self._render_mounting_plan()
        left,top,right,bottom=self._mounting_world_bounds
        w,h=max(100,self.canvas.winfo_width()),max(100,self.canvas.winfo_height())
        target=max(.01,min(20,min((w-60)/max(1,right-left),(h-60)/max(1,bottom-top))))
        self._mounting_zoom(target/self.zoom_level)
        self._set_mounting_viewport((left+right)/2*self.zoom_level-w/2,(top+bottom)/2*self.zoom_level-h/2)
        self._mounting_background(fast=True);self._draw_mounting_legend();self._schedule_mounting_image_quality()
