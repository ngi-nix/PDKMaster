# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
"""The pdkmaster.design.geometry module provides classes to represent shapes drawn in
a DesignMask of a technology.

Attributes:
    epsilon: value under which two coordinate values are considered equal.  
        Default is 1e-6; as coordinates are assumed to be in µm this
        corresponds with 1 fm.
    origin: (0.0, 0.0)
"""
import abc, enum
from itertools import product
from typing import (
    Iterable, Iterator, Generator, Collection, Tuple, List,
    Optional, Union, TypeVar, overload,
)

from .. import _util
from ..typing import SingleOrMulti
from ..technology import mask as msk


__all__ = [
    "epsilon",
    "Rotation", "FloatPoint",
    "Point", "origin", "Line", "Polygon", "Rect", "MultiShape", "RepeatedShape",
    "MaskShape", "MaskShapes",
]


epsilon: float = 1e-6
def _eq(v1: float, v2: float):
    """Compare if two floats have a difference smaller than epsilon

    API Notes:
        This function may only be used inside this module
    """
    return (abs(v1 - v2) < epsilon)


class Rotation(enum.Enum):
    """Enum type to represent supported `_Shape` rotations
    """
    No = "no"
    R0 = "no" # alias
    R90 = "90"
    R180 = "180"
    R270 = "270"
    MX = "mirrorx"
    MX90 = "mirrorx&90"
    MY = "mirrory"
    MY90 = "mirrory&90"

    @staticmethod
    def from_name(rot: str) -> "Rotation":
        """Helper function to convert a rotation string representation to
        a `Rotation` value.

        Arguments:
            rot: string r of the rotation; supported values:  
                ("no", "90", "180", "270", "mirrorx", "mirrorx&90", "mirrory",
                "mirrory&90")

        Returns:
            Corresponding `Rotation` value
        """
        lookup = {
            "no": Rotation.No,
            "90": Rotation.R90,
            "180": Rotation.R180,
            "270": Rotation.R270,
            "mirrorx": Rotation.MX,
            "mirrorx&90": Rotation.MX90,
            "mirrory": Rotation.MY,
            "mirrory&90": Rotation.MY90,
        }
        assert rot in lookup
        return lookup[rot]


