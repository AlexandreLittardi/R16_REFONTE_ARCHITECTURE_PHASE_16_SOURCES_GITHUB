"""Apply intermediate-clamp thickness to the EXISTING Layout lattice.

This intentionally changes the physical layout (and hence module coordinates in
Montage, SVG and PDF), instead of drawing fictitious gaps in the mounting layer.
"""
import math
from geometry_layout import grid_spec
from mounting import axes


def suggested_layout_gaps(app, rules):
    """Return (gap_width, gap_length, changed) without mutating the project."""
    gap=float(rules.get('joint_gap_mm',0))
    if not math.isfinite(gap) or gap<0:raise ValueError('Jeu de pince invalide.')
    settings=getattr(app,'model_settings',{})
    width=float(settings.get('module_gap_width_mm',settings.get('module_gap_x_mm',0)))
    length=float(settings.get('module_gap_length_mm',settings.get('module_gap_y_mm',0)))
    if not rules.get('enabled') or gap<=0:return width,length,False
    configs=app.mounting_plan.get('panels',{}).values()
    direction={axes(c)[2] for c in configs}
    if True in direction:width=max(width,gap)
    if False in direction:length=max(length,gap)
    return width,length, (width>float(settings.get('module_gap_width_mm',settings.get('module_gap_x_mm',0)))+1e-9 or
                          length>float(settings.get('module_gap_length_mm',settings.get('module_gap_y_mm',0)))+1e-9)


def check_layout_capacity(app, gap_width, gap_length):
    """Reject any grid gap update that would silently lose installed panels."""
    invalid=[]
    if getattr(app,'px_per_mm',0)<=0:return invalid
    zones=getattr(app,'roof_zones',[])
    for z_idx,zone in enumerate(zones):
        current_base=zone.get('row_base',z_idx*100)
        current_capacity=zone.get('row_capacity',max(zone.get('rows',0),100))
        trial=dict(zone,gap_width_mm=gap_width,gap_length_mm=gap_length,
                   gap_x_mm=gap_width,gap_y_mm=gap_length)
        rows,cols,*_=grid_spec(trial,app.panel_width_mm,app.panel_height_mm,app.px_per_mm)
        for coord in getattr(app,'panels',{}):
            r,c=coord
            if current_base<=r<current_base+current_capacity and (r-current_base>=rows or c>=cols):
                invalid.append(coord)
    return invalid


def commit_layout_gap(app, gap_width, gap_length):
    """Called after a confirmed and capacity-checked change, with project history."""
    app._record_history()
    settings=app.model_settings
    for key,value in (('module_gap_width_mm',gap_width),('module_gap_x_mm',gap_width),
                      ('module_gap_length_mm',gap_length),('module_gap_y_mm',gap_length)):
        settings[key]=value
    for entry,value in ((getattr(app,'entry_gap_width',None),gap_width),
                        (getattr(app,'entry_gap_length',None),gap_length)):
        if entry is not None:
            entry.delete(0,'end');entry.insert(0,str(value))
    app._recalculate_zone_grids()
    app._mark_geometry_change()
