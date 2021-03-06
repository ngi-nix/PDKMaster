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

        rot = _geo.Rotation.MX
        with self.assertRaisesRegex(
            TypeError, (
                "unsupported operand type\(s\) for \*\: "
                f"'{rot.__class__.__name__}' and 'int'"
            )
        ):
            rot * 2

        r0 = _geo.Rotation.R0

        p = _geo.Point(x=1.0, y=-2.0)
        rot = _geo.Rotation.MY
        self.assertEqual(p*r0, p)
        self.assertEqual(rot*p, p.rotated(rotation=rot))

        m = _msk.DesignMask("mask", fill_space="no")
        r = _geo.Rect.from_size(width=1.0, height=3.0)
        ms = _geo.MaskShape(mask=m, shape=r)
        mss = _geo.MaskShapes(ms)
        rot = _geo.Rotation.R270

        r_r = rot*r
        r_ms = ms*rot
        r_mss = rot*mss
        self.assertEqual(r0*r, r)
        self.assertEqual(r0*ms, ms)
        self.assertEqual(mss*r0, mss)
        self.assertEqual(r_r, r_ms.shape)
        self.assertEqual(r_ms, r_mss[0])

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

            def moved(self, *, dxy: _geo.Point):
                return super().moved(dxy=dxy)
            
            def rotated(self, *, rotation: _geo.Rotation) -> _geo._Shape:
                return super().rotated(rotation=rotation)

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
            t.moved(dxy=_geo.origin)
        with self.assertRaises(NotImplementedError):
            t.rotated(rotation=_geo.Rotation.R0)
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
            f"unsupported operand type\(s\) for \+: "
            f"'{t.__class__.__name__}' and '{int.__name__}'"
        ):
            t + 1
        with self.assertRaisesRegex(
            TypeError,
            f"unsupported operand type\(s\) for \-: "
            f"'{t.__class__.__name__}' and '{int.__name__}'"
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
            def moved(self, *, dxy: _geo.Point):
                return super().moved(dxy)
            def rotated(self, *, rotation: _geo.Rotation) -> _geo._Shape:
                return super().rotated(rotation)
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
        with self.assertRaisesRegex(
            TypeError,
            "unsupported operand type\(s\) for \+: "
            f"'{p.__class__.__name__}' and 'str'",
        ):
            p + "a"
        with self.assertRaisesRegex(
            TypeError,
            "unsupported operand type\(s\) for \-: "
            f"'float' and '{p.__class__.__name__}'",
        ):
            3.14 - p
        with self.assertRaisesRegex(
            TypeError,
            "unsupported operand type\(s\) for \-: "
            f"'{p.__class__.__name__}' and 'float'",
        ):
            p - 3.14

        self.assertEqual(-2*p, _geo.Point(x=2.0, y=4.0))
        with self.assertRaisesRegex(
            TypeError,
            f"unsupported operand type\(s\) for \*: "
            f"'{p.__class__.__name__}' and '{p.__class__.__name__}'",
        ):
            p*p

        p2 = p.rotated(rotation=_geo.Rotation.R0)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p, p2)
        p2 = p.rotated(rotation=_geo.Rotation.R90)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p2, _geo.Point(x=2.0, y=-1.0))
        p2 = p.rotated(rotation=_geo.Rotation.R180)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p2, _geo.Point(x=1.0, y=2.0))
        p2 = p.rotated(rotation=_geo.Rotation.R270)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p2, _geo.Point(x=-2.0, y=1.0))
        p2 = p.rotated(rotation=_geo.Rotation.MX)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p2, _geo.Point(x=1.0, y=-2.0))
        p2 = p.rotated(rotation=_geo.Rotation.MX90)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p2, _geo.Point(x=2.0, y=1.0))
        p2 = p.rotated(rotation=_geo.Rotation.MY)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p2, _geo.Point(x=-1.0, y=2.0))
        p2 = p.rotated(rotation=_geo.Rotation.MY90)
        self.assertEqual(p, _geo.Point(x=-1.0, y=-2.0))
        self.assertEqual(p2, _geo.Point(x=-2.0, y=-1.0))
        rot = _geo.Rotation.MY90
        self.assertEqual(p*rot, rot*p)

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
            l.rotated(rotation=_geo.Rotation.R90),
            _geo.Line(
                point1=p1.rotated(rotation=_geo.Rotation.R90),
                point2=p2.rotated(rotation=_geo.Rotation.R90),
            ),
        )

        dxy = _geo.Point(x=1.0, y=1.0)
        self.assertEqual(
            l.moved(dxy=dxy),
            _geo.Line(point1=p1.moved(dxy=dxy), point2=p2.moved(dxy=dxy)),
        )
        self.assertEqual(-dxy + l, l - dxy)

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
                f"'{poly1.__class__.__name__}' and '{poly2.__class__.__name__}'"
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
            poly1.moved(dxy=_geo.Point(x=1.0, y=1.0)),
            _geo.Polygon.from_floats(points=(
                (1.0, 1.0), (1.0, 2.0), (2.0, 2.0), (2.0, 1.0), (1.0, 1.0),
            ))
        )
        self.assertEqual(
            poly1.rotated(rotation=_geo.Rotation.R90),
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
            rect1.rotated(rotation=None)

        self.assertEqual(
            str(rect1), "Rect(left=-1.0,bottom=-1.0,right=1.0,top=1.0)",
        )
        self.assertEqual(
            _util.nth(rect1.points, 1),
            _geo.Point(x=rect1.left, y=rect1.top),
        )
        self.assertEqual(rect1, rect2)
        self.assertNotEqual(rect1, 1)
        self.assertEqual(rect1, rect1.rotated(rotation=_geo.Rotation.MX90))
        self.assertEqual(round(rect1.area, 6), 4.0)
        self.assertEqual(rect3, rect4)
        self.assertEqual(rect1.moved(dxy=_geo.Point(x=1.0, y=1.0)), rect3)
        self.assertEqual(rect5, rect6)
        self.assertEqual(rect5, rect7)

    def test_multipartshape(self):
        r_all = _geo.Rect(left=-2.0, bottom=-1.0, right=1.0, top=1.0)
        r_left = _geo.Rect(left=-2.0, bottom=-1.0, right=0.0, top=1.0)
        r_right = _geo.Rect(left=0.0, bottom=-1.0, right=1.0, top=1.0)
        mps = _geo.MultiPartShape(fullshape=r_all, parts=(r_left, r_right))

        self.assertEqual(_util.first(mps.pointsshapes), r_all)
        self.assertEqual(mps.bounds, r_all)

        part0 = _util.first(mps.parts)
        part1 = _util.nth(mps.parts, 1)

        self.assertEqual(part0.partshape, r_left)
        self.assertEqual(tuple(part0.points), tuple(r_left.points))
        self.assertEqual(part0.area, r_left.area)
        self.assertEqual(part1.multipartshape, mps)
        self.assertEqual(tuple(part1.pointsshapes), (r_right,))
        self.assertEqual(part1.bounds, r_right)
        self.assertEqual(mps.area, part0.area + part1.area)

        p = _geo.Point(x=-2.0, y=3.5)
        part0_moved = part0 + p
        self.assertEqual(mps + p, mps.moved(dxy=p))
        self.assertEqual(part0_moved.multipartshape, p + mps)

        rot = _geo.Rotation.MX90
        part1_rotated = rot*part1
        self.assertEqual(rot * mps, mps.rotated(rotation=rot))
        self.assertEqual(part1_rotated.multipartshape, mps*rot)

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
        ms3 = _geo.MultiShape(shapes=(l, _geo.MultiShape(shapes=(r, p))))
        ms4 = _geo.MultiShape(shapes=(p, l))
        ms5 = _geo.MultiShape(shapes=(p, p2))

        self.assertNotEqual(ms1, "")
        self.assertEqual(ms1, ms2)
        self.assertEqual(ms1, ms3)
        self.assertEqual(hash(ms1), hash(ms2))
        self.assertEqual(len(ms1), 3)
        self.assertTrue(l in ms2)
        self.assertAlmostEqual(ms1.area, 4.0, 6)
        self.assertNotEqual(ms1, ms4)
        self.assertEqual(set(ms1), {p, l, r})
        self.assertEqual(
            ms1.moved(dxy=p),
            _geo.MultiShape(shapes=(r + p, l + p, 2*p)),
        )
        rot = _geo.Rotation.MY
        self.assertEqual(
            ms1.rotated(rotation=rot),
            _geo.MultiShape(shapes=(
                r.rotated(rotation=rot), l.rotated(rotation=rot),
                p.rotated(rotation=rot),
            )),
        )
        self.assertEqual(
            ms1.bounds,
            _geo.Rect(left=-2.0, bottom=-3.0, right=2.0, top=1.0),
        )
        self.assertEqual(ms5.bounds, _geo.Line(point1=p, point2=p2))
        self.assertEqual(
            str(ms1),
            "(Rect(left=-2.0,bottom=-3.0,right=2.0,top=-2.0),(1.0,-1.0),(0.0,0.0)-(1.0,1.0))",
        )
        self.assertEqual(
            repr(ms1),
            "MultiShape(shapes=(Rect(left=-2.0,bottom=-3.0,right=2.0,top=-2.0),Point(x=1.0,y=-1.0),Line(point1=Point(x=0.0,y=0.0),point2=Point(x=1.0,y=1.0))))",
        )

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
        self.assertEqual(rp1.moved(dxy=p), rp3)
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
        ms5 = _geo.MultiShape(shapes=rp1.rotated(rotation=rot).pointsshapes)

        self.assertEqual(ms1, ms2)
        self.assertEqual(rp1.bounds, ms1.bounds)
        self.assertEqual(ms3, ms4)
        self.assertEqual(ms5, ms2.rotated(rotation=rot))
        self.assertEqual(rp4.bounds, ms4.bounds)

        self.assertIsInstance(repr(rp1), str) # __repr__ coverage

    def test_arrayshape(self):
        via = _geo.Rect.from_size(width=1.0, height=1.0)
        orig = _geo.Point(x=-1.0, y=-1.0)
        dx = 2.0
        dxy_x = _geo.Point(x=dx, y=0.0)
        dy = 3.0
        dxy_y = _geo.Point(x=0.0, y=dy)

        with self.assertRaises(ValueError):
            _geo.ArrayShape(shape=via, offset0=orig, rows=-1, columns=4)
        with self.assertRaises(ValueError):
            _geo.ArrayShape(shape=via, offset0=orig, rows=1, columns=1)
        with self.assertRaises(ValueError):
            _geo.ArrayShape(shape=via, offset0=orig, rows=2, columns=1)
        with self.assertRaises(ValueError):
            _geo.ArrayShape(shape=via, offset0=orig, rows=1, columns=2)

        self.assertEqual(
            _geo.ArrayShape(shape=via, offset0=orig, rows=3, columns=1, pitch_x=dx, pitch_y=dy),
            _geo.RepeatedShape(shape=via, offset0=orig, n=3, n_dxy=dxy_y),
        )
        self.assertEqual(
            _geo.ArrayShape(shape=via, offset0=orig, rows=1, columns=2, pitch_x=dx, pitch_y=dy),
            _geo.RepeatedShape(shape=via, offset0=orig, n=2, n_dxy=dxy_x),
        )
        self.assertEqual(
            _geo.ArrayShape(shape=via, offset0=orig, rows=3, columns=2, pitch_x=dx, pitch_y=dy),
            _geo.RepeatedShape(shape=via, offset0=orig, n=3, n_dxy=dxy_y, m=2, m_dxy=dxy_x),
        )

        ar = _geo.ArrayShape(shape=via, offset0=orig, rows=3, columns=4, pitch_x=dx, pitch_y=dy)
        self.assertEqual(ar.rows, 3)
        self.assertEqual(ar.columns, 4)
        self.assertEqual(ar.pitch_x, dx)
        self.assertEqual(ar.pitch_y, dy)

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
        ms6 = _geo.MaskShape(mask=m1, shape=l.rotated(rotation=rot))

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
        self.assertEqual(ms1.moved(dxy=p), ms5)
        self.assertEqual(ms4.rotated(rotation=rot), ms6)

    def test_maskshapes(self):
        m1 = _msk.DesignMask("mask1", fill_space="no")
        m2 = _msk.DesignMask("mask2", fill_space="no")
        p = _geo.Point(x=3.0, y=-2.0)
        rot = _geo.Rotation.R90
        r1 = _geo.Rect(left=-3.0, bottom=-1.0, right=-1.0, top=1.0)
        r2 = _geo.Rect(left=1.0, bottom=-1.0, right=3.0, top=1.0)
        ms1 = _geo.MaskShape(mask=m1, shape=r1)
        ms2 = _geo.MaskShape(mask=m2, shape=r2)
        ms3 = _geo.MaskShape(mask=m1, shape=r2)
        ms4 = _geo.MaskShape(mask=m1, shape=_geo.MultiShape(shapes=(r1, r2)))
        mss1 = _geo.MaskShapes(ms1)
        mss2 = _geo.MaskShapes((ms1, ms2))
        mss3 = _geo.MaskShapes((ms1, ms2))
        mss3.move(dxy=p)
        mss4 = _geo.MaskShapes(ms1)
        mss4.rotate(rotation=rot)
        mss5 = _geo.MaskShapes(ms1)
        mss5 += ms3
        mss6 = _geo.MaskShapes(ms4)
        mss7 = _geo.MaskShapes((ms1, ms3))

        self.assertEqual(_util.first(mss1), ms1)
        self.assertEqual(_util.last(mss2), ms2)
        self.assertEqual(mss5, mss6)
        self.assertEqual(mss5, mss7)
        self.assertEqual(mss2.moved(dxy=p), mss3)
        self.assertEqual(mss1.rotated(rotation=rot), mss4)

        mss1 += ms2

        self.assertEqual(mss1, mss2)

        mss2._freeze_()

        with self.assertRaises(TypeError):
            mss2.move(dxy=p)
        with self.assertRaises(TypeError):
            mss2.rotate(rotation=rot)