_shape_childclass = TypeVar("_shape_childclass", bound="_Shape")
class _Shape(abc.ABC):
    """The base class for representing shapes

    API Notes:
        * _Shape objects need to be immutable objects. They need to implement
          __hash__() and __eq__()
    """
    @abc.abstractmethod
    def __init__(self):
        pass

    @property
    @abc.abstractmethod
    def pointsshapes(self) -> Iterable["_PointsShape"]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def bounds(self) -> "_Rectangular":
        raise NotImplementedError

    @abc.abstractmethod
    def moved(self: "_shape_childclass", *, dxy: "Point") -> "_shape_childclass":
        """Move a _Shape object by a given vector

        This method is called moved() to represent the fact the _Shape objects are
        immutable and a new object is created by the moved() method.
        """
        raise NotImplementedError

    def repeat(self, *,
        offset0: "Point",
        n: int, n_dxy: "Point", m: int=1, m_dxy: Optional["Point"]=None,
    ) -> "RepeatedShape":
        return RepeatedShape(
            shape=self, offset0=offset0,
            n=n, n_dxy=n_dxy, m=m, m_dxy=m_dxy,
        )

    @abc.abstractmethod
    def rotated(self: "_shape_childclass", *, rotation: Rotation) -> "_shape_childclass":
        """Rotate a _Shape object by a given vector

        This method is called rotated() to represent the fact the _Shape objects are
        immutable and a new object is created by the rotated() method.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def area(self) -> float:
        raise NotImplementedError

    @abc.abstractmethod
    def __eq__(self, o: object) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def __hash__(self) -> int:
        raise NotImplementedError


class _Rectangular(_Shape):
    """Mixin base class rectangular shapes

    API Notes:
        * This is private class for this module and is not exported by default.
          It should only be used as mixing inside this module.
    """
    @property
    @abc.abstractmethod
    def left(self) -> float:
        raise NotImplementedError
    @property
    @abc.abstractmethod
    def bottom(self) -> float:
        raise NotImplementedError
    @property
    @abc.abstractmethod
    def right(self) -> float:
        raise NotImplementedError
    @property
    @abc.abstractmethod
    def top(self) -> float:
        raise NotImplementedError

    @property
    def center(self) -> "Point":
        return Point(
            x=0.5*(self.left + self.right),
            y=0.5*(self.bottom + self.top),
        )


class _PointsShape(_Shape):
    """base class for single shape that can be described
    as a list of points

    API Notes:
        * This is private class for this module and is not exported by default.
          It should only be used as mixing inside this module.
    """
    @property
    @abc.abstractmethod
    def points(self) -> Iterable["Point"]:
        raise NotImplementedError

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, _PointsShape):
            return False
        p_it1 = iter(self.points)
        p_it2 = iter(o.points)
        while True:
            try:
                p1 = next(p_it1)
            except StopIteration:
                try:
                    p2 = next(p_it2)
                except StopIteration:
                    # All points the same
                    return True
                else:
                    return False
            else:
                try:
                    p2 = next(p_it2)
                except StopIteration:
                    # Different number of points
                    return False
                if p1 != p2:
                    # Non-equal point
                    return False

    def __hash__(self) -> int:
        return hash(tuple(self.points))


FloatPoint = Union[Tuple[float, float], List[float]]
class Point(_PointsShape, _Rectangular):
    """A point object

    Arguments:
        x: X-coordinate
        y: Y-coordinate

    API Notes:
        * Point objects are immutable, x and y coordinates may not be changed
          after object creation.
        * Point is a final class, no backwards compatibility is guaranteed for
          subclassing this class.
    """
    def __init__(self, *, x: float, y: float):
        self._x = x
        self._y = y

    @staticmethod
    def from_float(*, point: FloatPoint) -> "Point":
        assert len(point) == 2
        return Point(x=point[0], y=point[1])

    @staticmethod
    def from_point(
        *, point: "Point", x: Optional[float]=None, y: Optional[float]=None,
    ) -> "Point":
        if x is None:
            x = point.x
        if y is None:
            y = point.y
        return Point(x=x, y=y)

    @property
    def x(self) -> float:
        """X-coordinate"""
        return self._x
    @property
    def y(self) -> float:
        """Y-coordinate"""
        return self._y

    # _Shape base class abstract methods
    @property
    def pointsshapes(self) -> Tuple["Point"]:
        return (self,)
    @property
    def bounds(self) -> "Point":
        return self

    def moved(self, *, dxy: "Point") -> "Point":
        x = self.x + dxy.x
        y = self.y + dxy.y

        return Point(x=x, y=y)

    def rotated(self, *, rotation: Rotation) -> "Point":
        x = self.x
        y = self.y
        tx, ty = {
            Rotation.No: (x, y),
            Rotation.R90: (-y, x),
            Rotation.R180: (-x, -y),
            Rotation.R270: (y, -x),
            Rotation.MX: (-x, y),
            Rotation.MX90: (-y, -x),
            Rotation.MY: (x, -y),
            Rotation.MY90: (y, x),
        }[rotation]

        return Point(x=tx, y=ty)

    # _PointsShape base class abstract methods
    @property
    def points(self) -> Tuple["Point"]:
        return (self,)

    # _Rectangular mixin abstract methods
    @property
    def left(self) -> float:
        return self._x
    @property
    def bottom(self) -> float:
        return self._y
    @property
    def right(self) -> float:
        return self._x
    @property
    def top(self) -> float:
        return self._y

    def __neg__(self) -> "Point":
        return Point(x=-self.x, y=-self.y)

    area = 0.0

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Point):
            return False
        else:
            return _eq(self.x, o.x) and _eq(self.y, o.y)

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    @overload
    def __add__(self, shape: _shape_childclass) -> _shape_childclass:
        ... # pragma: no cover
    @overload
    def __add__(self, shape: "MaskShape") -> "MaskShape":
        ... # pragma: no cover
    @overload
    def __add__(self, shape: "MaskShapes") -> "MaskShapes":
        ... # pragma: no cover
    def __add__(self, shape) -> Union[_Shape, "MaskShape", "MaskShapes"]:
        """The + operation with a Point.

        The + operation on a (mask)shape will move that shape with the given
        point as vector.

        Returns
            Shape shifted by the point as vector
        """
        if isinstance(shape, (_Shape, MaskShape, MaskShapes)):
            return shape.moved(dxy=self)
        else:
            raise TypeError(
                "unsupported operand type(s) for +: "
                f"'{self.__class__.__name__}' and '{shape.__class__.__name__}'"
            )
    __radd__ = __add__

    @overload
    def __rsub__(self, shape: _Shape) -> _Shape:
        ... # pragma: no cover
    @overload
    def __rsub__(self, shape: "MaskShape") -> "MaskShape":
        ... # pragma: no cover
    @overload
    def __rsub__(self, shape: "MaskShapes") -> "MaskShapes":
        ... # pragma: no cover
    def __rsub__(self, shape) -> Union[_Shape, "MaskShape", "MaskShapes"]:
        """Operation shape - `Point`

        Returns
            Shape shifted by the negative of the point as vector
        """
        if isinstance(shape, (_Shape, MaskShape, MaskShapes)):
            return shape.moved(dxy=-self)
        else:
            raise TypeError(
                "unsupported operand type(s) for -: "
                f"'{shape.__class__.__name__}' and '{self.__class__.__name__}'"
            )

    # Point - Point is not handled by __rsub__
    def __sub__(self, point: "Point") -> "Point":
        if isinstance(point, Point):
            return self.moved(dxy=-point)
        else:
            raise TypeError(
                "unsupported operand type(s) for -: "
                f"'{self.__class__.__name__}' and '{point.__class__.__name__}'"
            )

    def __mul__(self, m: float) -> "Point":
        if not isinstance(m, (int, float)):
            raise TypeError(
                f"unsupported operand type(s) for *: "
                f"'{self.__class__.__name__}' and '{m.__class__.__name__}'"
            )
        return Point(x=m*self.x, y=m*self.y)
    __rmul__ = __mul__

    def __str__(self) -> str:
        return f"({self.x},{self.y})"

    def __repr__(self) -> str:
        return f"Point(x={self.x},y={self.y})"


origin: Point = Point(x=0.0, y=0.0)


class Line(_PointsShape, _Rectangular):
    """A line shape

    A line consist of a start point and an end point. It is considered
    to be directional so two lines with start en and point exchanged
    are not considered equal.
    """
    def __init__(self, *, point1: Point, point2: Point):
        self._point1 = point1
        self._point2 = point2

    @property
    def point1(self) -> Point:
        return self._point1
    @property
    def point2(self) -> Point:
        return self._point2

    # _Shape base class abstraxt methods
    @property
    def pointsshapes(self) -> Tuple["Line"]:
        return (self,)
    @property
    def bounds(self) -> "Line":
        return self

    def moved(self, *, dxy: Point) -> "Line":
        return Line(
            point1=self._point1.moved(dxy=dxy),
            point2=self._point2.moved(dxy=dxy),
        )

    def rotated(self, *, rotation: Rotation) -> "Line":
        return Line(
            point1=self.point1.rotated(rotation=rotation),
            point2=self.point2.rotated(rotation=rotation),
        )

    # _PointsShape mixin abstract methods
    @property
    def points(self) -> Tuple[Point, Point]:
        return (self._point1, self._point2)

    # _Rectangular mixin abstract methods
    @property
    def left(self) -> float:
        return min(self._point1.left, self._point2.left)
    @property
    def bottom(self) -> float:
        return min(self._point1.bottom, self._point2.bottom)
    @property
    def right(self) -> float:
        return max(self._point1.right, self._point2.right)
    @property
    def top(self) -> float:
        return max(self._point1.top, self._point2.top)

    area = 0.0

    def __str__(self) -> str:
        return f"{self.point1}-{self.point2}"

    def __repr__(self) -> str:
        return f"Line(point1={self.point1!r},point2={self.point2!r})"


class Polygon(_PointsShape):
    def __init__(self, *, points: Iterable["Point"]):
        self._points = points = tuple(points)
        if points[0] != points[-1]:
            raise ValueError("Last point has to be the same as the first point")

        left = min(point.x for point in points)
        bottom = min(point.y for point in points)
        right = max(point.x for point in points)
        top = max(point.y for point in points)
        if _eq(left, right) or _eq(bottom, top):
            raise ValueError("Polygon with only colinear points not allowed")
        self._bounds: Rect = Rect(left=left, bottom=bottom, right=right, top=top)

    @classmethod
    def from_floats(
        cls, *, points: Iterable[FloatPoint],
    ):
        """
        API Notes:
            * This method is only meant to be called as Outline.from_floats
              not as obj.__class__.from_floats(). This means that subclasses
              may overload this method with incompatible call signature.
        """
        return cls(points=(Point(x=x, y=y) for x, y in points))

    # _Shape base class abstraxt methods
    @property
    def pointsshapes(self) -> Generator["Polygon", None, None]:
        yield self
    @property
    def bounds(self) -> "Rect":
        return self._bounds

    def moved(self, *, dxy: Point) -> "Polygon":
        return Polygon(points=(point + dxy for point in self.points))

    def rotated(self, *, rotation: Rotation) -> "Polygon":
        return Polygon(points=(
            point.rotated(rotation=rotation) for point in self.points
        ))

    # _PointsShape mixin abstract methods
    @property
    def points(self):
        return self._points

    @property
    def area(self) -> float:
        raise NotImplementedError


class Rect(Polygon, _Rectangular):
    """A rectangular shape object

    Arguments:
        left, bottom, right, top:
            Edge coordinates of the rectangle; left, bottom have to be smaller
            than resp. right, top.

    API Notes:
        * Rect objects are immutable, dimensions may not be changed after creation.
        * This class is final. No backwards guarantess given for subclasses in
          user code
    """
    def __init__(self, *, left: float, bottom: float, right: float, top: float):
        assert (left < right) and (bottom < top)

        self._left = left
        self._bottom = bottom
        self._right = right
        self._top = top

    @staticmethod
    # type: ignore[override]
    def from_floats(*, values: Tuple[float, float, float, float]) -> "Rect":
        left, bottom, right, top = values
        return Rect(left=left, bottom=bottom, right=right, top=top)

    @staticmethod
    def from_rect(
        *, rect: "Rect",
        left: Optional[float]=None, bottom: Optional[float]=None,
        right: Optional[float]=None, top: Optional[float]=None,
        bias: float=0.0,
    ) -> "Rect":
        if left is None:
            left = rect.left
        left -= bias
        if bottom is None:
            bottom = rect.bottom
        bottom -= bias
        if right is None:
            right = rect.right
        right += bias
        if top is None:
            top = rect.top
        top += bias
        return Rect(left=left, bottom=bottom, right=right, top=top)

    @staticmethod
    def from_corners(*, corner1: Point, corner2: Point) -> "Rect":
        left = min(corner1.x, corner2.x)
        bottom = min(corner1.y, corner2.y)
        right = max(corner1.x, corner2.x)
        top = max(corner1.y, corner2.y)

        return Rect(left=left, bottom=bottom, right=right, top=top)

    @staticmethod
    def from_float_corners(*, corners: Tuple[FloatPoint, FloatPoint]) -> "Rect":
        return Rect.from_corners(
            corner1=Point.from_float(point=corners[0]),
            corner2=Point.from_float(point=corners[1]),
        )

    @staticmethod
    def from_size(
        *, center: Point=Point(x=0, y=0), width: float, height: float,
    ) -> "Rect":
        assert (width > 0) and (height > 0)
        x = center.x
        y = center.y
        left = x - 0.5*width
        bottom = y - 0.5*height
        right = x + 0.5*width
        top = y + 0.5*height

        return Rect(left=left, bottom=bottom, right=right, top=top)

    @property
    def left(self) -> float:
        return self._left
    @property
    def bottom(self) -> float:
        return self._bottom
    @property
    def right(self) -> float:
        return self._right
    @property
    def top(self) -> float:
        return self._top

    @property
    def bounds(self) -> "Rect":
        return self

    # Computed properties
    @property
    def width(self) -> float:
        return self.right - self.left
    @property
    def height(self) -> float:
        return self.top - self.bottom

    # overloaded _Shape base class abstract methods
    def moved(self, *, dxy: Point) -> "Rect":
        left = self.left + dxy.x
        bottom = self.bottom + dxy.y
        right = self.right + dxy.x
        top = self.top + dxy.y

        return Rect(left=left, bottom=bottom, right=right, top=top)

    def rotated(self, *, rotation: Rotation) -> "Rect":
        if rotation in (Rotation.No, Rotation.R180, Rotation.MX, Rotation.MY):
            width = self.width
            height = self.height
        elif rotation in (Rotation.R90, Rotation.R270, Rotation.MX90, Rotation.MY90):
            width = self.height
            height = self.width
        else:
            raise RuntimeError(
                f"Internal error: unsupported rotation '{rotation}'"
            )

        return Rect.from_size(
            center=self.center.rotated(rotation=rotation),
            width=width, height=height,
        )

    # overloaded _PointsShape mixin abstract methods
    @property
    def points(self):
        return (
            Point(x=self.left, y=self.bottom),
            Point(x=self.left, y=self.top),
            Point(x=self.right, y=self.top),
            Point(x=self.right, y=self.bottom),
            Point(x=self.left, y=self.bottom),
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"left={self.left},bottom={self.bottom},"
            f"right={self.right},top={self.top})"
        )

    @property
    def area(self) -> float:
        return self.width*self.height

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Rect):
            return False
        return (
            _eq(self.left, o.left) and _eq(self.bottom,  o.bottom)
            and _eq(self.right, o.right) and _eq(self.top, o.top)
        )

    def __hash__(self) -> int:
        return hash((self.left, self.bottom, self.right, self.top))


class MultiPartShape(Polygon):
    """This shape represents a single polygon shape that consist of
    a build up of touching parts.

    Main use case is to represent a shape where parts are on a different
    as is typically the case for a WaferWire.

    Arguments:
        fullshape: The full shape
        parts: The subshapes
            The subshapes should be touching shapes and joined should form the
            fullshape shape. Currently it is only checked if the areas match,
            in better checking may be implemented.

            The subshapes will be converted to MultiPartShape._Part objects before
            becoming member of the parts property
    """
    class _Part(Polygon):
        """A shape representing one part of a MultiPartShape

        This object keeps reference to the MultiPartShape so the parts can be added
        to nets in layout and the shapes still being able to know to which
        MultiPartShape object they belong.
        """
        def __init__(self, *, partshape: Polygon, multipartshape: "MultiPartShape"):
            self._partshape = partshape
            self._multipartshape = multipartshape

        @property
        def partshape(self) -> Polygon:
            return self._partshape
        @property
        def multipartshape(self) -> "MultiPartShape":
            return self._multipartshape

        @property
        def pointsshapes(self) -> Generator["Polygon", None, None]:
            return self.partshape.pointsshapes
        @property
        def bounds(self) -> "Rect":
            return self.partshape.bounds

        def moved(self, *, dxy: Point):
            idx = self.multipartshape.parts.index(self)
            return self.multipartshape.moved(dxy=dxy).parts[idx]

        def rotated(self, *, rotation: Rotation):
            idx = self.multipartshape.parts.index(self)
            return self.multipartshape.rotated(rotation=rotation).parts[idx]

        # _PointsShape mixin abstract methods
        @property
        def points(self):
            return self.partshape.points

        @property
        def area(self) -> float:
            return self.partshape.area

    def __init__(self, fullshape: Polygon, parts: Iterable[Polygon]):
        # TODO: check if shape is actually build up of the parts
        self._fullshape = fullshape
        self._parts = tuple(
            MultiPartShape._Part(partshape=part, multipartshape=self)
            for part in parts
        )

    @property
    def fullshape(self) -> Polygon:
        return self._fullshape
    @property
    def parts(self) -> Tuple["MultiPartShape._Part", ...]:
        return self._parts

    @property
    def pointsshapes(self) -> Generator["Polygon", None, None]:
        return self.fullshape.pointsshapes
    @property
    def bounds(self) -> "Rect":
        return self.fullshape.bounds

    def moved(self, *, dxy: Point) -> "MultiPartShape":
        return MultiPartShape(
            fullshape=self.fullshape.moved(dxy=dxy),
            parts=(part.partshape.moved(dxy=dxy) for part in self.parts)
        )

    def rotated(self, *, rotation: Rotation) -> "MultiPartShape":
        return MultiPartShape(
            fullshape=self.fullshape.rotated(rotation=rotation),
            parts=(part.partshape.rotated(rotation=rotation) for part in self.parts)
        )

    # _PointsShape mixin abstract methods
    @property
    def points(self):
        return self.fullshape.points

    @property
    def area(self) -> float:
        return self.fullshape.area


class MultiShape(_Shape, Collection[_Shape]):
    """A shape representing a group of shapes

    Arguments:
        shapes: the sub shapes.
            Subshapes may or may not overlap. The object will fail to create if only one unique
            shape is provided including if the same shape is provided multiple times without
            another shape.

            MultiShape objects part of the provided shapes will be flattened and it's children will
            be joined with the other shapes.
    """
    def __init__(self, *, shapes: Iterable[_Shape]):
        def iterate_shapes(ss: Iterable[_Shape]) -> Generator[_Shape, None, None]:
            for shape in ss:
                if isinstance(shape, MultiShape):
                    yield from iterate_shapes(shape.shapes)
                else:
                    yield shape
        self._shapes = shapes = frozenset(iterate_shapes(shapes))
        if len(shapes) < 2:
            raise ValueError("MultiShape has to consist of more than one shape")

    @property
    def shapes(self):
        return self._shapes

    # _Shape base class abstract methods
    @property
    def pointsshapes(self) -> Generator[_PointsShape, None, None]:
        for shape in self._shapes:
            yield from shape.pointsshapes
    @property
    def bounds(self) -> _Rectangular:
        boundss = tuple(shape.bounds for shape in self.shapes)
        left = min(bounds.left for bounds in boundss)
        bottom = min(bounds.bottom for bounds in boundss)
        right = max(bounds.right for bounds in boundss)
        top = max(bounds.top for bounds in boundss)

        # It should be impossible to create a MultiShape where bounds
        # corresponds with a point.
        assert (left != right) or (bottom != top), "Internal error"
        if (left == right) or (bottom == top):
            return Line(
                point1=Point(x=left, y=bottom),
                point2=Point(x=right, y=top),
            )
        else:
            return Rect(left=left, bottom=bottom, right=right, top=top)

    def moved(self, *, dxy: Point) -> "MultiShape":
        return MultiShape(
            shapes=(polygon.moved(dxy=dxy) for polygon in self.pointsshapes),
        )

    def rotated(self, *, rotation: Rotation) -> "MultiShape":
        return MultiShape(
            shapes=(polygon.rotated(rotation=rotation) for polygon in self.pointsshapes)
        )

    # Collection mixin abstract methods
    def __iter__(self) -> Iterator[_Shape]:
        return iter(self.shapes)

    def __len__(self) -> int:
        return len(self.shapes)

    def __contains__(self, shape: object) -> bool:
        return shape in self.shapes

    @property
    def area(self) -> float:
        # TODO: guarantee non overlapping shapes
        return sum(shape.area for shape in self._shapes)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, MultiShape):
            return False
        else:
            return self._shapes == o._shapes

    def __hash__(self) -> int:
        return hash(self.shapes)

    def __str__(self) -> str:
        return "(" + ",".join(str(shape) for shape in self.shapes) + ")"

    def __repr__(self) -> str:
        return (
            "MultiShape(shapes=("
            + ",".join(repr(shape) for shape in self.shapes)
            + "))"
        )


class RepeatedShape(_Shape):
    """A repetition of a shape allowing easy generation of array of objects.
    Implementation is generic so that one can represent any repetition wit
    one or two vector that don't need to be manhattan.

    API Notes:
        * The current implementation assumes repeated shapes don't overlap. If they
          do area property will give wrong value.
    """
    # TODO: decide if repeated shapes may overlap, if not can we check it ?
    def __init__(self, *,
        shape: _Shape, offset0: Point,
        n: int, n_dxy: Point, m: int=1, m_dxy: Optional[Point]=None,
    ):
        if n < 2:
            raise ValueError(f"n has to be equal to or higher than 2, not '{n}'")
        if m < 1:
            raise ValueError(f"m has to be equal to or higher than 1, not '{m}'")
        if (m > 1) and (m_dxy is None):
            raise ValueError("m_dxy may not be None if m > 1")
        self._shape = shape
        self._offset0 = offset0
        self._n = n
        self._n_dxy = n_dxy
        self._m = m
        self._m_dxy = m_dxy

        self._hash = None

    @property
    def shape(self) -> _Shape:
        return self._shape
    @property
    def offset0(self) -> Point:
        return self._offset0
    @property
    def n(self) -> int:
        return self._n
    @property
    def n_dxy(self) -> Point:
        return self._n_dxy
    @property
    def m(self) -> int:
        return self._m
    @property
    def m_dxy(self) -> Optional[Point]:
        return self._m_dxy

    def moved(self: "RepeatedShape", *, dxy: "Point") -> "RepeatedShape":
        return RepeatedShape(
            shape=self.shape, offset0=(self.offset0 + dxy),
            n=self.n, n_dxy=self.n_dxy, m=self.m, m_dxy=self.m_dxy,
        )

    @property
    def pointsshapes(self) -> Generator["_PointsShape", None, None]:
        if self.m <= 1:
            for i_n in range(self.n):
                dxy = self.offset0 + i_n*self.n_dxy
                yield from (polygon + dxy for polygon in self.shape.pointsshapes)
        else:
            assert self.m_dxy is not None
            for i_n, i_m in product(range(self.n), range(self.m)):
                dxy = self.offset0 + i_n*self.n_dxy + i_m*self.m_dxy
                yield from (polygon + dxy for polygon in self.shape.pointsshapes)

    @property
    def bounds(self):
        b0 = self.shape.bounds
        b1 = b0 + self.offset0
        if self.m <= 1:
            b2 = b0 + (self.offset0 + (self.n - 1)*self.n_dxy)
        else:
            assert self.m_dxy is not None
            b2 = b0 + (
                self.offset0 + (self.n - 1)*self.n_dxy + (self.m - 1)*self.m_dxy
            )
        return Rect(
            left=min(b1.left, b2.left), right=max(b1.right, b2.right),
            bottom=min(b1.bottom, b2.bottom), top=max(b1.top, b2.top),
        )

    def rotated(self, *, rotation: Rotation) -> "RepeatedShape":
        return RepeatedShape(
            shape=self.shape.rotated(rotation=rotation),
            offset0=self.offset0.rotated(rotation=rotation),
            n=self.n, n_dxy=self.n_dxy.rotated(rotation=rotation),
            m=self.m, m_dxy=(
                None if self.m_dxy is None else self.m_dxy.rotated(rotation=rotation)
            )
        )

    @property
    def area(self) -> float:
        # TODO: Support case with overlapping shapes ?
        return self.n*self.m*self.shape.area

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, RepeatedShape):
            return False
        elif (self.shape != o.shape) or (self.offset0 != o.offset0):
            return False
        elif self.m == 1:
            return (
                (self.n == o.n) and (self.n_dxy == o.n_dxy)
                and (o.m == 1)
            )
        elif self.n == self.m:
            return (
                (self.n == o.n == o.m)
                # dxy value may be exchanged => compare sets
                and ({self.n_dxy, self.m_dxy} == {o.n_dxy, o.m_dxy})
            )
        else: # (self.n != self.m) and (self.m > 1)
            return (
                (
                    (self.n == o.n) and (self.n_dxy == o.n_dxy)
                    and (self.m == o.m) and (self.m_dxy == o.m_dxy)
                )
                or
                (
                    (self.n == o.m) and (self.n_dxy == o.m_dxy)
                    and (self.m == o.n) and (self.m_dxy == o.n_dxy)
                )
            )

    def __hash__(self) -> int:
        if self._hash is None:
            if self.m == 1:
                self._hash = hash(frozenset((
                    self.shape, self.offset0, self.n, self.n_dxy,
                )))
            else:
                self._hash = hash(frozenset((
                    self.shape, self.offset0, self.n, self.n_dxy, self.m, self.m_dxy,
                )))
        return self._hash

    def __repr__(self) -> str:
        s_args = ",".join((
            f"shape={self.shape!r}",
            f"offset0={self.offset0!r}",
            f"n={self.n}", f"n_dxy={self.n_dxy!r}",
            f"m={self.m}", f"m_dxy={self.m_dxy!r}",
        ))
        return f"RepeatedShape({s_args})"


class MaskShape:
    def __init__(self, *, mask: msk.DesignMask, shape: _Shape):
        self._mask = mask
        self._shape = shape
        # TODO: Check grid

    @property
    def mask(self) -> msk.DesignMask:
        return self._mask
    @property
    def shape(self) -> _Shape:
        return self._shape

    def moved(self, *, dxy: Point) -> "MaskShape":
        return MaskShape(mask=self.mask, shape=self.shape.moved(dxy=dxy))

    def rotated(self, *, rotation: Rotation) -> "MaskShape":
        return MaskShape(mask=self.mask, shape=self.shape.rotated(rotation=rotation))

    @property
    def area(self) -> float:
        return self.shape.area

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, MaskShape):
            return False
        return (self.mask == o.mask) and (self.shape == o.shape)

    def __hash__(self) -> int:
        return hash((self.mask, self.shape))

    def __repr__(self) -> str:
        return f"MaskShape=(mask={self.mask!r},shape={self.shape!r})"

    @property
    def bounds(self) -> _Rectangular:
        return self.shape.bounds


class MaskShapes(_util.TypedListMapping[MaskShape, msk.DesignMask]):
    """A TypedListMapping of MaskShape objects.

    API Notes:
        Contrary to other classes a MaskShapes object is mutable if not frozen.
    """
    _elem_type_ = MaskShape
    _index_type_ = msk.DesignMask
    _index_attribute_ = "mask"

    def __init__(self, iterable: SingleOrMulti[MaskShape].T):
        shapes = _util.v2t(iterable)

        def join_shapes() -> Generator[MaskShape, None, None]:
            masks = []
            for shape in shapes:
                mask = shape.mask
                if mask not in masks:
                    shapes2 = tuple(filter(lambda ms: ms.mask == mask, shapes))
                    if len(shapes2) == 1:
                        yield shapes2[0]
                    else:
                        yield MaskShape(
                            mask=mask,
                            shape=MultiShape(shapes=(ms.shape for ms in shapes2))
                        )
                    masks.append(mask)

        super().__init__(join_shapes())

    def __iadd__(self, shape: SingleOrMulti[MaskShape].T) -> "MaskShapes":
        for s in _util.v2t(shape):
            mask = s.mask
            try:
                ms = self[mask]
            except KeyError:
                super().__iadd__(s)
            except: # pragma: no cover
                raise
            else:
                ms2 = MaskShape(
                    mask=mask, shape=MultiShape(shapes=(ms.shape, s.shape)),
                )
                self[mask] = ms2

        return self

    def move(self, *, dxy: Point) -> None:
        if self._frozen_:
            raise TypeError(f"moving frozen '{self.__class__.__name__}' object not allowed")
        for i in range(len(self)):
            self[i] = self[i].moved(dxy=dxy)

    def moved(self, *, dxy: Point) -> "MaskShapes":
        """Moved MaskShapes object will not be frozen"""
        return MaskShapes(ms.moved(dxy=dxy) for ms in self)

    def rotate(self, *, rotation: Rotation) -> None:
        if self._frozen_:
            raise TypeError(f"rotating frozen '{self.__class__.__name__}' object not allowed")
        for i in range(len(self)):
            self[i] = self[i].rotated(rotation=rotation)

    def rotated(self, *, rotation: Rotation) -> "MaskShapes":
        """Rotated MaskShapes object will not be frozen"""
        return MaskShapes(ms.rotated(rotation=rotation) for ms in self)


# TODO: Complete MaskPath, allow 45 deg sections etc.
# class MaskPath(MaskPolygon):
#     NextFloat = Union[
#         Tuple[FloatPoint, Optional[float]],
#         List[FloatPoint, Optional[float]],
#     ]
#     class Next:
#         def __init__(self, *, point: Point, width: Optional[float]=None):
#             self.point = point
#             self.width = width

#         @staticmethod
#         def from_floats(self, *, next: "MaskPath.NextFloat") -> "MaskPath.Next":
#             return MaskPath.Next(point=next[0], width=next[1])

#     def __init__(self, connections: Iterable[Next]):
#         self.connections = conns = tuple(connections)
#         assert len(conns) > 1, f"Need at least two points"
#         assert (
#             (conns[0].width is not None) or (conns[1].width is not None),
#             "No width for first section"
#         )

#         self._shape: Optional[MaskPolygon] = None

#     @staticmethod
#     def from_floats(connnections: Iterable["MaskPath.NextFloat"]) -> "MaskPath":
#         return MaskPath(
#             connections=(MaskPath.Next.from_floats(conn) for conn in connnections),
#         )

#     @property
#     def shape(self) -> MaskPolygon:
#         if self._shape is None:
#             self._build()
#         return self._shape

#     @property
#     def hull(self) -> Outline:
#         return self.shape.hull

#     @property
#     def holes(self) -> Iterable[Outline]:
#         return 

#     def _build(self) -> None:
