"""Cell-range selection, fill handle, formula references and clipboard actions."""
import tkinter as tk
from mixins.spreadsheet_tools import cell_id
from domain.spreadsheet_edits import paste_block, shift_formula, fill_range


class SpreadsheetInteractionsMixin:
    def _rebuild_spreadsheet_grid(self):
        self.spreadsheet_fill_handle=None
        self.spreadsheet_range_anchor=None
        self.spreadsheet_range_end=None
        self._spreadsheet_fill_outline=None
        return super()._rebuild_spreadsheet_grid()

    def _init_spreadsheet_state(self):
        super()._init_spreadsheet_state()
        self.spreadsheet_range_anchor=None
        self.spreadsheet_range_end=None
        self.spreadsheet_fill_handle=None
        self.spreadsheet_drag_mode=None

    def _build_material_spreadsheet_area(self):
        super()._build_material_spreadsheet_area()
        grid=self.spreadsheet_data_canvas
        grid.bind('<B1-Motion>',self._spreadsheet_cell_drag)
        grid.bind('<ButtonRelease-1>',self._spreadsheet_cell_release)
        grid.bind('<Control-c>',self._spreadsheet_copy)
        grid.bind('<Control-v>',self._spreadsheet_paste)

    def _spreadsheet_rect_coords(self,first,last):
        r0,r1=sorted((first[0],last[0]))
        c0,c1=sorted((first[1],last[1]))
        return (self._spreadsheet_col_x(c0),self._spreadsheet_row_y(r0),
                self._spreadsheet_col_x(c1)+self._spreadsheet_col_w(c1),
                self._spreadsheet_row_y(r1)+self._spreadsheet_row_h(r1))

    def _draw_spreadsheet_selection(self):
        super()._draw_spreadsheet_selection()
        grid=self.spreadsheet_data_canvas
        if self.spreadsheet_selected is None:return
        anchor=self.spreadsheet_range_anchor or self.spreadsheet_selected
        end=self.spreadsheet_range_end or self.spreadsheet_selected
        x0,y0,x1,y1=self._spreadsheet_rect_coords(anchor,end)
        if self.spreadsheet_selection_rect is not None:
            grid.coords(self.spreadsheet_selection_rect,x0,y0,x1,y1)
            grid.tag_raise(self.spreadsheet_selection_rect)
        if self.spreadsheet_fill_handle is None:
            self.spreadsheet_fill_handle=grid.create_rectangle(0,0,0,0,fill='#1565C0',outline='white')
        grid.coords(self.spreadsheet_fill_handle,x1-5,y1-5,x1+3,y1+3)
        grid.tag_raise(self.spreadsheet_fill_handle)

    def _insert_clicked_cell_reference(self,cell):
        entry=self.spreadsheet_edit_entry if self.spreadsheet_editing_cell is not None else self.spreadsheet_formula_entry
        if entry is None or not entry.get().strip().startswith('='):return False
        # Keep editing the source cell. Its FocusOut handler is not invoked.
        pos=entry.index(tk.INSERT)
        entry.insert(pos,cell_id(*cell))
        entry.icursor(pos+len(cell_id(*cell)))
        entry.focus_set()
        return True

    def _on_spreadsheet_cell_click(self,event):
        cell=self._spreadsheet_cell_at_event(event)
        if cell is None:return
        if self.spreadsheet_editing_cell is not None and self.spreadsheet_editing_cell!=cell:
            if self._insert_clicked_cell_reference(cell):return 'break'
        if (self.spreadsheet_formula_entry.focus_get()==self.spreadsheet_formula_entry and
            self._insert_clicked_cell_reference(cell)):
            return 'break'
        grid=self.spreadsheet_data_canvas
        if self.spreadsheet_selected is not None and self.spreadsheet_fill_handle is not None:
            x0,y0,x1,y1=grid.coords(self.spreadsheet_fill_handle)
            x,y=grid.canvasx(event.x),grid.canvasy(event.y)
            if x0-3<=x<=x1+3 and y0-3<=y<=y1+3:
                self.spreadsheet_drag_mode='fill'
                return 'break'
        if event.state & 0x0001 and self.spreadsheet_selected is not None:
            self.spreadsheet_range_anchor=self.spreadsheet_range_anchor or self.spreadsheet_selected
            self.spreadsheet_range_end=cell
            self.spreadsheet_drag_mode='select'
            self._draw_spreadsheet_selection()
            return 'break'
        self.spreadsheet_range_anchor=cell
        self.spreadsheet_range_end=cell
        self.spreadsheet_drag_mode='select'
        return super()._on_spreadsheet_cell_click(event)

    def _spreadsheet_cell_drag(self,event):
        if self.spreadsheet_drag_mode is None:return
        cell=self._spreadsheet_cell_at_event(event)
        if cell is None:return
        if self.spreadsheet_drag_mode=='select':
            self.spreadsheet_range_end=cell
            self._draw_spreadsheet_selection()
        elif self.spreadsheet_drag_mode=='fill':
            self._spreadsheet_fill_target=cell
            x0,y0,x1,y1=self._spreadsheet_rect_coords(self.spreadsheet_range_anchor or self.spreadsheet_selected,cell)
            grid=self.spreadsheet_data_canvas
            if not getattr(self,'_spreadsheet_fill_outline',None):
                self._spreadsheet_fill_outline=grid.create_rectangle(x0,y0,x1,y1,outline='#1976D2',dash=(4,2),width=2)
            else:grid.coords(self._spreadsheet_fill_outline,x0,y0,x1,y1)

    def _spreadsheet_cell_release(self,event):
        if self.spreadsheet_drag_mode=='fill' and getattr(self,'_spreadsheet_fill_target',None) is not None:
            self._spreadsheet_fill_to(self._spreadsheet_fill_target)
        self.spreadsheet_drag_mode=None
        self._spreadsheet_fill_target=None
        if getattr(self,'_spreadsheet_fill_outline',None):
            self.spreadsheet_data_canvas.delete(self._spreadsheet_fill_outline)
            self._spreadsheet_fill_outline=None

    def _spreadsheet_fill_to(self,target):
        return self._run_project_edit('spreadsheet:fill-range',
                                      self._spreadsheet_fill_to_impl, target)

    def _spreadsheet_fill_to_impl(self,target):
        if self.spreadsheet_selected is None:return
        anchor=self.spreadsheet_range_anchor or self.spreadsheet_selected
        end=self.spreadsheet_range_end or anchor
        fill_range(self.material_spreadsheet, anchor, end, target)
        self.spreadsheet_range_end=target
        self._refresh_spreadsheet()
        self._draw_spreadsheet_selection()

    def _spreadsheet_copy(self,event=None):
        if self.spreadsheet_selected is None:return 'break'
        a=self.spreadsheet_range_anchor or self.spreadsheet_selected
        b=self.spreadsheet_range_end or a
        r0,r1=sorted((a[0],b[0]));c0,c1=sorted((a[1],b[1]))
        cells=self.material_spreadsheet['cells']
        value='\n'.join('\t'.join(str(cells.get(cell_id(r,c),'')) for c in range(c0,c1+1)) for r in range(r0,r1+1))
        self.root.clipboard_clear();self.root.clipboard_append(value)
        return 'break'

    def _spreadsheet_paste(self,event=None):
        if self.spreadsheet_selected is None:return 'break'
        try:text=self.root.clipboard_get()
        except tk.TclError:return 'break'
        r0,c0=self.spreadsheet_selected
        values=[line.split('\t') for line in text.splitlines()]
        self._run_project_edit('spreadsheet:paste',
            lambda: paste_block(self.material_spreadsheet, r0, c0, values))
        self._refresh_spreadsheet();self._draw_spreadsheet_selection()
        return 'break'
