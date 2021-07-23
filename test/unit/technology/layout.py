# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
# type: ignore
import unittest

from pdkmaster.technology import mask as _msk, net as _net, geometry as _geo
from pdkmaster.design import layout as _lay, circuit as _ckt

class TestNet(_net.Net):
    def __init__(self, name: str):
        super().__init__(name)

class LayoutTest(unittest.TestCase):
    def test_maskshapessublayout(self):
        m1 = _msk.DesignMask("mask1", fill_space="no")
        m2 = _msk.DesignMask("mask2", fill_space="no")
        n1 = TestNet("net1")
        n2 = TestNet("net2")
        p = _geo.Point(x=3.0, y=-2.0)
        rot = "90"
        r1 = _geo.Rect(left=-3.0, bottom=-1.0, right=-1.0, top=1.0)
        r2 = _geo.Rect(left=1.0, bottom=-1.0, right=3.0, top=1.0)
        ms1 = _geo.MaskShape(mask=m1, shape=r1)
        ms2 = _geo.MaskShape(mask=m2, shape=r2)
        ms4 = _geo.MaskShape(mask=m1, shape=_geo.MultiShape(shapes=(r1, r2)))
        mssl1 = _lay.MaskShapesSubLayout(
            net=n1, shapes=_geo.MaskShapes(ms1),
        )
        mssl2 = _lay.MaskShapesSubLayout(
            net=None, shapes=_geo.MaskShapes(ms1),
        )
        mssl3 = _lay.MaskShapesSubLayout(
            net=n1, shapes=_geo.MaskShapes((ms1, ms2)),
        )
        mssl4 = mssl1.dup()
        mssl4.add_shape(shape=ms2)

        self.assertNotEqual(mssl1, "")
        self.assertNotEqual(mssl1, mssl2)
        with self.assertRaises(TypeError):
            hash(mssl1)
        self.assertNotEqual(mssl1, mssl4)
        self.assertEqual(mssl3, mssl4)
        # Get coverage for _hier_strs_, don't check output
        s = "\n".join(mssl1._hier_strs_)

        mssl5 = mssl3.moved(dx=p.x, dy=p.y, rotation="no")
        mssl4.move(dx=p.x, dy=p.y, rotation="no")

        self.assertNotEqual(mssl3, mssl5)
        self.assertEqual(mssl4, mssl5)

        mssl6 = mssl3.moved(dx=p.x, dy=p.y, rotation=rot)
        mssl7 = mssl3.dup()
        mssl7.move(dx=0.0, dy=0.0, rotation=rot)
        mssl7.move(dx=p.x, dy=p.y, rotation="no")

        self.assertEqual(mssl6, mssl7)
