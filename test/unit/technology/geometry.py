# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
# type: ignore
from itertools import product
import unittest
from typing import Iterable

from shapely.geometry.polygon import Polygon

from pdkmaster import _util
from pdkmaster.technology import mask as _msk, geometry as _geo

class GeometryTest(unittest.TestCase):
    def test_rotation(self):
        self.assertEqual(_geo.Rotation.No, _geo.Rotation.R0)
        for name, rot in (
            ("no", _geo.Rotation.R0),
            ("90", _geo.Rotation.R90),
            ("180", _geo.Rotation.R180),
            ("270", _geo.Rotation.R270),
            ("mirrorx", _geo.Rotation.MX),
            ("mirrorx&90", _geo.Rotation.MX90),
            ("mirrory", _geo.Rotation.MY),
            ("mirrory&90", _geo.Rotation.MY90),
        ):
            self.assertEqual(_geo.Rotation.from_name(name), rot)
    
    def test_abstract(self):
        with self.assertRaisesRegex(
            TypeError, "^Can't instantiate abstract class _Shape",
        ):
            _geo._Shape()
        with self.assertRaisesRegex(
            TypeError, "^Can't instantiate abstract class _Rectangular",
        ):
            _geo._Rectangular()
        with self.assertRaisesRegex(
            TypeError, "^Can't instantiate abstract class _PointsShape",
        ):
            _geo._PointsShape()

    def test_pointsshape(self): # Also test _Shape
        class ShapeTest(_geo._PointsShape):
            def __init__(self):
                super().__init__()

            @property
            def pointsshapes(self) -> Iterable[_geo._PointsShape]:
                return super().pointsshapes

            @property
            def bounds(self) -> _geo._Rectangular:
                return super().bounds

            def move(self, *, dxy: _geo.Point):
                return super().move(dxy=dxy)
            
            def rotate(self, *, rotation: _geo.Rotation) -> _geo._Shape:
                return super().rotate(rotation=rotation)

            @property
            def area(self) -> float:
                return super().area

            def __eq__(self, o: object) -> bool:
                return super().__eq__(o)

            @property
            def points(self) -> Iterable[_geo.Point]:
                return super().points

        t = ShapeTest()
        with self.assertRaises(NotImplementedError):
            t.pointsshapes
        with self.assertRaises(NotImplementedError):
            t.bounds
        with self.assertRaises(NotImplementedError):
            t.move(dxy=_geo.origin)
        with self.assertRaises(NotImplementedError):
            t.rotate(rotation=_geo.Rotation.R0)
        with self.assertRaises(NotImplementedError):
            t.area
        with self.assertRaises(NotImplementedError):
            _geo._Shape.__eq__(t, None)
        with self.assertRaises(NotImplementedError):
            t.points
        with self.assertRaises(NotImplementedError):
            _geo._Shape.__hash__(t)

        with self.assertRaisesRegex(
            TypeError,
            f"unsupported operand type\(s\) for \+: '{ShapeTest}' and '{int}'"
        ):
            t + 1
        with self.assertRaisesRegex(
            TypeError,
            f"unsupported operand type\(s\) for \-: '{ShapeTest}' and '{int}'"
        ):
            t - 1

        self.assertNotEqual(t, 1)

    def test_rectangular(self):
        class RectangularTest(_geo._Rectangular):
            def __init__(self):
                super().__init__()

            # _Shape abstract methods
            @property
            def pointsshapes(self) -> Iterable[_geo._PointsShape]:
                return super().pointsshapes
            @property
            def bounds(self) -> _geo._Rectangular:
                return super().bounds
            def move(self, *, dxy: _geo.Point):
                return super().move(dxy)
            def rotate(self, *, rotation: _geo.Rotation) -> _geo._Shape:
                return super().rotate(rotation)
            @property
            def area(self) -> float:
                return super().area
            def __eq__(self, o: object) -> bool:
                return super().__eq__(o)

            @property
            def left(self) -> float:
                return super().left
            @property
            def bottom(self) -> float:
                return super().bottom
            @property
            def right(self) -> float:
                return super().right
            @property
            def top(self) -> float:
                return super().top

        t = RectangularTest()
        with self.assertRaises(NotImplementedError):
            t.left
        with self.assertRaises(NotImplementedError):
            t.bottom
        with self.assertRaises(NotImplementedError):
            t.right
        with self.assertRaises(NotImplementedError):
            t.top
        with self.assertRaises(NotImplementedError):
            self.assertNotEqual(t, 1)

    def test_point(self):
        p = _geo.Point(x=0.0, y=0.0)
        self.assertTrue((abs(p.x) < _geo.epsilon) and (abs(p.y) < _geo.epsilon))
        self.assertEqual(p.area, 0.0)
        self.assertNotEqual(p, 1)

        p += _geo.Point.from_float(point=(1.0, 2.0))
        self.assertEqual(p, _geo.Point(x=1.0, y=2.0))

        p = _geo.Point.from_point(point=p, x=-1.0)
        self.assertEqual(p, _geo.Point(x=-1.0, y=2.0))

        p = _geo.Point.from_point(point=p, y=-p.y)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))

        first = True
        for p2 in p.pointsshapes:
            self.assertTrue(first)
            first = False
            self.assertEqual(p2, p)
        first = True
        for p2 in p.points:
            self.assertTrue(first)
            first = False
            self.assertEqual(p2, p)

        self.assertEqual(p - p, _geo.Point(x=0.0, y=0.0))

        self.assertEqual(-2*p, _geo.Point(x=2.0, y=4.0))
        with self.assertRaisesRegex(
            TypeError,
            f"unsupported operand type\(s\) for \*: {_geo.Point} and {_geo.Point}",
        ):
            p*p

        p2 = p.rotate(rotation=_geo.Rotation.R0)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p, p2)
        p2 = p.rotate(rotation=_geo.Rotation.R90)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p2, _geo.Point(x=2.0, y=-1.0))
        p2 = p.rotate(rotation=_geo.Rotation.R180)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p2, _geo.Point(x=1.0, y=2.0))
        p2 = p.rotate(rotation=_geo.Rotation.R270)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p2, _geo.Point(x=-2.0, y=1.0))
        p2 = p.rotate(rotation=_geo.Rotation.MX)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p2, _geo.Point(x=1.0, y=-2.0))
        p2 = p.rotate(rotation=_geo.Rotation.MX90)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p2, _geo.Point(x=2.0, y=1.0))
        p2 = p.rotate(rotation=_geo.Rotation.MY)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p2, _geo.Point(x=-1.0, y=2.0))
        p2 = p.rotate(rotation=_geo.Rotation.MY90)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p2, _geo.Point(x=-2.0, y=-1.0))

        self.assertEqual(str(p), f"({str(p.x)},{str(p.y)})")
        self.assertEqual(repr(p), f"Point(x={p.x},y={p.y})")

    def test_line(self):
        p1 = _geo.Point(x=0.0, y=0.0)
        p2 = _geo.Point(x=1.0, y=-1.0)
        l = _geo.Line(point1=p1, point2=p2)

        self.assertEqual(l.point1, p1)
        self.assertEqual(l.point2, p2)
        self.assertEqual(l.area, 0.0)

        first = True
        for l2 in l.pointsshapes:
            self.assertTrue(first)
            first = False
            self.assertEqual(l, l2)
        ps = l.points
        self.assertEqual(len(ps), 2)
        self.assertEqual(ps[0], p1)
        self.assertEqual(ps[1], p2)

        self.assertEqual(l.bounds, l)

        self.assertEqual(
            l.rotate(rotation=_geo.Rotation.R90),
            _geo.Line(
                point1=p1.rotate(rotation=_geo.Rotation.R90),
                point2=p2.rotate(rotation=_geo.Rotation.R90),
            ),
        )

        dxy = _geo.Point(x=1.0, y=1.0)
        self.assertEqual(
            l.move(dxy=dxy),
            _geo.Line(point1=p1.move(dxy=dxy), point2=p2.move(dxy=dxy)),
        )

        self.assertEqual(str(l), f"{p1}-{p2}")
        self.assertEqual(repr(l), f"Line(point1={p1!r},point2={p2!r})")

    def test_polygon(self):
        with self.assertRaisesRegex(
            ValueError, "Last point has to be the same as the first point"
        ):
            _geo.Polygon(points=(
                _geo.Point(x=0.0, y=0.0), _geo.Point(x=0.0, y=1.0),
                _geo.Point(x=1.0, y=1.0), _geo.Point(x=1.0, y=0.0),
            ))
        with self.assertRaisesRegex(
            ValueError, "Polygon with only colinear points not allowed"
        ):
            _geo.Polygon(points=(
                _geo.Point(x=0.0, y=0.0), _geo.Point(x=0.0, y=1.0),
                _geo.Point(x=0.0, y=0.5), _geo.Point(x=0.0, y=0.0),
            ))
            
        poly1 = _geo.Polygon(points=(
            _geo.Point(x=0.0, y=0.0), _geo.Point(x=0.0, y=1.0),
            _geo.Point(x=1.0, y=1.0), _geo.Point(x=1.0, y=0.0),
            _geo.Point(x=0.0, y=0.0),
        ))
        poly2 = _geo.Polygon.from_floats(points=(
            (0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0),
        ))
        line1 = _geo.Line(
            point1=_util.first(poly1.points),
            point2=_util.nth(poly1.points, 1),
        )
        line2 = _geo.Line(
            point1=_util.first(poly1.points),
            point2=_util.nth(poly1.points, 2),
        )

        with self.assertRaises(NotImplementedError):
            poly1.area
        with self.assertRaisesRegex(
            TypeError, (
                "unsupported operand type\(s\) for \+: "
                f"'{_geo.Polygon}' and '{_geo.Polygon}'"
            )
        ):
            poly3 = poly1 + poly2

        self.assertEqual(poly1, poly2)
        self.assertNotEqual(poly1, line1)
        self.assertNotEqual(poly1, line2)
        self.assertEqual(
            poly1.bounds,
            _geo.Rect(left=0.0, bottom=0.0, right=1.0, top=1.0),
        )
        self.assertNotEqual(line1, poly1)
        self.assertEqual(
            poly1.move(dxy=_geo.Point(x=1.0, y=1.0)),
            _geo.Polygon.from_floats(points=(
                (1.0, 1.0), (1.0, 2.0), (2.0, 2.0), (2.0, 1.0), (1.0, 1.0),
            ))
        )
        self.assertEqual(
            poly1.rotate(rotation=_geo.Rotation.R90),
            _geo.Polygon.from_floats(points=(
                (0.0, 0.0), (-1.0, 0.0), (-1.0, 1.0), (0.0, 1.0), (0.0, 0.0),
            ))
        )

    def test_rect(self):
        with self.assertRaises(AssertionError):
            _geo.Rect(left=0.0, bottom=0.0, right=0.0, top=1.0)
        with self.assertRaises(AssertionError):
            _geo.Rect.from_size(width=1.0, height=-1.0)

        rect1 = _geo.Rect(left=-1.0, bottom=-1.0, right=1.0, top=1.0)
        rect2 = _geo.Rect.from_size(width=2.0, height=2.0)
        rect3 = _geo.Rect.from_corners(
            corner1=_geo.Point(x=0.0, y=0.0), corner2=_geo.Point(x=2.0, y=2.0),
        )
        rect4 = _geo.Rect.from_floats(values=(0.0, 0.0, 2.0, 2.0))
        rect5 = _geo.Rect.from_rect(rect=rect1, bias=1.0)
        rect6 = _geo.Rect.from_rect(rect=rect3, left=-2.0, bottom=-2.0)
        rect7 = _geo.Rect.from_float_corners(corners=((-2.0, -2.0), (2.0, 2.0)))

        with self.assertRaisesRegex(
            RuntimeError,
            f"Internal error: unsupported rotation 'None'"
        ):
            rect1.rotate(rotation=None)

        self.assertEqual(
            str(rect1), "Rect(left=-1.0,bottom=-1.0,right=1.0,top=1.0)",
        )
        self.assertEqual(
            _util.nth(rect1.points, 1),
            _geo.Point(x=rect1.left, y=rect1.top),
        )
        self.assertEqual(rect1, rect2)
        self.assertNotEqual(rect1, 1)
        self.assertEqual(rect1, rect1.rotate(rotation=_geo.Rotation.MX90))
        self.assertEqual(round(rect1.area, 6), 4.0)
        self.assertEqual(rect3, rect4)
        self.assertEqual(rect1.move(dxy=_geo.Point(x=1.0, y=1.0)), rect3)
        self.assertEqual(rect5, rect6)
        self.assertEqual(rect5, rect7)

    def test_multishape(self):
        p = _geo.Point(x=1.0, y=-1.0)
        p2 = _geo.Point(x=1.0, y=1.0)
        l = _geo.Line(point1=_geo.Point(x=0.0, y=0.0), point2=_geo.Point(x=1.0, y=1.0))
        r = _geo.Rect(left=-2.0, bottom=-3.0, right=2.0, top=-2.0)
        
        with self.assertRaisesRegex(
            ValueError, "MultiShape has to consist of more than one shape",
        ):
            _geo.MultiShape(shapes=(p,))

        ms1 = _geo.MultiShape(shapes=(p, l, r))
        ms2 = _geo.MultiShape(shapes=(l, r, p))
        ms3 = _geo.MultiShape(shapes=(p, l))
        ms4 = _geo.MultiShape(shapes=(p, p2))

        self.assertNotEqual(ms1, "")
        self.assertEqual(ms1, ms2)
        self.assertEqual(hash(ms1), hash(ms2))
        self.assertEqual(len(ms1), 3)
        self.assertTrue(l in ms2)
        self.assertAlmostEqual(ms1.area, 4.0, 6)
        self.assertNotEqual(ms1, ms3)
        self.assertEqual(set(ms1), {p, l, r})
        self.assertEqual(
            ms1.move(dxy=p),
            _geo.MultiShape(shapes=(r + p, l + p, 2*p)),
        )
        rot = _geo.Rotation.MY
        self.assertEqual(
            ms1.rotate(rotation=rot),
            _geo.MultiShape(shapes=(
                r.rotate(rotation=rot), l.rotate(rotation=rot),
                p.rotate(rotation=rot),
            )),
        )
        self.assertEqual(
            ms1.bounds,
            _geo.Rect(left=-2.0, bottom=-3.0, right=2.0, top=1.0),
        )
        self.assertEqual(ms4.bounds, _geo.Line(point1=p, point2=p2))

    def test_repeatedshape(self):
        s = _geo.Rect.from_size(width=2.0, height=2.0)
        dxy1 = _geo.Point(x=5.0, y=0.0)
        dxy2 = _geo.Point(x=0.0, y=5.0)
        p = _geo.Point(x=0.0, y=1.0)

        with self.assertRaisesRegex(
            ValueError, "n has to be equal to or higher than 2, not '1'"
        ):
            _geo.RepeatedShape(shape=s, offset0=_geo.origin, n=1, n_dxy=dxy1)
        with self.assertRaisesRegex(
            ValueError, "m has to be equal to or higher than 1, not '0'"
        ):
            _geo.RepeatedShape(shape=s, offset0=_geo.origin, n=2, n_dxy=dxy1, m=0)
        with self.assertRaisesRegex(
            ValueError, "m_dxy may not be None if m > 1"
        ):
            _geo.RepeatedShape(shape=s, offset0=_geo.origin, n=2, n_dxy=dxy1, m=2)
        
        rp1 = _geo.RepeatedShape(
            shape=s, offset0=_geo.origin, n=2, n_dxy=dxy1,
        )
        rp2 = s.repeat(
            offset0=_geo.origin, n=2, n_dxy=dxy1,
        )
        rp3 = _geo.RepeatedShape(
            shape=s, offset0=p, n=2, n_dxy=dxy1,
        )
        rp4 = _geo.RepeatedShape(
            shape=s, offset0=_geo.origin, n=2, n_dxy=dxy1, m=2, m_dxy=dxy2,
        )
        rp5 = _geo.RepeatedShape(
            shape=s, offset0=_geo.origin, n=2, n_dxy=dxy2, m=2, m_dxy=dxy1,
        )
        rp6 = _geo.RepeatedShape(
            shape=s, offset0=_geo.origin, n=2, n_dxy=dxy1, m=3, m_dxy=dxy2,
        )
        rp7 = _geo.RepeatedShape(
            shape=s, offset0=_geo.origin, n=3, n_dxy=dxy2, m=2, m_dxy=dxy1,
        )
        rp8 = _geo.RepeatedShape(
            shape=s, offset0=_geo.origin, n=2, n_dxy=dxy2, m=3, m_dxy=dxy1,
        )

        self.assertAlmostEqual(rp1.area, 2*s.area, 6)
        self.assertNotEqual(rp1, False)
        self.assertEqual(rp1, rp2)
        self.assertEqual(hash(rp1), hash(rp2))
        self.assertNotEqual(rp1, rp3)
        self.assertEqual(rp1.move(dxy=p), rp3)
        self.assertNotEqual(rp1, rp4)
        self.assertEqual(rp4, rp5)
        self.assertEqual(rp6, rp7)
        self.assertEqual(hash(rp6), hash(rp7))
        self.assertNotEqual(rp6, rp8)

        ms1 = _geo.MultiShape(shapes=(s, s+dxy1))
        ms2 = _geo.MultiShape(shapes=rp1.pointsshapes)
        ms3 = _geo.MultiShape(shapes=(
            s + i*dxy1 + j*dxy2 for i, j in product(range(2), range(2))
        ))
        ms4 = _geo.MultiShape(shapes=rp4.pointsshapes)
        rot = _geo.Rotation.MY90
        ms5 = _geo.MultiShape(shapes=rp1.rotate(rotation=rot).pointsshapes)

        self.assertEqual(ms1, ms2)
        self.assertEqual(rp1.bounds, ms1.bounds)
        self.assertEqual(ms3, ms4)
        self.assertEqual(ms5, ms2.rotate(rotation=rot))
        self.assertEqual(rp4.bounds, ms4.bounds)

        self.assertIsInstance(repr(rp1), str) # __repr__ coverage

    def test_maskshape(self):
        p = _geo.Point(x=0.0, y=1.0)
        l = _geo.Line(point1=_geo.origin, point2=p)
        r1 = _geo.Rect.from_size(width=2.0, height=2.0)
        r2 = _geo.Rect.from_size(width=2.0, height=2.0) # Same r1 to test equality
        m1 = _msk.DesignMask("mask1", fill_space="no")
        m2 = _msk.DesignMask("mask2", fill_space="no")
        ms1 = _geo.MaskShape(mask=m1, shape=r1)
        ms2 = _geo.MaskShape(mask=m2, shape=r1)
        ms3 = _geo.MaskShape(mask=m1, shape=r2)
        ms4 = _geo.MaskShape(mask=m1, shape=l)
        ms5 = _geo.MaskShape(mask=m1, shape=(r1 + p))
        rot = _geo.Rotation.R270
        ms6 = _geo.MaskShape(mask=m1, shape=l.rotate(rotation=rot))

        self.assertEqual(ms1.mask, m1)
        self.assertEqual(ms1.shape, r1)
        self.assertEqual(ms1.bounds, r1)
        self.assertNotEqual(ms1, [])
        self.assertIsInstance(repr(ms1), str) # coverage of __repr__()
        self.assertAlmostEqual(ms1.area, r1.area, 6)
        self.assertNotEqual(ms1, ms2)
        self.assertEqual(ms1, ms3)
        self.assertEqual(hash(ms1), hash(ms3))
        self.assertNotEqual(ms1, ms4)
        self.assertEqual(ms1.move(dxy=p), ms5)
        self.assertEqual(ms4.rotate(rotation=rot), ms6)
