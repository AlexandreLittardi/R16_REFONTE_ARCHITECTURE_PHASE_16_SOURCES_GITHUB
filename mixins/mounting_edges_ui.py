"""End/intermediate fixing profiles and explicit plan overrides."""
import copy
import tkinter as tk
from tkinter import ttk,messagebox
from mounting import validate_config
from mounting_edges import default_rules,validate_rules
from mounting_drawing import geometry,scene,bounds,draw_tk
from mounting_quantities import fixing_inventory
from mounting_joint_gap import suggested_layout_gaps,check_layout_capacity,commit_layout_gap


class MountingEdgesMixin:
    def _build_mounting_edges_menu(self,parent):
        menu=tk.Menu(parent,tearoff=False)
        menu.add_command(label='Types, module gaps and quantities...',command=self._open_mounting_edges)
        for panels,title in ((False,'Type of selected clamp'),(True,'Clamp types for selected modules')):
            sub=tk.Menu(menu,tearoff=False)
            for kind,label in (('auto','Automatic'),('edge','End'),('intermediate','Intermediate')):
                sub.add_command(label=label,command=lambda k=kind,p=panels:self._change_mounting_types(k,p))
            menu.add_cascade(label=title,menu=sub)
        return menu

    def _select_boundary_panels(self):
        if not self._mounting_ready():return
        items=geometry(self)
        self.selected_panel_coords={item['coord'] for item in items.values() if item['is_boundary']}
        self._mounting_selected_fixing=None;self._mounting_selected_dimension=None
        self._set_mounting_mode('select')

    def _validate_mounting_config(self,uid,config):
        enabled=self.mounting_plan.get('edge_rules',{}).get('enabled',False)
        c=validate_config(config,footprint=not enabled)
        plan=dict(self.mounting_plan,panels={**self.mounting_plan['panels'],uid:c})
        item=geometry(self,plan).get(uid)
        if item and item['issue']:raise ValueError(item['issue'])
        return c

    def _change_mounting_types(self,kind,panels=False):
        if not self._mounting_ready():return
        rules=validate_rules(self.mounting_plan.get('edge_rules'))
        if panels:
            targets={self.panel_uids[c]:range(self.mounting_plan['panels'][self.panel_uids[c]]['count'])
                     for c in self.selected_panel_coords if self.panel_uids.get(c) in self.mounting_plan['panels']}
        else:
            selected=self._mounting_selected_fixing
            targets={selected[0]:[selected[1]]} if selected else {}
        if not targets:
            messagebox.showinfo('Clamp type','Select a clamp or previously configured modules on the drawing.',parent=self.root);return
        for uid,indices in targets.items():
            values=rules['overrides'].setdefault(uid,{})
            for index in indices:
                if kind=='auto':values.pop(str(index),None)
                else:values[str(index)]=kind
            if not values:rules['overrides'].pop(uid,None)
        if not rules['enabled'] and kind!='auto':
            self._open_mounting_edges(overrides=rules['overrides']);return
        plan=dict(self.mounting_plan,edge_rules=rules)
        issues=[f"P{item['number']} : {item['issue']}" for item in geometry(self,plan).values() if item['issue']]
        if issues:
            messagebox.showerror('Incompatible type','\n'.join(issues[:3]),parent=self.root);return
        self._record_history();self.mounting_plan['edge_rules']=rules;self.draw_grid();self._record_history()

    def _open_mounting_edges(self,overrides=None):
        if not self._mounting_ready():return
        existing=getattr(self,'_mounting_edges_dialog',None)
        if existing and existing.winfo_exists():existing.lift();return
        rules=validate_rules(self.mounting_plan.get('edge_rules'))
        if rules==default_rules():
            config=next(iter(self.mounting_plan['panels'].values()),None)
            if config:rules=default_rules(config['clamp_length_mm'],config['clamp_width_mm'])
        if overrides is not None:rules['overrides']=copy.deepcopy(overrides)
        win=tk.Toplevel(self.root);self._mounting_edges_dialog=win
        win.title('End and intermediate clamps');win.transient(self.root);win.grab_set()
        body=ttk.Frame(win,padding=12);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Clamps classified by module edges',font=('Arial',13,'bold')).pack(anchor='w')
        enabled=tk.BooleanVar(value=True)
        ttk.Checkbutton(body,text='Automatically classify end and intermediate clamps',variable=enabled).pack(anchor='w',pady=5)
        ttk.Label(body,text='A clamp is intermediate when an adjacent module faces its mounting point; otherwise it is an end clamp.\nA module may use both types. Manually overridden types take precedence.',justify='left',wraplength=1000).pack(anchor='w',pady=5)
        table=ttk.Frame(body);table.pack(fill='x',pady=5);variables={}
        for column,label in enumerate(('Type','Reference / description','Length Lf (mm)','Width lf (mm)')):
            ttk.Label(table,text=label).grid(row=0,column=column,padx=8,sticky='w')
        for row,(kind,label) in enumerate((('intermediate','Intermediate (I)'),('edge','End (R)')),1):
            ttk.Label(table,text=label).grid(row=row,column=0,padx=8,sticky='w')
            for col,key in enumerate(('reference','length_mm','width_mm'),1):
                var=tk.StringVar(value=str(rules['profiles'][kind][key]));variables[(kind,key)]=var
                entry=ttk.Entry(table,textvariable=var,width=28 if col==1 else 14)
                entry.grid(row=row,column=col,padx=8,pady=4)
        gap=tk.StringVar(value=f"{rules['max_gap_mm']:g}")
        row=ttk.Frame(body);row.pack(fill='x',pady=4)
        ttk.Label(row,text='Maximum gap between neighboring modules (mm)').pack(side='left',padx=5)
        ttk.Entry(row,textvariable=gap,width=12).pack(side='left',padx=5)
        joint=tk.StringVar(value=f"{rules.get('joint_gap_mm',0):g}")
        row_joint=ttk.Frame(body);row_joint.pack(fill='x',pady=4)
        ttk.Label(row_joint,text='Minimum gap imposed by intermediate clamp (mm)').pack(side='left',padx=5)
        ttk.Entry(row_joint,textvariable=joint,width=12).pack(side='left',padx=5)
        ttk.Label(body,text='This gap is measured BETWEEN FRAMES. Apply will increase the Layout spacing along clamped edges as needed. Coordinates, dimensions and exports are recalculated; existing larger gaps are preserved.',wraplength=1000,justify='left').pack(anchor='w',pady=4)
        ttk.Label(body,text='Only parallel, facing module frames are considered adjacent. A gap above the threshold separates groups.\nArray boundaries, openings and isolated rows are considered; roof edges are not used for this detection.',wraplength=1000,justify='left').pack(anchor='w',pady=4)
        preview=tk.Canvas(body,background='#ffffff',highlightthickness=1,highlightbackground='#aaaaaa',height=320)
        preview.pack(fill='both',expand=True,pady=8)
        status=ttk.Label(body,wraplength=1050,justify='left');status.pack(fill='x',pady=4)
        ttk.Label(body,text="Both types retain their real-scale footprint. The summary distinguishes contact points from shared physical clamps.\nFor exceptions: select a clamp, then Clamps / Edges / Type of selected clamp.",wraplength=1050,justify='left').pack(anchor='w',pady=5)
        buttons=ttk.Frame(body);buttons.pack(fill='x');last={}

        def render(*args):
            last.clear();preview.delete('all')
            try:
                draft=copy.deepcopy(rules);draft['enabled']=enabled.get();draft['max_gap_mm']=float(gap.get().replace(',','.'));draft['joint_gap_mm']=float(joint.get().replace(',','.'))
                for (kind,key),var in variables.items():
                    draft['profiles'][kind][key]=var.get() if key=='reference' else float(var.get().replace(',','.'))
                draft=validate_rules(draft);plan=dict(self.mounting_plan,edge_rules=draft)
                if draft['enabled'] and draft['joint_gap_mm']>0 and not self.mounting_plan['panels']:
                    raise ValueError('Configure module clamps first; their clamped edge determines the Layout gap axis.')
                items=geometry(self,plan)
                issues=[f"P{item['number']} : {item['issue']}" for item in items.values() if item['issue']]
                if issues:raise ValueError('\n'.join(issues[:3]))
                points=[p for item in items.values() for p in item['poly']]
                if points:
                    width=max(p[0] for p in points)-min(p[0] for p in points)
                    height=max(p[1] for p in points)-min(p[1] for p in points)
                    z=min(max(30,preview.winfo_width()-100)/max(1,width),max(30,preview.winfo_height()-100)/max(1,height))
                    shapes=scene(self,items,font=10/z,plan=plan)
                    left,top,right,bottom=bounds(shapes,font=10/z)
                    z=min(max(30,preview.winfo_width()-30)/(right-left),max(30,preview.winfo_height()-30)/(bottom-top))
                    draw_tk(preview,shapes,z,(preview.winfo_width()/2-(left+right)/2*z,preview.winfo_height()/2-(top+bottom)/2*z))
                fs=[f for item in items.values() for f in item['fixings']]
                inventory=fixing_inventory(items,self.px_per_mm,draft['max_gap_mm'])
                suggested_width,suggested_length,will_change=suggested_layout_gaps(self,draft)
                bad=check_layout_capacity(self,suggested_width,suggested_length) if will_change else []
                if bad:raise ValueError(f'Gap too large: {len(bad)} modules would no longer fit in their area (e.g. {bad[0]}). Reduce the gap or adjust Layout.')
                text=(f"{sum(item['is_boundary'] for item in items.values())}/{len(items)} boundary modules. "
                      f"{inventory['points_by_kind'].get('edge',0)} end contacts -> {inventory['pieces_by_kind'].get('edge',0)} pieces; "
                      f"{inventory['points_by_kind'].get('intermediate',0)} intermediate contacts -> {inventory['pieces_by_kind'].get('intermediate',0)} pieces; "
                      f"TOTAL {inventory['pieces_total']} pieces ({inventory['points_total']} contacts); "
                      f"{sum(f.get('forced',False) for f in fs)} manual assignments."
                      +(f' Clamp gap: {draft["joint_gap_mm"]:g} mm; Layout gap after applying: {suggested_width:g} × {suggested_length:g} mm.' if draft['joint_gap_mm'] else '')
                      +(f' {inventory["unpaired_intermediate"]} unpaired intermediate contacts to verify.' if inventory['unpaired_intermediate'] else '')) if draft['enabled'] else 'Uniform mode: each module’s own clamp dimensions are used.'
                status.configure(text=text,foreground='#222222');apply_button.state(['!disabled']);last['rules']=draft
            except (ValueError,TypeError) as exc:
                status.configure(text=str(exc),foreground='#333333');apply_button.state(['disabled'])

        def apply():
            if 'rules' not in last:return
            draft=last['rules']
            gap_width,gap_length,change=suggested_layout_gaps(self,draft)
            bad=check_layout_capacity(self,gap_width,gap_length) if change else []
            if bad:
                messagebox.showerror('Incompatible gap',f'{len(bad)} modules would fall outside their area grid.',parent=win);return
            if change:
                if not messagebox.askyesno('Adjust Layout',
                    f'The intermediate clamp gap requires a new physical Layout spacing:\n'
                    f'Width gap = {gap_width:g} mm ; length gap = {gap_length:g} mm.\n\n'
                    'Modules will move and their dimensions will be recalculated. Edge setbacks may change. Continue?',parent=win):return
            self._record_history()
            if change:commit_layout_gap(self,gap_width,gap_length)
            self.mounting_plan['edge_rules']=draft
            win.destroy();self.draw_grid();self._record_history()

        apply_button=ttk.Button(buttons,text='Apply to project',command=apply);apply_button.pack(side='left',padx=4)
        ttk.Button(buttons,text='Cancel',command=win.destroy).pack(side='right',padx=4)
        for var in list(variables.values())+[gap,joint,enabled]:var.trace_add('write',render)
        preview.bind('<Configure>',render);self._fit_dialog(win,1120,830);win.after_idle(render)
