"""Installer-facing datum, editable fixing inspector and drawing metadata."""
import copy
import math
import tkinter as tk
from tkinter import ttk, messagebox
from mounting import validate_site, axes, set_fixing_position
from mounting_drawing import site_origin


class MountingChantierMixin:
    def _build_mounting_chantier_menu(self, parent):
        menu=parent
        menu.add_command(label='Place the site datum on the drawing',command=lambda:self._set_mounting_mode('origin'))
        menu.add_command(label='Drawing references, revision and site instructions...',command=self._edit_mounting_site)
        menu.add_separator()
        self.mounting_auto_cotes=tk.BooleanVar(master=self.root,value=True)
        menu.add_checkbutton(label='Show live dimensions',variable=self.mounting_auto_cotes,command=self._draw_mounting_annotations)
        menu.add_separator()
        menu.add_command(label='Installation PDF package (vector)...',command=lambda:self._export_mounting('pdf'))
        return menu

    def _refresh_mounting_image(self):
        if self._mounting_active():
            self._mounting_background(fast=True)
            self._schedule_mounting_image_quality()

    def _build_mounting_inspector(self):
        frame=ttk.Frame(self.canvas_frame,padding=(7,4))
        self.mounting_inspector=frame
        row=ttk.Frame(frame);row.pack(fill='x')
        self._mounting_inspector_title=ttk.Label(row,text='Installation drawing · select a clamp to view and edit its position.',justify='left')
        self._mounting_inspector_title.pack(side='left',padx=(0,12))
        ttk.Label(row,text='Distance from top / starting edge (mm):').pack(side='left')
        self._mounting_inspector_value=tk.StringVar(master=self.root)
        self._mounting_inspector_entry=ttk.Entry(row,textvariable=self._mounting_inspector_value,width=12)
        self._mounting_inspector_entry.pack(side='left',padx=(5,4))
        self._mounting_inspector_entry.bind('<Return>',lambda e:self._mounting_apply_inspector())
        self._mounting_inspector_button=ttk.Button(row,text='Apply position',command=self._mounting_apply_inspector)
        self._mounting_inspector_button.pack(side='left',padx=5)
        ttk.Button(row,text='Site datum',command=lambda:self._set_mounting_mode('origin')).pack(side='right',padx=5)
        ttk.Button(row,text='PDF package',command=lambda:self._export_mounting('pdf')).pack(side='right',padx=5)
        row2=ttk.Frame(frame);row2.pack(fill='x',pady=(4,0))
        self._mounting_inspector_details=ttk.Label(row2,justify='left')
        self._mounting_inspector_details.pack(side='left')
        self._mounting_cursor_label=ttk.Label(row2,foreground='#444444')
        self._mounting_cursor_label.pack(side='right')
        self._mounting_inspector_target=None
        self._mounting_inspector_entry.state(['disabled']);self._mounting_inspector_button.state(['disabled'])

    def _mounting_sync_inspector(self):
        if not hasattr(self,'_mounting_inspector_title'):return
        items=getattr(self,'_mounting_items',{})
        selected=self._mounting_selected_fixing
        item=items.get(selected[0]) if selected else None
        fixing=(item['fixings'][selected[1]] if item and 0<=selected[1]<len(item['fixings']) else None)
        if fixing:
            origin,confirmed=site_origin(self,items)
            x=(fixing['point'][0]-origin[0])/self.px_per_mm
            y=(fixing['point'][1]-origin[1])/self.px_per_mm
            label={'edge':'End','intermediate':'Intermediate','standard':'Uniform'}[fixing['kind']]
            paired=item['config']['count']==6 and item['config'].get('top_offsets_mm') is not None
            station='ABC'[fixing['index']//2] if paired else f"F{fixing['index']+1}"
            self._mounting_inspector_title.configure(text=f"P{item['number']} / F{fixing['index']+1} — {station} — {label}"
                + (' · left/right pair' if paired else ''))
            self._mounting_inspector_details.configure(text=(f"X={x:.1f} mm  ·  Y={y:.1f} mm from datum "
                f"{'defined' if confirmed else 'TEMPORARY'}  |  {fixing['length_mm']:g} × {fixing['width_mm']:g} mm  |  "
                f"Ref. {fixing['reference'] or 'to specify'}  |  "
                f"{'manual type' if fixing.get('forced') else 'automatic type'}"))
            if selected!=self._mounting_inspector_target or self.root.focus_get()!=self._mounting_inspector_entry:
                self._mounting_inspector_value.set(f"{fixing['position_mm']:.1f}")
            self._mounting_inspector_target=selected
            self._mounting_inspector_entry.state(['!disabled']);self._mounting_inspector_button.state(['!disabled'])
        else:
            self._mounting_inspector_target=None
            self._mounting_inspector_title.configure(text='Select a clamp to view its coordinates and edit its position.')
            configured=sum(bool(i['config']) for i in items.values())
            origin,confirmed=site_origin(self,items)
            self._mounting_inspector_details.configure(text=(f"Modules: {len(items)}  ·  configured mountings: {configured}  ·  "
                f"datum: {'defined' if confirmed else 'TEMPORARY — set on drawing'}  ·  "
                'dimensions and coordinates follow actual geometry.'))
            self._mounting_inspector_value.set('')
            self._mounting_inspector_entry.state(['disabled']);self._mounting_inspector_button.state(['disabled'])

    def _mounting_apply_inspector(self):
        selected=self._mounting_selected_fixing
        if selected is None:return
        uid,index=selected
        if uid not in self.mounting_plan.get('panels',{}):return
        try:
            value=float(self._mounting_inspector_value.get().strip().replace(',','.'))
            if not math.isfinite(value):raise ValueError('Value must be finite.')
            config=copy.deepcopy(self.mounting_plan['panels'][uid])
            config=set_fixing_position(config,index,round(value,2))
            validated=self._validate_mounting_config(uid,config)
        except (ValueError,TypeError) as exc:
            messagebox.showerror('Invalid position',str(exc),parent=self.root)
            return
        self._record_history()
        self.mounting_plan['panels'][uid]=validated
        self.draw_grid();self._record_history()

    def _mounting_define_origin(self,point):
        if self.px_per_mm<=0:return
        snapped,_=self._mounting_snap(point)
        self._record_history()
        self.mounting_plan.setdefault('site',{})['origin']=list(snapped)
        self._set_mounting_mode('select')
        self._record_history()

    def _edit_mounting_site(self):
        if not self._mounting_ready():return
        old=getattr(self,'_mounting_site_window',None)
        if old is not None and old.winfo_exists():old.lift();return
        win=tk.Toplevel(self.root);self._mounting_site_window=win
        win.title('Site references and installation instructions');win.transient(self.root);win.grab_set()
        body=ttk.Frame(win,padding=15);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Drawing title block / site information',font=('Arial',13,'bold')).pack(anchor='w')
        ttk.Label(body,text='Blank fields will appear as “TO BE CONFIRMED”. Rails, anchors and tightening torques are not calculated.',
                  wraplength=750,justify='left').pack(anchor='w',pady=(6,12))
        labels=(('drawing_reference','Drawing number'),('revision','Revision'),('origin_label','Datum name'),
                ('roof_reference','Roof / area reference'),('support_reference','Selected rails / supports'),
                ('anchor_reference','Selected anchors / fasteners'))
        vars={};grid=ttk.Frame(body);grid.pack(fill='x')
        site=validate_site(self.mounting_plan.get('site'))
        for i,(key,label) in enumerate(labels):
            ttk.Label(grid,text=label).grid(row=i,column=0,sticky='w',padx=(0,15),pady=5)
            var=tk.StringVar(master=win,value=site[key]);vars[key]=var
            ttk.Entry(grid,textvariable=var,width=65).grid(row=i,column=1,sticky='ew',pady=5)
        grid.columnconfigure(1,weight=1)
        ttk.Label(body,text='Installation notes and on-site checks:').pack(anchor='w',pady=(12,3))
        notes=tk.Text(body,height=5,wrap='word');notes.pack(fill='both',expand=True)
        notes.insert('1.0',site['installer_notes'])
        origin,_=site_origin(self,getattr(self,'_mounting_items',{}))
        ttk.Label(body,text=('Datum O: calibrated drawing X/Y coordinates in mm (image origin at top left). '
            'You can also place the datum by clicking the canvas and snapping to a module corner.'),
            wraplength=750,justify='left').pack(anchor='w',pady=(12,5))
        pos=ttk.Frame(body);pos.pack(fill='x')
        values=[]
        for title,v in (('Image X (mm)',origin[0]/self.px_per_mm),('Image Y (mm)',origin[1]/self.px_per_mm)):
            ttk.Label(pos,text=title).pack(side='left',padx=(0,5))
            var=tk.StringVar(master=win,value=f'{v:.2f}');values.append(var)
            ttk.Entry(pos,textvariable=var,width=14).pack(side='left',padx=(0,20))
        temporary=tk.BooleanVar(master=win,value=site['origin'] is None)
        ttk.Checkbutton(pos,text='Automatic temporary datum',variable=temporary).pack(side='left')
        def save():
            try:
                draft={k:v.get() for k,v in vars.items()}
                draft['installer_notes']=notes.get('1.0','end-1c')
                if temporary.get():draft['origin']=None
                else:
                    xy=[float(v.get().replace(',','.'))*self.px_per_mm for v in values]
                    draft['origin']=xy
                draft=validate_site(draft)
            except (ValueError,TypeError) as exc:
                messagebox.showerror('Invalid data',str(exc),parent=win);return
            self._record_history();self.mounting_plan['site']=draft
            win.destroy();self.draw_grid();self._record_history()
        controls=ttk.Frame(body);controls.pack(fill='x',pady=12)
        ttk.Button(controls,text='Save site details',command=save).pack(side='left')
        ttk.Button(controls,text='Cancel',command=win.destroy).pack(side='right')
        self._fit_dialog(win,850,720)
