"""Calibration and photograph registration must not silently alter roof geometry."""
import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from PIL import Image
from mixins.zone_tools import ZoneToolsMixin
from mixins.installation_geometry import InstallationGeometryMixin
from project_store import write_project,validate_project


class CalibrationTest(unittest.TestCase):
    def new_model(self):
        model=SimpleNamespace(
            px_per_mm=2.,
            roof_pil_img=Image.new('RGB',(100,80),'white'),
            roof_zones=[dict(id=1,x1=10.,y1=20.,x2=210.,y2=120.,w_mm=100.,h_mm=50.)],
            distance_markers=[dict(point=(20.,30.),nearest_point=(120.,30.),distance_mm=50.)],
            scale_p1=None,scale_p2=None,scale_length_mm=0.,
            _align_replacement_image=False,
            _update_zones_from_scale=Mock(),_invalidate_cable_routes=Mock(),draw_grid=Mock(),
            _get_image_resample_filter=lambda:Image.Resampling.NEAREST,
        )
        model._recalculate_dimensions_after_scale_change=lambda:ZoneToolsMixin._recalculate_dimensions_after_scale_change(model)
        return model

    def test_recalibrating_same_photo_updates_every_stored_length_and_live_dimension(self):
        m=self.new_model()
        aligned=ZoneToolsMixin._apply_scale_reference(m,(0,0),(100,0),100.)
        self.assertFalse(aligned)
        self.assertEqual(m.px_per_mm,1.)
        self.assertEqual((m.roof_zones[0]['w_mm'],m.roof_zones[0]['h_mm']),(200.,100.))
        self.assertEqual(m.distance_markers[0]['distance_mm'],100.)
        self.assertEqual(m.roof_pil_img.size,(100,80))
        self.assertEqual(m.scale_length_mm,100.)
        m._update_zones_from_scale.assert_called_once()
        m._invalidate_cable_routes.assert_called_once()
        self.assertEqual(m.scale_p2,(100,0))

        class LabelRenderer:
            px_per_mm=m.px_per_mm
            canvas=SimpleNamespace(create_line=Mock())
            _draw_text_with_bg=Mock()
        renderer=LabelRenderer()
        InstallationGeometryMixin._draw_dimension(renderer,
            {'p1':(10.,20.),'p2':(210.,20.),'label':(110.,5.),'axis':'aligned'},2.5)
        self.assertEqual(renderer._draw_text_with_bg.call_args.kwargs['text'],'200 mm')

    def test_matching_replacement_photo_does_not_change_existing_project_scale(self):
        m=self.new_model()
        m._align_replacement_image=True
        self.assertTrue(ZoneToolsMixin._apply_scale_reference(m,(0.,0.),(100.,0.),100.))
        self.assertEqual(m.px_per_mm,2.)
        self.assertEqual(m.roof_pil_img.size,(200,160))
        self.assertEqual(m.scale_p2,(200,0))
        self.assertEqual(m.roof_zones[0]['w_mm'],100.)
        self.assertEqual(m.distance_markers[0]['distance_mm'],50.)
        m._update_zones_from_scale.assert_not_called()


    def test_jpg_export_background_is_shifted_but_plan_stays_fixed(self):
        from unittest.mock import patch
        from plan_renderer import render_plan
        app=SimpleNamespace(
            roof_pil_img=Image.new('RGB',(30,30),'#101010'),
            roof_image_offset=(40.,50.), roof_polygons=[], measures=[],
            strings={}, cable_paths=[], inverter_positions={}, panels={})
        with tempfile.TemporaryDirectory() as folder, patch('plan_renderer.scene', return_value=([],(0.,0.,150.,120.))):
            path=Path(folder)/'check.jpg'
            render_plan(app,path,scale=2)
            with Image.open(path) as img:
                # Photo is located at x=40..70, y=50..80 in world coordinates.
                left,top=-12.,-12.
                def sample(x,y):return img.getpixel((round((x-left)*2),round((y-top)*2)))
                self.assertGreater(sample(10,10)[0],235)
                self.assertLess(sample(50,60)[0],50)
                self.assertGreater(sample(90,90)[0],235)

    def test_image_offset_survives_json_validation(self):
        payload=validate_project({'roof_image_offset':[18.5,-4.25]})
        self.assertEqual(payload['roof_image_offset'],[18.5,-4.25])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'project.json'
            write_project(path,payload)
            self.assertEqual(json.loads(path.read_text())['roof_image_offset'],[18.5,-4.25])
        with self.assertRaises(ValueError):
            validate_project({'roof_image_offset':['NaN',0]})


if __name__=='__main__':unittest.main()
