# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
"""The pdkmaster.design.layout module provides classes to represent layout shapes
in a PDKMaster technology. These classes are designed to only allow to create
layout that conform to the technology definition. In order to detect design
shorts as fast as possible shapes are put on nets.

A LayoutFactory class is provided to generate layouts for a certain technology and
it's primitives.

Internally the klayout API is used to represent the shapes and perform manipulations
on them.
"""
import abc, logging
from itertools import product
from pdkmaster.typing import IntFloat, SingleOrMulti
from typing import (
    Any, Iterable, Generator, Sequence, Mapping, Tuple, Optional, Union, Type, cast,
)
from matplotlib import pyplot as plt
import descartes
from shapely import geometry as sh_geo, ops as sh_ops, affinity as sh_aff

from .. import _util
from ..technology import (
    property_ as prp, net as net_, mask as msk, geometry as geo,
    primitive as prm, technology_ as tch, dispatcher as dsp
)
from . import circuit as ckt

__all__ = [
    "MaskPolygon", "MaskPolygons",
    "NetSubLayout", "MultiNetSubLayout", "NetlessSubLayout",
    "MaskShapesSubLayout",
    "SubLayouts",
    "LayoutFactory", "Plotter",
]

_rotations = (
    "no", "90", "180", "270", "mirrorx", "mirrorx&90", "mirrory", "mirrory&90",
)


class NetOverlapError(Exception):
    pass


def _rect(
    left: float, bottom: float, right: float, top: float, *,
    enclosure: Optional[Union[float, Sequence[float], prp.Enclosure]]=None,
) -> geo.Rect:
    if enclosure is not None:
        if isinstance(enclosure, prp.Enclosure):
            enclosure = enclosure.spec
        if isinstance(enclosure, float):
            left -= enclosure
            bottom -= enclosure
            right += enclosure
            top += enclosure
        else:
            left -= enclosure[0]
            bottom -= enclosure[1]
            right += enclosure[0]
            top += enclosure[1]

    return geo.Rect(
        left=left, bottom=bottom, right=right, top=top,
    )


def _via_array(
    left: float, bottom: float, width: float, pitch: float, rows: int, columns: int,
):
    via = geo.Rect.from_size(width=width, height=width)
    xy0 = geo.Point(x=(left + 0.5*width), y=(bottom + 0.5*width))

    if (rows == 1) and (columns == 1):
        return via + xy0
    else:
        return geo.ArrayShape(
            shape=via, offset0=xy0, rows=rows, columns=columns, pitch_x=pitch, pitch_y=pitch,
        )


def _manhattan_polygon(polygon, *, outer=True):
    def _manhattan_coords(coords, outer):
        n_coords = len(coords)
        idx = 0
        prev = None
        while idx < n_coords:
            coord = coords[idx]

            idx += 1
            if idx == n_coords:
                yield coord
                break
            next_coord = coords[idx]

            if ((next_coord[0] != coord[0]) and (next_coord[1] != coord[1])):
                idx += 1
                if prev is None:
                    next2_coord = coords[idx]
                    if next_coord[0] == next2_coord[0]:
                        if outer:
                            coord = (next_coord[0], coord[1])
                        else:
                            yield coord
                            yield (coord[0], next_coord[1])
                            coord = next_coord
                    elif next_coord[1] == next2_coord[1]:
                        if outer:
                            coord = (coord[0], next_coord[1])
                        else:
                            yield coord
                            yield (next_coord[0], coord[1])
                            coord = next_coord
                    else:
                        raise RuntimeError("two consecutive non-Manhattan points")
                else:
                    if coord[0] == prev[0]:
                        if outer:
                            coord = (coord[0], next_coord[1])
                        else:
                            yield coord
                            yield (next_coord[0], coord[1])
                            coord = next_coord
                    elif coord[1] == prev[1]:
                        if outer:
                            coord = (next_coord[0], coord[1])
                        else:
                            yield coord
                            yield (coord[0], next_coord[1])
                            coord = next_coord
                    else:
                        raise RuntimeError(
                            "two consecutive non-Manhattan points:\n"
                            f"  {prev}, {coord}, {next_coord}"
                        )

            yield coord
            prev = coord

    if _util.is_iterable(polygon):
        return sh_ops.unary_union(tuple(
            _manhattan_polygon(subpolygon, outer=outer)
            for subpolygon in polygon
        ))
    else:
        return sh_geo.Polygon(
            shell=_manhattan_coords(tuple(polygon.exterior.coords), outer),
            holes=tuple(
                _manhattan_coords(tuple(interior.coords), not outer)
                for interior in polygon.interiors
            )
        )


class MaskPolygon:
    _geometry_types = (sh_geo.Polygon, sh_geo.MultiPolygon)
    _geometry_types_str = "'Polygon'/'MultiPolygon' from shapely"

    def __init__(self, mask, polygon):
        if not isinstance(mask, msk.DesignMask):
            raise TypeError("mask has to be of type 'DesignMask'")
        self.name = mask.name
        self.mask = mask

        if isinstance(polygon, geo.Rect):
            polygon = sh_geo.Polygon((
                (polygon.left, polygon.bottom),
                (polygon.right, polygon.bottom),
                (polygon.right, polygon.top),
                (polygon.left, polygon.top),
                (polygon.left, polygon.bottom),
            ))
        if not isinstance(polygon, self._geometry_types):
            raise TypeError(
                f"polygon has to be of type {self._geometry_types_str}"
            )
        self.polygon = polygon

    def dup(self):
        return MaskPolygon(self.mask, self.polygon)

    @property
    def bounds(self) -> geo.Rect:
        values: Any = tuple(self.polygon.bounds)
        return geo.Rect.from_floats(values=values)

    @property
    def polygons(self):
        # Split up MultiPolygon in indivual Polygon
        if isinstance(self.polygon, sh_geo.Polygon):
            yield self
        elif isinstance(self.polygon, sh_geo.MultiPolygon):
            for polygon in self.polygon: # type: ignore
                yield MaskPolygon(self.mask, polygon)
        else:
            raise AssertionError("Internal error")

    def __iadd__(self, polygon):
        if isinstance(polygon, MaskPolygon):
            if self.mask == polygon.mask:
                self.polygon = self.polygon.union(polygon.polygon)
                return self
            else:
                return self + polygon
        elif isinstance(polygon, MaskPolygons):
            return polygon + self
        elif isinstance(polygon, self._geometry_types):
            self.polygon = self.polygon.union(polygon)
            return self
        else:
            raise TypeError(
                "can only add object of type 'MaskPolygon', 'Maskpolygons' or \n"
                f"{self._geometry_types_str}"
            )
    __ior__ = __iadd__

    def __isub__(self, polygon):
        if isinstance(polygon, MaskPolygon):
            if self.mask == polygon.mask:
                self.polygon = self.polygon.difference(polygon.polygon)
        elif isinstance(polygon, MaskPolygons):
            try:
                polygon = polygon[self.mask]
            except:
                pass
            else:
                self.polygon = self.polygon.difference(polygon.polygon)
        elif isinstance(polygon, self._geometry_types):
            self.polygon = self.polygon.difference(polygon)
        else:
            raise TypeError(
                "can only add object of type 'MaskPolygon', 'Maskpolygons' or \n"
                f"{self._geometry_types_str}"
            )
        return self

    def __iand__(self, polygon):
        if isinstance(polygon, MaskPolygon):
            if self.mask == polygon.mask:
                self.polygon = self.polygon.intersection(polygon.polygon)
            else:
                self.polygon = sh_geo.Polygon()
        elif isinstance(polygon, MaskPolygons):
            try:
                polygon = polygon[self.mask]
            except:
                self.polygon = sh_geo.Polygon()
            else:
                self.polygon = self.polygon.intersection(polygon.polygon)
        elif isinstance(polygon, self._geometry_types):
            self.polygon = self.polygon.intersection(polygon)
        else:
            raise TypeError(
                "can only intersect object of type 'MaskPolygon', 'Maskpolygons' or \n"
                f"{self._geometry_types_str}"
            )
    __imul__ = __iand__

    def __add__(self, polygon):
        if isinstance(polygon, MaskPolygon):
            if self.mask == polygon.mask:
                return MaskPolygon(self.mask, self.polygon.union(polygon.polygon))
            else:
                return MaskPolygons((self, polygon))
        elif isinstance(polygon, MaskPolygons):
            return polygon + self
        elif isinstance(polygon, self._geometry_types):
            return MaskPolygon(self.mask, self.polygon.union(polygon))
        else:
            raise TypeError(
                "can only add object of type 'MaskPolygon', 'Maskpolygons' or \n"
                f"{self._geometry_types_str}"
            )
    __or__ = __add__

    def __sub__(self, polygon):
        if isinstance(polygon, MaskPolygon):
            if self.mask == polygon.mask:
                newpolygon = self.polygon.difference(polygon.polygon)
            else:
                newpolygon = self.polygon
        elif isinstance(polygon, MaskPolygons):
            try:
                polygon = polygon[self.mask]
            except:
                newpolygon = self.polygon
            else:
                newpolygon = self.polygon.difference(polygon.polygon)
        elif isinstance(polygon, self._geometry_types):
            newpolygon = self.polygon.difference(polygon)
        else:
            raise TypeError(
                "can only add object of type 'MaskPolygon', 'Maskpolygons' or \n"
                f"{self._geometry_types_str}"
            )

        return MaskPolygon(self.mask, newpolygon)

    def __and__(self, polygon):
        if isinstance(polygon, MaskPolygon):
            if self.mask == polygon.mask:
                newpolygon = self.polygon.intersection(polygon.polygon)
            else:
                newpolygon = sh_geo.Polygon()
        elif isinstance(polygon, MaskPolygons):
            try:
                polygon = polygon[self.mask]
            except:
                newpolygon = sh_geo.Polygon()
            else:
                newpolygon = self.polygon.intersection(polygon.polygon)
        elif isinstance(polygon, self._geometry_types):
            newpolygon = self.polygon.intersection(polygon)
        else:
            raise TypeError(
                "can only add object of type 'MaskPolygon', 'Maskpolygons' or \n"
                f"{self._geometry_types_str}"
            )

        return MaskPolygon(self.mask, newpolygon)
    __mul__ = __and__

    def overlaps_with(self, other):
        if not isinstance(other, MaskPolygon):
            raise TypeError(
                f"other has to be of type 'MaskPolygon', not '{type(other)}'"
            )
        return (
            (self.mask == other.mask)
            and self.polygon.intersects(other.polygon)
        )

    def _move_polygon(self, dx, dy, rotation):
        def mirrorx(x, y):
            return (-x, y)
        def mirrory(x, y):
            return (x, -y)

        try:
            f_rotate = {
                "no": lambda p: p,
                "90": lambda p: sh_aff.rotate(p, 90, origin=(0, 0)),
                "180": lambda p: sh_aff.rotate(p, 180, origin=(0, 0)),
                "270": lambda p: sh_aff.rotate(p, 270, origin=(0, 0)),
                "mirrorx": lambda p: sh_ops.transform(mirrorx, p),
                "mirrorx&90": lambda p: sh_aff.rotate(
                    sh_ops.transform(mirrorx, p), 90, origin=(0, 0)
                ),
                "mirrory": lambda p: sh_ops.transform(mirrory, p),
                "mirrory&90": lambda p: sh_aff.rotate(
                    sh_ops.transform(mirrory, p), 90, origin=(0, 0)
                ),
            }[rotation]
        except KeyError:
            raise NotImplementedError(
                f"polygon rotation '{rotation}'"
            )
        polygon = f_rotate(self.polygon)
        if (round(dx, 6) == 0.0) and (round(dy, 6) == 0.0):
            return polygon
        else:
            return sh_aff.translate(polygon, dx, dy)

    def move(self, dx, dy, rotation="no"):
        self.polygon = self._move_polygon(dx, dy, rotation)
        assert isinstance(self.polygon, MaskPolygon._geometry_types)

    def moved(self, dx, dy, rotation="no"):
        return MaskPolygon(self.mask, self._move_polygon(dx, dy, rotation))

    def grow(self, size):
        self.polygon = _manhattan_polygon(
            self.polygon.buffer(size, resolution=0), outer=True,
        )

    def grown(self, size):
        return MaskPolygon(
            self.mask, _manhattan_polygon(
                self.polygon.buffer(size, resolution=0), outer=True,
            ),
        )

    def connect(self):
        try:
            self.polygon = _manhattan_polygon(
                self.polygon.simplify(1e-6).convex_hull, outer=False,
            )
        except:
            logging.warning(f"Polygon.connect() failed for '{self}'")

    def connected(self):
        return MaskPolygon(
            self.mask, _manhattan_polygon(
                self.polygon.simplify(1e-6).convex_hull, outer=False,
            ),
        )


class MaskPolygons(_util.TypedListMapping[MaskPolygon, msk.DesignMask]):
    _elem_type_ = MaskPolygon
    _index_attribute_ = "mask"
    _index_type_ = msk.DesignMask

    def dup(self):
        return MaskPolygons(mp.dup() for mp in self)

    def mps_bounds(self, *, mask=None) -> geo.Rect:
        mps = self if mask is None else filter(
            lambda mp: mp.mask == mask, self,
        )
        boundslist = tuple(mp.bounds for mp in mps)
        return geo.Rect(
            left=min(bds.left for bds in boundslist),
            bottom=min(bds.bottom for bds in boundslist),
            right=max(bds.right for bds in boundslist),
            top=max(bds.top for bds in boundslist),
        )

    def __getattr__(self, name: str):
        for elem in self._t:
            if elem.mask.name == name:
                return elem
        raise AttributeError(f"No polygon for mask named '{name}'")

    def __iadd__(self, other):
        if self._frozen_:
            raise ValueError("Can't add layout to a frozen 'MaskPolygons' object")
        if not isinstance(other, MaskPolygons):
            other = tuple(other) if _util.is_iterable(other) else (other,)
            if not all(isinstance(polygons, MaskPolygon) for polygons in other):
                raise TypeError(
                    "Element to add to object of type 'MaskPolygons' has to be of type\n"
                    "'MaskPolygon', 'MaskPolygons' or an iterable of 'MaskPolygon'"
                )

        # Join polygons on the same mask
        new = []
        for polygon in other:
            try:
                p2 = self[polygon.mask]
            except:
                new.append(polygon)
            else:
                p2 += polygon.polygon
        super().__iadd__(new)

        return self

    def __isub__(self, other):
        if self._frozen_:
            raise ValueError("Can't subtract from a frozen 'MaskPolygons' object")
        if isinstance(other, MaskPolygons):
            for polygon in self:
                try:
                    polygon2 = other[polygon.mask]
                except:
                    pass
                else:
                    polygon -= polygon2
        elif isinstance(other, MaskPolygon):
            try:
                polygon = self[other.mask]
            except:
                pass
            else:
                polygon -= other
        else:
            raise TypeError(
                "can only subtrast object of type 'MaskPolygon' or 'MaskPolygons' from\n"
                "a 'MaskPolygons' object"
            )
        return self

    def __add__(self, other):
        newpolygons = MaskPolygons(self)
        newpolygons += other
        return newpolygons

    def __sub__(self, other):
        newpolygons = MaskPolygons(self)
        newpolygons -= other
        return newpolygons


class _SubLayout(abc.ABC):
    @abc.abstractmethod
    def __init__(self, polygons):
        assert isinstance(polygons, MaskPolygons), "Internal error"
        self.polygons = polygons

    @abc.abstractmethod
    def overlaps_with(self, sublayout: "_SubLayout", *, hierarchical: bool=True) -> bool:
        return False

    @abc.abstractmethod
    def dup(self):
        raise AssertionError("Internal error")

    @abc.abstractmethod
    def move(self, dx, dy, rotation="no"):
        if isinstance(self.polygons, geo.MaskShape):
            if rotation == "no":
                polygons = self.polygons
            else:
                polygons = geo.Rotation.from_name(rotation)*self.polygons
            self.polygons = polygons + geo.Point(x=dx, y=dy)
        else:
            assert isinstance(self.polygons, MaskPolygons)
            for pg in self.polygons:
                pg.move(dx, dy, rotation)

    @abc.abstractmethod
    def moved(self, dx, dy, rotation="no"):
        raise AssertionError("Internal error")

    @property
    @abc.abstractmethod
    def _hier_strs_(self) -> Generator[str, None, None]:
        pass


class NetSubLayout(_SubLayout):
    def __init__(self, net: net_.Net, polygons: Union[
        MaskPolygon, MaskPolygons,
    ]):
        self.net = net

        if isinstance(polygons, MaskPolygon):
            polygons = MaskPolygons(polygons)
        super().__init__(polygons)

    def dup(self):
        return NetSubLayout(self.net, self.polygons.dup())

    def move(self, dx, dy, rotation="no"):
        super().move(dx, dy, rotation)

    def moved(self, dx, dy, rotation="no"):
        return NetSubLayout(self.net, MaskPolygons(
            mp.moved(dx, dy, rotation) for mp in self.polygons
        ))

    def __iadd__(self, other):
        assert (
            isinstance(other, NetSubLayout)
            and (self.net == other.net)
        ), "Internal error"
        self.polygons += other.polygons

        return self

    def overlaps_with(self,
        other: Union["NetlessSubLayout", "NetSubLayout", "MultiNetSubLayout"], *,
        hierarchical: bool=True,
    ):
        super().overlaps_with(other, hierarchical=hierarchical)

        if isinstance(other, MultiNetSubLayout):
            return other.overlaps_with(self, hierarchical=hierarchical)

        self_polygons = dict((p.mask, p) for p in self.polygons)
        self_masks = set(self_polygons.keys())
        other_polygons = dict((p.mask, p) for p in other.polygons)
        other_masks = set(other_polygons.keys())
        common_masks = self_masks.intersection(other_masks)

        same_net = (not isinstance(other, NetlessSubLayout)) and (self.net == other.net)
        for mask in common_masks:
            if self_polygons[mask].overlaps_with(other_polygons[mask]):
                if same_net:
                    return True
                else:
                    try:
                        net = cast(NetSubLayout, other).net
                    except:
                        othernet = "None"
                    else:
                        othernet = net.name
                    raise NetOverlapError(
                        f"Overlapping polygons for mask {mask.name} "
                        f"on net '{self.net.name}' and net '{othernet}'"
                    )
        else:
            return False

    @property
    def _hier_strs_(self) -> Generator[str, None, None]:
        yield f"NetSubLayout net={self.net}"
        for mp in self.polygons:
            yield "  " + str(mp)


class NetlessSubLayout(_SubLayout):
    def __init__(self, polygons):
        if isinstance(polygons, MaskPolygon):
            polygons = MaskPolygons(polygons)
        if not isinstance(polygons, MaskPolygons):
            raise TypeError("polygons has to be of type 'MaskPolygon' or 'MaskPolygons'")
        super().__init__(polygons)

    def dup(self):
        return NetlessSubLayout(self.polygons.dup())

    def move(self, dx, dy, rotation="no"):
        super().move(dx, dy, rotation)

    def moved(self, dx, dy, rotation="no"):
        return NetlessSubLayout(MaskPolygons(
            mp.moved(dx, dy, rotation) for mp in self.polygons
        ))

    def __iadd__(self, other):
        assert isinstance(other, NetlessSubLayout), "Internal error"
        self.polygons += other.polygons

        return self

    def overlaps_with(self, other, *, hierarchical=True):
        super().overlaps_with(other, hierarchical=hierarchical)

        if isinstance(other, (NetSubLayout, MultiNetSubLayout)):
            return other.overlaps_with(self, hierarchical=hierarchical)

        assert isinstance(other, NetlessSubLayout), "Internal error"

        self_polygons = dict((p.mask, p) for p in self.polygons)
        self_masks = set(self_polygons.keys())
        other_polygons = dict((p.mask, p) for p in other.polygons)
        other_masks = set(other_polygons.keys())
        common_masks = self_masks.intersection(other_masks)
        for mask in common_masks:
            if self_polygons[mask].overlaps_with(other_polygons[mask]):
                return True
        else:
            return False

    @property
    def _hier_strs_(self) -> Generator[str, None, None]:
        yield f"NetlessSubLayout"
        for mp in self.polygons:
            yield "  " + str(mp)


class MultiNetSubLayout(_SubLayout):
    def __init__(self, sublayouts: Iterable[Union[NetSubLayout, NetlessSubLayout]]):
        self.sublayouts = tuple(sublayouts)

        super().__init__(MaskPolygons())
        self._update_maskpolygon()

    def dup(self):
        return MultiNetSubLayout(sl.dup() for sl in self.sublayouts)

    def move(self, dx, dy, rotation="no"):
        super().move(dx, dy, rotation)
        for sl in self.sublayouts:
            sl.move(dx, dy, rotation)

    def moved(self, dx, dy, rotation="no"):
        return MultiNetSubLayout((
            sl.moved(dx, dy, rotation) for sl in self.sublayouts
        ))

    @property
    def _netmasks(self):
        for netlayout in self.sublayouts:
            for polygon in netlayout.polygons:
                yield polygon.mask

    @property
    def _netpolygons(self):
        for netlayout in self.sublayouts:
            for polygon in netlayout.polygons:
                yield polygon.polygon

    def _update_maskpolygon(self):
        netmasks = set(self._netmasks)
        if len(netmasks) != 1:
            raise ValueError(
                "all layouts in sublayouts have to be on the same mask"
            )
        netmask = netmasks.pop()

        netpolygons = tuple(self._netpolygons)
        maskpolygon = MaskPolygon(netmask, sh_ops.unary_union(netpolygons))
        area = sum(polygon.area for polygon in netpolygons)
        if not all((
            isinstance(maskpolygon.polygon, sh_geo.Polygon),
            abs(area - maskpolygon.polygon.area)/area < 1e-4,
        )):
            raise ValueError(
                "sublayouts has to consist of touching, non-overlapping subblocks"
            )
        self.polygons = MaskPolygons(maskpolygon)

    def __iadd__(self, other):
        if not isinstance(other, _SubLayout):
            raise TypeError("Can only add object of type '_SubLayout'")

        assert len(self.polygons) == 1, "Internal error"
        self_polygon = self.polygons[0]

        if isinstance(other, (NetSubLayout, NetlessSubLayout)):
            if len(other.polygons) != 1:
                raise ValueError(
                    "Can only add single polygon sublayout to 'MultiNetSubLayout'"
                )
            else:
                other_polygon = other.polygons[0]
                if self_polygon.mask != other_polygon.mask:
                    raise ValueError(
                        f"Polygon on mask {other_polygon.mask.name} can't be added to\n"
                        f"'MultiNetSubLayout' polygon on mask {self_polygon.mask.name}"
                    )
                for self_sublayout in self.sublayouts:
                    if self_sublayout.overlaps_with(other, hierarchical=False):
                        self_sublayout += other
                        self._update_maskpolygon()
                        break
                else:
                    raise ValueError(
                        "Can only add overlapping polygon to 'MultiNetSubLayout'"
                    )
        else:
            assert isinstance(other, MultiNetSubLayout), "Internal error"
            for other_sublayout in other.sublayouts:
                for self_sublayout in self.sublayouts:
                    if other_sublayout.overlaps_with(self_sublayout, hierarchical=False):
                        self_sublayout += other_sublayout
                        break
                else:
                    self.sublayouts += (other_sublayout,)
            self._update_maskpolygon()

        return self

    def merge_from(self, other):
        """Extract overlapping polygon from other and add it to itself

        return wether other is now empty"""
        if not self.overlaps_with(other, hierarchical=False):
            return False

        if isinstance(other, MultiNetSubLayout):
            self += other
            return True
        else:
            assert len(self.polygons) == 1

            def add_polygon(self, other_polygon):
                if isinstance(other, NetSubLayout):
                    self += NetSubLayout(other.net, other_polygon)
                elif isinstance(other, NetlessSubLayout):
                    self += NetlessSubLayout(other_polygon)
                else:
                    raise AssertionError("Internal error")

            self_polygon = self.polygons[0]
            other_polygon = other.polygons[self_polygon.mask]
            if isinstance(other_polygon.polygon, sh_geo.Polygon):
                add_polygon(self, other_polygon)
                other.polygons.pop(self_polygon.mask)
            elif isinstance(other_polygon.polygon, sh_geo.MultiPolygon):
                # Take only parts of other polygon that overlap with out polygon
                for p2 in filter(
                    lambda p: self_polygon.polygon.intersects(p),
                    other_polygon.polygon,
                ):
                    add_polygon(self, MaskPolygon(other_polygon.mask, p2))
                    other_polygon.polygon = other_polygon.polygon.difference(p2)
                if not other_polygon.polygon:
                    other.polygons.pop(self_polygon.mask)
            else:
                raise AssertionError("Internal error")

            return not other.polygons

    def overlaps_with(self, other, *, hierarchical=True):
        super().overlaps_with(other, hierarchical=hierarchical)

        assert len(self.polygons) == 1, "Internal error"
        self_polygon = self.polygons[0]

        for other_polygon in filter(
            lambda p: p.mask == self_polygon.mask,
            other.polygons,
        ):
            if self_polygon.overlaps_with(other_polygon):
                # Recursively call overlaps_with to check for wrong net overlaps.
                for sublayout in self.sublayouts:
                    if other.overlaps_with(sublayout, hierarchical=hierarchical):
                        return True
                else:
                    # This should not happen: joined polygon overlaps but none of
                    # the sublayout overlaps.
                    raise AssertionError("Internal error")
        else:
            return False

    @property
    def _hier_strs_(self) -> Generator[str, None, None]:
        yield f"MultiNetSubLayout"
        for sl in self.sublayouts:
            for s in sl._hier_strs_:
                yield "  " + s


class MaskShapesSubLayout(_SubLayout):
    """Object representing the sublayout of a net consisting of geometry._Shape
    objects.

    Arguments:
        net: The net of the SubLayout
            `None` value represents no net for the shapes.
        shapes: The maskshapes on the net.
    """
    def __init__(self, *, net: Optional[net_.Net], shapes: geo.MaskShapes):
        self._net = net
        self._shapes = shapes

    @property
    def net(self) -> Optional[net_.Net]:
        return self._net
    @property
    def shapes(self) -> geo.MaskShapes:
        return self._shapes

    def add_shape(self, *, shape: geo.MaskShape):
        self._shapes += shape

    def overlaps_with(self, sublayout: "_SubLayout", *, hierarchical: bool) -> bool:
        raise NotImplementedError()

    def move(self, dx: float, dy: float, rotation: str):
        if rotation == "no":
            shapes = self.shapes
        else:
            shapes = geo.Rotation.from_name(rotation)*self.shapes
        self._shapes = (shapes + geo.Point(x=dx, y=dy))

    def moved(self, dx: float, dy: float, rotation: str) -> "MaskShapesSubLayout":
        r = geo.Rotation.from_name(rotation)
        return MaskShapesSubLayout(
            net=self.net, shapes=(r*self.shapes + geo.Point(x=dx, y=dy)),
        )

    def dup(self) -> "MaskShapesSubLayout":
        return MaskShapesSubLayout(
            net=self.net, shapes=geo.MaskShapes(self.shapes),
        )

    @property
    def _hier_strs_(self) -> Generator[str, None, None]:
        yield f"MaskShapesSubLayout net={self.net}"
        for ms in self.shapes:
            yield "  " + str(ms)

    def __hash__(self):
        return hash((self.net, self.shapes))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MaskShapesSubLayout):
            return (self.net == other.net) and (self.shapes == other.shapes)
        else:
            return False


class _InstanceSubLayout(_SubLayout):
    def __init__(self, inst, *, x, y, layoutname, rotation):
        assert (
            isinstance(inst, ckt._CellInstance)
            and isinstance (x, float) and isinstance(y, float)
            and ((layoutname is None) or isinstance(layoutname, str))
            and (rotation in _rotations)
        ), "Internal error"
        self.inst = inst
        self.x = x
        self.y = y
        self.rotation = rotation
        cell = inst.cell

        if layoutname is None:
            try:
                # Create default layout
                l = cell.layout
            except:
                raise ValueError(
                    f"Cell '{cell.name}' has no default layout and no layoutname"
                    " was specified"
                )
        else:
            if layoutname not in cell.layouts.keys():
                raise ValueError(
                    f"Cell '{cell.name}' has no layout named '{layoutname}'"
                )
            self.layoutname = layoutname
        # layout is a property and will only be looked up the first time it is accessed.
        # This is to support cell with delayed layout generation.
        self._layout = None

    @property
    def layout(self):
        if self._layout is None:
            l = (
                self.inst.cell.layouts[self.layoutname] if hasattr(self, "layoutname")
                else self.inst.cell.layout
            )
            self._layout = l.moved(dx=self.x, dy=self.y, rotation=self.rotation)

        return self._layout

    @property
    def boundary(self) -> geo._Rectangular:
        l = (
            self.inst.cell.layouts[self.layoutname] if hasattr(self, "layoutname")
            else self.inst.cell.layout
        )
        assert l.boundary is not None
        return l.boundary.rotated(
            rotation=geo.Rotation.from_name(self.rotation),
        ) + geo.Point(x=self.x, y=self.y)

    @property
    def polygons(self):
        return self.layout.polygons

    def overlaps_with(self, other, *, hierarchical=True):
        if hierarchical:
            return any(
                p1.overlaps_with(p2) for p1, p2 in product(
                    self.polygons, other.polygons,
                ))
        else:
            return False

    def dup(self):
        return self

    def _rotation(self, rotation):
        x = self.x
        y = self.y
        _xylookup = {
            "no": (x, y),
            "90": (-y, x),
            "180": (-x, -y),
            "270": (y, -x),
            "mirrorx": (-x, y),
            "mirrorx&90": (-y, -x),
            "mirrory": (x, -y),
            "mirrory&90": (y, x),
        }
        _rotlookup = {
            "no": {
                "no": "no",
                "90": "90",
                "180": "180",
                "270": "270",
                "mirrorx": "mirrorx",
                "mirrorx&90": "mirrorx&90",
                "mirrory": "mirrory",
                "mirrory&90": "mirrory&90",
            },
            "90": {
                "no": "90",
                "90": "180",
                "180": "270",
                "270": "no",
                "mirrorx": "mirrory&90",
                "mirrorx&90": "270",
                "mirrory": "mirrorx&90",
                "mirrory&90": "mirrorx",
            },
            "180": {
                "no": "180",
                "90": "270",
                "180": "no",
                "270": "90",
                "mirrorx": "mirrory",
                "mirrorx&90": "mirrory&90",
                "mirrory": "mirrorx",
                "mirrory&90": "mirrorx&90",
            },
            "270": {
                "no": "270",
                "90": "no",
                "180": "90",
                "270": "180",
                "mirrorx": "mirrory&90",
                "mirrorx&90": "mirrorx",
                "mirrory": "mirrorx&90",
                "mirrory&90": "mirrory",
            },
            "mirrorx": {
                "no": "mirrorx",
                "90": "mirrorx&90",
                "180": "mirrory",
                "270": "mirrory&90",
                "mirrorx": "no",
                "mirrorx&90": "90",
                "mirrory": "180",
                "mirrory&90": "270",
            },
            "mirrorx&90": {
                "no": "mirrorx&90",
                "90": "mirrory",
                "180": "mirrory&90",
                "270": "mirrorx",
                "mirrorx": "270",
                "mirrorx&90": "no",
                "mirrory": "90",
                "mirrory&90": "180",
            },
            "mirrory": {
                "no": "mirrory",
                "90": "mirrory&90",
                "180": "mirrorx",
                "270": "mirrorx&90",
                "mirrorx": "180",
                "mirrorx&90": "270",
                "mirrory": "no",
                "mirrory&90": "90",
            },
            "mirrory&90": {
                "no": "mirrory&90",
                "90": "mirrorx",
                "180": "mirrorx&90",
                "270": "mirrory",
                "mirrorx": "90",
                "mirrorx&90": "180",
                "mirrory": "270",
                "mirrory&90": "no",
            },
        }

        return (*_xylookup[rotation], _rotlookup[self.rotation][rotation])

    def move(self, dx, dy, rotation="no"):
        x, y, rot2 = self._rotation(rotation)
        self.x += x + dx
        self.y += y + dy
        self.rotation = rot2
        self._layout = None

    def moved(self, dx, dy, rotation="no"):
        x, y, rot2 = self._rotation(rotation)
        return _InstanceSubLayout(
            self.inst, x=(x + dx), y=(y + dy),
            layoutname=(self.layoutname if hasattr(self, "layoutname") else None),
            rotation=rot2
        )

    @property
    def _hier_strs_(self) -> Generator[str, None, None]:
        yield f"_InstanceSubLayout inst={self.inst}, x={self.x}, y={self.y}, rot={self.rotation}"
        for s in self.layout._hier_strs_:
            yield "  " + s


class SubLayouts(_util.TypedList[_SubLayout]):
    _elem_type_ = _SubLayout

    def __init__(self, iterable: SingleOrMulti[_SubLayout].T=tuple()):
        if isinstance(iterable, _SubLayout):
            super().__init__((iterable,))
        else:
            super().__init__(iterable)

    def dup(self) -> "SubLayouts":
        return SubLayouts(l.dup() for l in self)

    def __iadd__(self, other_: SingleOrMulti[_SubLayout].T) -> "SubLayouts":
        other: Iterable[_SubLayout]
        if isinstance(other_, _SubLayout):
            other = (other_,)
        else:
            other = tuple(other_)

        # First try to add the sublayout to the multinet polygons
        multinets = tuple(self.__iter_type__(MultiNetSubLayout))
        def add2multinet(other_sublayout):
            if isinstance(other_sublayout, (MaskShapesSubLayout, _InstanceSubLayout)):
                return False
            for multinet in multinets:
                if multinet.overlaps_with(other_sublayout, hierarchical=False):
                    return multinet.merge_from(other_sublayout)
            else:
                return False
        other = filter(lambda sl: not add2multinet(sl), other)

        # Now try to add to other sublayouts
        def add2other(other_sublayout):
            if isinstance(other_sublayout, MultiNetSubLayout):
                for sublayout in self:
                    if (
                        (not isinstance(sublayout, _InstanceSubLayout))
                        and sublayout.overlaps_with(other_sublayout, hierarchical=False)
                    ):
                        if other_sublayout.merge_from(sublayout):
                            self.remove(sublayout)
                return False
            elif isinstance(other_sublayout, (NetlessSubLayout, NetSubLayout)):
                # Can only add to same type
                for sublayout in self.__iter_type__(other_sublayout.__class__):
                    if (
                        # Add all netless together
                        isinstance(other_sublayout, NetlessSubLayout)
                        # or polygons on same net
                        or (cast(NetSubLayout, sublayout).net == other_sublayout.net)
                    ):
                        # TODO: remove ignore after Pylance fix
                        sublayout += other_sublayout # type: ignore
                        return True
                else:
                    return False
            elif isinstance(other_sublayout, MaskShapesSubLayout):
                for sublayout in self.__iter_type__(MaskShapesSubLayout):
                    if sublayout.net == other_sublayout.net:
                        for shape in other_sublayout.shapes:
                            sublayout.add_shape(shape=shape)
                        return True
                else:
                    return False
            elif not isinstance(other_sublayout, _InstanceSubLayout):
                raise AssertionError("Internal error")
        other = tuple(filter(lambda sl: not add2other(sl), other))

        if other:
            # Append remaining sublayouts
            self.extend(sl.dup() for sl in other)
        return self

    def __add__(self, other: SingleOrMulti[_SubLayout].T) -> "SubLayouts":
        ret = self.dup()
        ret += other
        return ret


class _Layout:
    def __init__(self, fab, sublayouts):
        assert (
            isinstance(fab, LayoutFactory)
            and isinstance(sublayouts, SubLayouts)
        ), "Internal error"
        self.fab = fab
        self.sublayouts = sublayouts

        self.boundary: Optional[geo._Rectangular] = None

    @property
    def polygons(self) -> Generator[Union[MaskPolygon, geo.MaskShape], None, None]:
        for sublayout in self.sublayouts:
            if isinstance(sublayout, MaskShapesSubLayout):
                yield from sublayout.shapes
            else:
                yield from sublayout.polygons

    @property
    def top_polygons(self):
        for sublayout in self.sublayouts.__iter_type__((
            NetlessSubLayout, NetSubLayout, MultiNetSubLayout,
        )):
            yield from sublayout.polygons

    def _net_sublayouts(self, *, net: net_.Net, depth: Optional[int]) -> Generator[
        NetSubLayout, None, None,
    ]:
        for sl in self.sublayouts:
            if isinstance(sl, NetlessSubLayout):
                pass
            elif isinstance(sl, NetSubLayout):
                if sl.net == net:
                    yield sl
            elif isinstance(sl, MultiNetSubLayout):
                yield from cast(Iterable[NetSubLayout], filter(
                    lambda sl2: isinstance(sl2, NetSubLayout) and (sl2.net == net),
                    sl.sublayouts,
                ))
            elif isinstance(sl, _InstanceSubLayout):
                assert isinstance(net, ckt._CircuitNet)
                if depth != 0:
                    for port in net.childports:
                        if (
                            isinstance(port, ckt._InstanceNet)
                            and (port.inst == sl.inst)
                        ):
                            yield from sl.layout._net_sublayouts(
                                net=port.net,
                                depth=(None if depth is None else (depth - 1)),
                            )
            elif isinstance(sl, MaskShapesSubLayout):
                if net == sl.net:
                    yield sl
            else:
                raise AssertionError("Internal error")

    def net_polygons(self, net: net_.Net, *, depth: Optional[int]=None) -> Generator[
        Union[MaskPolygon, geo.MaskShape], None, None
    ]:
        if not isinstance(net, net_.Net):
            raise TypeError("net has to be of type 'Net'")
        for sl in self._net_sublayouts(net=net, depth=depth):
            if isinstance(sl, MaskShapesSubLayout):
                yield from sl.shapes
            else:
                yield from sl.polygons

    def filter_polygons(self, *,
        net: Optional[net_.Net]=None, mask: Optional[msk._Mask]=None,
        split: bool=False, depth: Optional[int]=None,
    ) -> Generator[Union[MaskPolygon, geo.MaskShape], None, None]:
        if net is None:
            sls = self.sublayouts
        else:
            sls = self._net_sublayouts(net=net, depth=depth)
        for sl in sls:
            if isinstance(sl, MaskShapesSubLayout):
                if mask is None:
                    shapes = sl.shapes
                else:
                    shapes = filter(lambda sh: sh.mask == mask, sl.shapes)
                if not split:
                    yield from shapes
                else:
                    for shape in shapes:
                        for shape2 in shape.shape.pointsshapes:
                            yield geo.MaskShape(mask=shape.mask, shape=shape2)
            else:
                assert isinstance(sl.polygons, MaskPolygons)
                for poly in sl.polygons:
                    if (mask is not None) and (poly.mask != mask):
                        continue
                    if split:
                        yield from poly.polygons
                    else:
                        yield poly

    def dup(self) -> "_Layout":
        l = _Layout(
            fab=self.fab,
            sublayouts=SubLayouts(sl.dup() for sl in self.sublayouts),
        )
        l.boundary = self.boundary
        return l

    def bounds(self, *,
        mask: Optional[msk._Mask]=None, net: Optional[net_.Net]=None,
        depth: Optional[int]=None,
    ) -> geo.Rect:
        if net is None:
            if depth is not None:
                raise TypeError(
                    f"depth has to 'None' if net is 'None'"
                )
            polygons = self.polygons
        else:
            polygons = self.net_polygons(net, depth=depth)
        mps = polygons if mask is None else filter(
            lambda mp: mp.mask == mask, polygons,
        )
        boundslist = tuple(mp.bounds for mp in mps)
        return geo.Rect(
            left=min(bds.left for bds in boundslist),
            bottom=min(bds.bottom for bds in boundslist),
            right=max(bds.right for bds in boundslist),
            top=max(bds.top for bds in boundslist),
        )

    def __iadd__(self, other):
        if self.sublayouts._frozen_:
            raise ValueError("Can't add sublayouts to a frozen 'Layout' object")
        if not isinstance(other, (_Layout, _SubLayout, SubLayouts)):
            raise TypeError(
                "Can only add '_Layout', '_SubLayout' or 'SubLayouts' object to"
                " a '_Layout' object"
            )

        self.sublayouts += (
            other.sublayouts if isinstance(other, _Layout) else other
        )

        return self

    def add_primitive(self, *,
        prim: prm._Primitive, x: float=0.0, y: float=0.0, rotation: str="no",
        **prim_params,
    ) -> "_Layout":
        if not (prim in self.fab.tech.primitives):
            raise ValueError(
                f"prim '{prim.name}' is not a primitive of technology"
                f" '{self.fab.tech.name}'"
            )
        if rotation not in _rotations:
            raise ValueError(
                f"rotation '{rotation}' is not one of {_rotations}"
            )

        primlayout = self.fab.new_primitivelayout(prim, **prim_params)
        primlayout.move(dx=x, dy=y, rotation=rotation)
        self += primlayout
        return primlayout

    def add_wire(self, *,
        net: net_.Net, wire: prm._Conductor, shape: Optional[geo._Shape]=None,
        **wire_params,
    ) -> "_Layout":
        if (shape is None) or isinstance(shape, geo.Rect):
            if shape is not None:
                # TODO: Add support in _PrimitiveLayouter for shape argument,
                # e.g. non-rectangular shapes
                c = shape.center
                wire_params.update({
                    "x": c.x, "y": c.y,
                    "width": shape.width, "height": shape.height,
                })
            return self.add_primitive(
                portnets={"conn": net}, prim=wire, **wire_params,
            )
        else:
            pin = wire_params.pop("pin", None)
            if len(wire_params) != 0:
                raise TypeError(
                    f"params {wire_params.keys()} not supported for shape not of type 'Rect'",
                )
            l = self.fab.new_layout()
            self.add_shape(net=net, prim=wire, shape=shape)
            l.add_shape(net=net, prim=wire, shape=shape)
            if pin is not None:
                self.add_shape(net=net, prim=pin, shape=shape)
                l.add_shape(net=net, prim=pin, shape=shape)
            return l

    def add_maskshape(self, *, net: Optional[net_.Net]=None, maskshape: geo.MaskShape):
        """Add a geometry MaskShape to a _Layout
        """
        for sl in self.sublayouts.__iter_type__(MaskShapesSubLayout):
            if sl.net == net:
                sl.add_shape(shape=maskshape)
                break
        else:
            self.sublayouts += MaskShapesSubLayout(
                net=net, shapes=geo.MaskShapes(maskshape),
            )

    def add_shape(self, *,
        prim: prm._DesignMaskPrimitive, net: Optional[net_.Net]=None, shape: geo._Shape,
    ):
        """Add a geometry _Shape to a _Layout
        """
        self.add_maskshape(
            net=net,
            maskshape=geo.MaskShape(mask=cast(msk.DesignMask, prim.mask), shape=shape),
        )

    def move(self, dx, dy, rotation="no"):
        for mp in self.sublayouts:
            mp.move(dx, dy, rotation)

    def moved(self, dx, dy, rotation="no"):
        l = _Layout(
            self.fab, SubLayouts(sl.moved(dx, dy, rotation) for sl in self.sublayouts),
        )

        if self.boundary is None:
            bound = None
        else:
            bound = self.boundary
            if rotation != "no":
                bound = bound.rotated(rotation=geo.Rotation.from_name(rotation))
            bound = bound + geo.Point(x=dx, y=dy)
        l.boundary = bound

        return l

    def freeze(self):
        self.sublayouts._freeze_()

    @property
    def _hier_str_(self) -> str:
        return "\n  ".join(("layout:", *(s for s in self._hier_strs_)))

    @property
    def _hier_strs_(self) -> Generator[str, None, None]:
        for sl in self.sublayouts:
            yield from sl._hier_strs_


class _PrimitiveLayouter(dsp.PrimitiveDispatcher):
    def __init__(self, fab: "LayoutFactory"):
        self.fab = fab

    def __call__(self, prim: prm._Primitive, *args, **kwargs) -> _Layout:
        return super().__call__(prim, *args, **kwargs)

    @property
    def tech(self):
        return self.fab.tech

    # Dispatcher implementation
    def _Primitive(self, prim: prm._Primitive, **params):
        raise NotImplementedError(
            f"Don't know how to generate minimal layout for primitive '{prim.name}'\n"
            f"of type '{prim.__class__.__name__}'"
        )

    def Marker(self, prim: prm.Marker, **params) -> _Layout:
        if ("width" in params) and ("height" in params):
            return self._WidthSpacePrimitive(cast(prm._WidthSpacePrimitive, prim), **params)
        else:
            return super().Marker(prim, **params)

    def _WidthSpacePrimitive(self,
        prim: prm._WidthSpacePrimitive, **widthspace_params,
    ) -> _Layout:
        if len(prim.ports) != 0:
            raise NotImplementedError(
                f"Don't know how to generate minimal layout for primitive '{prim.name}'\n"
                f"of type '{prim.__class__.__name__}'"
            )
        width = widthspace_params["width"]
        height = widthspace_params["height"]
        r = geo.Rect.from_size(width=width, height=height)

        l = self.fab.new_layout()
        assert isinstance(prim, prm._DesignMaskPrimitive)
        l.add_shape(prim=prim, shape=r)
        return l

    def _WidthSpaceConductor(self,
        prim: prm._WidthSpaceConductor, **conductor_params,
    ) -> _Layout:
        assert (
            (len(prim.ports) == 1) and (prim.ports[0].name == "conn")
        ), "Internal error"
        width = conductor_params["width"]
        height = conductor_params["height"]
        r = geo.Rect.from_size(width=width, height=height)

        try:
            portnets = conductor_params["portnets"]
        except KeyError:
            net = prim.ports.conn
        else:
            net = portnets["conn"]

        layout = self.fab.new_layout()
        layout.add_shape(prim=prim, net=net, shape=r)
        pin = conductor_params.get("pin", None)
        if pin is not None:
            layout.add_shape(prim=pin, net=net, shape=r)

        return layout

    def WaferWire(self, prim: prm.WaferWire, **waferwire_params) -> _Layout:
        width = waferwire_params["width"]
        height = waferwire_params["height"]

        implant = waferwire_params.pop("implant")
        implant_enclosure = waferwire_params.pop("implant_enclosure")
        assert implant_enclosure is not None

        well = waferwire_params.pop("well", None)
        well_enclosure = waferwire_params.pop("well_enclosure", None)

        oxide = waferwire_params.pop("oxide", None)
        oxide_enclosure = waferwire_params.pop("oxide_enclosure", None)

        layout = self._WidthSpaceConductor(prim, **waferwire_params)
        layout.add_shape(prim=implant, shape=_rect(
            -0.5*width, -0.5*height, 0.5*width, 0.5*height,
            enclosure=implant_enclosure,
        ))
        if well is not None:
            try:
                well_net = waferwire_params["well_net"]
            except KeyError:
                raise TypeError(
                    f"No well_net given for WaferWire '{prim.name}' in well '{well.name}'"
                )
            layout.add_shape(prim=well, net=well_net, shape=_rect(
                -0.5*width, -0.5*height, 0.5*width, 0.5*height,
                enclosure=well_enclosure,
            ))
        if oxide is not None:
            layout.add_shape(prim=oxide, shape=_rect(
                -0.5*width, -0.5*height, 0.5*width, 0.5*height,
                enclosure=oxide_enclosure,
            ))
        return layout

    def Via(self, prim: prm.Via, **via_params) -> _Layout:
        try:
            portnets = via_params["portnets"]
        except KeyError:
            net = prim.ports.net
        else:
            if set(portnets.keys()) != {"conn"}:
                raise ValueError(f"Via '{prim.name}' needs one net for the 'conn' port")
            net = portnets["conn"]

        bottom = via_params["bottom"]
        bottom_enc = via_params["bottom_enclosure"]
        if bottom_enc is None:
            idx = prim.bottom.index(bottom)
            bottom_enc = prim.min_bottom_enclosure[idx]
        if isinstance(bottom_enc.spec, float):
            bottom_enc_x = bottom_enc_y = bottom_enc.spec
        else:
            bottom_enc_x = bottom_enc.spec[0]
            bottom_enc_y = bottom_enc.spec[1]

        top = via_params["top"]
        top_enc = via_params["top_enclosure"]
        if top_enc is None:
            idx = prim.top.index(top)
            top_enc = prim.min_top_enclosure[idx]
        if isinstance(top_enc.spec, float):
            top_enc_x = top_enc_y = top_enc.spec
        else:
            top_enc_x = top_enc.spec[0]
            top_enc_y = top_enc.spec[1]

        width = prim.width
        space = via_params["space"]
        pitch = width + space

        rows = via_params["rows"]
        if rows is None:
            bottom_height = via_params["bottom_height"]
            if bottom_height is None:
                top_height = via_params["top_height"]
                assert top_height is not None, "Internal error"

                rows = int((top_height - 2*top_enc_y - width)//pitch + 1)
                via_height = rows*pitch - space
                bottom_height = via_height + 2*bottom_enc_y
            else:
                rows = int((bottom_height - 2*bottom_enc_y - width)//pitch + 1)
                via_height = rows*pitch - space
                top_height = via_height + 2*top_enc_y
        else:
            via_height = rows*pitch - space
            bottom_height = via_height + 2*bottom_enc_y
            top_height = via_height + 2*top_enc_y

        columns = via_params["columns"]
        if columns is None:
            bottom_width = via_params["bottom_width"]
            if bottom_width is None:
                top_width = via_params["top_width"]
                assert top_width is not None, "Internal error"

                columns = int((top_width - 2*top_enc_x - width)//pitch + 1)
                via_width = columns*pitch - space
                bottom_width = via_width + 2*bottom_enc_x
            else:
                columns = int((bottom_width - 2*bottom_enc_x - width)//pitch + 1)
                via_width = columns*pitch - space
                top_width = via_width + 2*top_enc_x
        else:
            via_width = columns*pitch - space
            bottom_width = via_width + 2*bottom_enc_x
            top_width = via_width + 2*top_enc_x

        bottom_left = -0.5*bottom_width
        bottom_bottom = -0.5*bottom_height
        bottom_right = 0.5*bottom_width
        bottom_top = 0.5*bottom_height

        via_bottom = -0.5*via_height
        via_left = -0.5*via_width

        layout = cast(_Layout, self.fab.new_layout())

        layout.add_shape(prim=bottom, net=net, shape=geo.Rect.from_size(
            width=bottom_width, height=bottom_height,
        ))
        layout.add_shape(prim=prim, net=net, shape=_via_array(
            via_left, via_bottom, width, pitch, rows, columns,
        ))
        layout.add_shape(prim=top, net=net, shape=geo.Rect.from_size(
            width=top_width, height=top_height,
        ))
        try:
            impl = via_params["bottom_implant"]
        except KeyError:
            impl = None
        else:
            if impl is not None:
                enc = via_params["bottom_implant_enclosure"]
                assert enc is not None, "Internal error"
                layout.add_shape(prim=impl, shape=_rect(
                    bottom_left, bottom_bottom, bottom_right, bottom_top,
                    enclosure=enc,
                ))
        try:
            well = via_params["bottom_well"]
        except KeyError:
            well = None
        else:
            if well is not None:
                well_net = via_params.get("well_net", None)
                enc = via_params["bottom_well_enclosure"]
                assert enc is not None, "Internal error"
                if (impl is not None) and (impl.type_ == well.type_):
                    if well_net is not None:
                        if well_net != net:
                            raise ValueError(
                                f"Net '{well_net}' for well '{well.name}' of WaferWire"
                                f" {bottom.name} is different from net '{net.name}''\n"
                                f"\tbut implant '{impl.name}' is same type as the well"
                            )
                    else:
                        well_net = net
                elif well_net is None:
                    raise TypeError(
                        f"No well_net specified for WaferWire '{bottom.name}' in"
                        f" well '{well.name}'"
                    )
                layout.add_shape(prim=well, net=well_net, shape=_rect(
                    bottom_left, bottom_bottom, bottom_right, bottom_top,
                    enclosure=enc,
                ))

        return layout

    def Resistor(self, prim: prm.Resistor, **resistor_params) -> _Layout:
        try:
            portnets = resistor_params["portnets"]
        except KeyError:
            port1 = prim.ports.port1
            port2 = prim.ports.port2
        else:
            if set(portnets.keys()) != {"port1", "port2"}:
                raise ValueError(
                    f"Resistor '{prim.name}' needs two port nets ('port1', 'port2')"
                )
            port1 = portnets["port1"]
            port2 = portnets["port2"]
        if prim.contact is None:
            raise NotImplementedError("Resistor layout without contact layer")

        res_width = resistor_params["width"]
        res_height = resistor_params["height"]

        wire = prim.wire

        cont = prim.contact
        cont_space = prim.min_contact_space
        assert cont_space is not None
        try:
            wire_idx = cont.bottom.index(wire)
        except ValueError:
            try:
                wire_idx = cont.top.index(wire)
            except ValueError:
                raise AssertionError("Internal error")
            else:
                cont_enc = cont.min_top_enclosure[wire_idx]
                cont_args = {"top": wire, "x": 0.0, "top_width": res_width}
        else:
            cont_enc = cont.min_bottom_enclosure[wire_idx]
            cont_args = {"bottom": wire, "x": 0.0, "bottom_width": res_width}
        cont_y1 = -0.5*res_height - cont_space - 0.5*cont.width
        cont_y2 = -cont_y1

        wire_ext = cont_space + cont.width + cont_enc.min()

        layout = self.fab.new_layout()

        # Draw indicator layers
        for idx, ind in enumerate(prim.indicator):
            ext = prim.min_indicator_extension[idx]
            layout += self(ind, width=(res_width + 2*ext), height=res_height)

        # Draw wire layer
        mp = geo.MultiPartShape(
            fullshape=geo.Rect.from_size(
                width=res_width, height=(res_height + 2*wire_ext),
            ),
            parts = (
                geo.Rect.from_floats(values=(
                    -0.5*res_width, -0.5*res_height - wire_ext,
                    0.5*res_width, -0.5*res_height,
                )),
                geo.Rect.from_floats(values=(
                    -0.5*res_width, -0.5*res_height,
                    0.5*res_width, 0.5*res_height,
                )),
                geo.Rect.from_floats(values=(
                    -0.5*res_width, 0.5*res_height,
                    0.5*res_width, 0.5*res_height + wire_ext,
                )),
            )
        )
        layout.add_shape(prim=wire, net=port1, shape=mp.parts[0])
        layout.add_shape(prim=wire, shape=mp.parts[1])
        layout.add_shape(prim=wire, net=port2, shape=mp.parts[2])

        # Draw contacts
        layout.add_wire(net=port1, wire=cont, y=cont_y1, **cont_args)
        layout.add_wire(net=port2, wire=cont, y=cont_y2, **cont_args)

        if prim.implant is not None:
            impl = prim.implant
            try:
                enc = prim.min_implant_enclosure.max() # type: ignore
            except AttributeError:
                assert isinstance(wire, prm.WaferWire), "Internal error"
                idx = wire.implant.index(impl)
                enc = wire.min_implant_enclosure[idx].max()
            impl_width = res_width + 2*enc
            impl_height = res_height + 2*wire_ext + 2*enc
            layout.add_shape(prim=impl, shape=geo.Rect.from_size(width=impl_width, height=impl_height))

        return layout

    def Diode(self, prim: prm.Diode, **diode_params) -> _Layout:
        try:
            portnets = diode_params.pop("portnets")
        except KeyError:
            an = prim.ports.anode
            cath = prim.ports.cathode
        else:
            if set(portnets.keys()) != {"anode", "cathode"}:
                raise ValueError(
                    f"Diode '{prim.name}' needs two port nets ('anode', 'cathode')"
                )
            an = portnets["anode"]
            cath = portnets["cathode"]

        if prim.min_implant_enclosure is not None:
            raise NotImplementedError(
                "Diode layout generation with min_implant_enclosure specified"
            )
        wirenet_args = {
            "implant": prim.implant,
            "net": an if prim.implant.type_ == "p" else cath,
        }
        if prim.well is not None:
            wirenet_args.update({
                "well": prim.well,
                "well_net": cath if prim.implant.type_ == "p" else an,
            })

        layout = self.fab.new_layout()
        layout.add_wire(wire=prim.wire, **wirenet_args, **diode_params)
        wireact_bounds = layout.bounds(mask=prim.wire.mask)
        act_width = wireact_bounds.right - wireact_bounds.left
        act_height = wireact_bounds.top - wireact_bounds.bottom

        for i, ind in enumerate(prim.indicator):
            enc = prim.min_indicator_enclosure[i].max()
            layout += self(ind, width=(act_width + 2*enc), height=(act_height + 2*enc))

        return layout

    def MOSFET(self, prim: prm.MOSFET, **mos_params) -> _Layout:
        l = mos_params["l"]
        w = mos_params["w"]
        impl_enc = mos_params["activeimplant_enclosure"]
        gate_encs = mos_params["gateimplant_enclosures"]
        sdw = mos_params["sd_width"]

        try:
            portnets = cast(Mapping[str, net_.Net], mos_params["portnets"])
        except KeyError:
            portnets = prim.ports

        gate_left = -0.5*l
        gate_right = 0.5*l
        gate_top = 0.5*w
        gate_bottom = -0.5*w

        layout = self.fab.new_layout()

        active = prim.gate.active
        active_width = l + 2*sdw
        active_left = -0.5*active_width
        active_right = 0.5*active_width
        active_bottom = gate_bottom
        active_top = gate_top

        mps = geo.MultiPartShape(
            fullshape=geo.Rect.from_size(width=active_width, height=w),
            parts=(
                geo.Rect(
                    left=active_left, bottom=active_bottom,
                    right=gate_left, top=active_top,
                ),
                geo.Rect(
                    left=gate_left, bottom =active_bottom,
                    right=gate_right, top=active_top,
                ),
                geo.Rect(
                    left=gate_right, bottom =active_bottom,
                    right=active_right, top=active_top,
                ),
            )
        )
        layout.add_shape(prim=active, net=portnets["sourcedrain1"], shape=mps.parts[0])
        layout.add_shape(prim=active, net=portnets["bulk"], shape=mps.parts[1])
        layout.add_shape(prim=active, net=portnets["sourcedrain2"], shape=mps.parts[2])

        for impl in prim.implant:
            if impl in active.implant:
                layout.add_shape(prim=impl, shape=_rect(
                    active_left, active_bottom, active_right, active_top,
                    enclosure=impl_enc
                ))

        poly = prim.gate.poly
        ext = prim.computed.min_polyactive_extension
        poly_left = gate_left
        poly_bottom = gate_bottom - ext
        poly_right = gate_right
        poly_top = gate_top + ext
        layout.add_shape(prim=poly, net=portnets["gate"], shape=geo.Rect(
            left=poly_left, bottom=poly_bottom, right=poly_right, top=poly_top,
        ))

        if prim.well is not None:
            enc = active.min_well_enclosure[active.well.index(prim.well)]
            layout.add_shape(prim=prim.well, net=portnets["bulk"], shape=_rect(
                active_left, active_bottom, active_right, active_top, enclosure=enc,
            ))

        if prim.gate.oxide is not None:
            # TODO: Check is there is an enclosure rule from oxide around active
            # and apply the if so.
            enc = getattr(
                prim.gate, "min_gateoxide_enclosure", prp.Enclosure(self.tech.grid),
            )
            layout.add_shape(prim=prim.gate.oxide, shape=_rect(
                gate_left, gate_bottom, gate_right, gate_top, enclosure=enc,
            ))

        if prim.gate.inside is not None:
            # TODO: Check is there is an enclosure rule from oxide around active
            # and apply the if so.
            for i, inside in enumerate(prim.gate.inside):
                enc = (
                    prim.gate.min_gateinside_enclosure[i]
                    if prim.gate.min_gateinside_enclosure is not None
                    else prp.Enclosure(self.tech.grid)
                )
                layout.add_shape(prim=inside, shape=_rect(
                    gate_left, gate_bottom, gate_right, gate_top, enclosure=enc,
                ))

        for i, impl in enumerate(prim.implant):
            enc = gate_encs[i]
            layout.add_shape(prim=impl, shape=_rect(
                gate_left, gate_bottom, gate_right, gate_top, enclosure=enc,
            ))

        return layout


class _CircuitLayouter:
    def __init__(self, *,
        fab: "LayoutFactory", circuit: ckt._Circuit, boundary: Optional[geo._Rectangular]
    ):
        self.fab = fab
        self.circuit = circuit

        self.layout = l = fab.new_layout()
        l.boundary = boundary

    @property
    def tech(self):
        return self.circuit.fab.tech

    def inst_layout(self, inst, *, layoutname=None, rotation="no"):
        if not isinstance(inst, ckt._Instance):
            raise TypeError("inst has to be of type '_Instance'")
        if not isinstance(rotation, str):
            raise TypeError(
                f"rotation has to be a string, not of type {type(rotation)}",
            )
        if rotation not in _rotations:
            ValueError(
                f"rotation '{rotation}' is not one of {_rotations}"
            )

        if isinstance(inst, ckt._PrimitiveInstance):
            def _portnets():
                for net in self.circuit.nets:
                    for port in net.childports:
                        if (inst == port.inst):
                            yield (port.name, net)
            portnets = dict(_portnets())
            portnames = set(inst.ports.keys())
            portnetnames = set(portnets.keys())
            if not (portnames == portnetnames):
                raise ValueError(
                    f"Unconnected port(s) {portnames - portnetnames}"
                    f" for inst '{inst.name}' of primitive '{inst.prim.name}'"
                )
            l = self.fab.new_primitivelayout(
                prim=inst.prim, portnets=portnets,
                **inst.params,
            )
            if rotation != "no":
                l.move(dx=0.0, dy=0.0, rotation=rotation)
            return l
        elif isinstance(inst, ckt._CellInstance):
            # TODO: propoer checking of nets for instance
            layout = None
            if layoutname is None:
                try:
                    circuitname = cast(Any, inst).circuitname
                    layout = inst.cell.layouts[circuitname]
                except:
                    layout = inst.cell.layout
                else:
                    layoutname = circuitname
            else:
                if not isinstance(layoutname, str):
                    raise TypeError(
                        "layoutname has to be 'None' or a string, not of type"
                        f" '{type(layoutname)}'"
                    )
                layout = inst.cell.layouts[layoutname]

            l = _Layout(
                self.fab,
                SubLayouts(_InstanceSubLayout(
                    inst, x=0.0, y=0.0, layoutname=layoutname, rotation=rotation,
                )),
            )
            l.boundary = layout.boundary

            return l
        else:
            raise AssertionError("Internal error")

    def wire_layout(self, *, net, wire, **wire_params):
        if net not in self.circuit.nets:
            raise ValueError(
                f"net '{net.name}' is not a net of circuit '{self.circuit.name}'"
            )
        if not (
            hasattr(wire, "ports")
            and (len(wire.ports) == 1)
            and (wire.ports[0].name == "conn")
        ):
            raise TypeError(
                f"Wire '{wire.name}' does not have exactly one port named 'conn'"
            )

        return self.fab.new_primitivelayout(
            wire, portnets={"conn": net}, **wire_params,
        )

    def place(self, object_, *,
        x: IntFloat, y: IntFloat, layoutname: Optional[str]=None, rotation: str="no",
    ) -> _Layout:
        if not isinstance(object_, (ckt._Instance, _Layout)):
            raise TypeError("inst has to be of type '_Instance' or '_Layout'")
        if not isinstance(rotation, str):
            raise TypeError(
                f"rotation has to be a string, not of type {type(rotation)}",
            )
        if rotation not in _rotations:
            raise ValueError(
                f"rotation '{rotation}' is not one of {_rotations}"
            )

        if isinstance(object_, ckt._Instance):
            inst = object_
            if inst not in self.circuit.instances:
                raise ValueError(
                    f"inst '{inst.name}' is not part of circuit '{self.circuit.name}'"
                )
            x = _util.i2f(x)
            y = _util.i2f(y)
            if not all((isinstance(x, float), isinstance(y, float))):
                raise TypeError("x and y have to be floats")

            if isinstance(inst, ckt._PrimitiveInstance):
                def _portnets():
                    for net in self.circuit.nets:
                        for port in net.childports:
                            if (inst == port.inst):
                                yield (port.name, net)
                portnets = dict(_portnets())
                portnames = set(inst.ports.keys())
                portnetnames = set(portnets.keys())
                if not (portnames == portnetnames):
                    raise ValueError(
                        f"Unconnected port(s) {portnames - portnetnames}"
                        f" for inst '{inst.name}' of primitive '{inst.prim.name}'"
                    )
                return self.layout.add_primitive(
                    prim=inst.prim, x=x, y=y, rotation=rotation, portnets=portnets,
                    **inst.params,
                )
            elif isinstance(inst, ckt._CellInstance):
                # TODO: propoer checking of nets for instance
                if (
                    (layoutname is None)
                    and inst.circuitname is not None
                    and (inst.circuitname in inst.cell.layouts.keys())
                ):
                    layoutname = inst.circuitname
                sl = _InstanceSubLayout(
                    inst, x=x, y=y, layoutname=layoutname, rotation=rotation,
                )
                self.layout += sl

                l = _Layout(self.fab, SubLayouts(sl))
                l.boundary = sl.boundary

                return l
            else:
                raise RuntimeError("Internal error: unsupported instance type")
        elif isinstance(object_, _Layout):
            if layoutname is not None:
                raise TypeError(
                    f"{self.__class__.__name__}.place() got unexpected keyword argument"
                    " 'layoutname'"
                )
            layout = object_.moved(x, y, rotation=rotation)
            self.layout += layout
            return layout
        else:
            raise AssertionError("Internal error")

    def add_shape(self, *,
        prim: prm._DesignMaskPrimitive, net: Optional[net_.Net], shape: geo._Shape,
    ):
        """Add a geometry shape to a _Layout

        This is lower level tool. One is adviced to use higher level add_...() methods
        if possible.
        """
        if (net is not None) and (net not in self.circuit.nets):
            raise ValueError(
                f"net '{net.name}' is not a net of circuit '{self.circuit.name}'"
            )

        self.layout.add_shape(prim=prim, net=net, shape=shape)

    def add_wire(self, *, net, wire, **wire_params) -> _Layout:
        if net not in self.circuit.nets:
            raise ValueError(
                f"net '{net.name}' is not a net of circuit '{self.circuit.name}'"
            )
        return self.layout.add_wire(
            net=net, wire=wire, **wire_params,
        )

    def add_portless(self, *,
        prim: prm._DesignMaskPrimitive, shape: Optional[geo._Shape]=None, **prim_params,
    ):
        if len(prim.ports) > 0:
            raise ValueError(
                f"prim '{prim.name}' should not have any port"
            )

        if shape is None:
            return self.layout.add_primitive(prim=prim, **prim_params)
        else:
            if len(prim_params) != 0:
                raise ValueError(
                    f"Parameters '{tuple(prim_params.keys())}' not supported for shape not 'None'",
                )
            self.add_shape(prim=prim, net=None, shape=shape)

    def connect(self, *, masks=None):
        for polygon in self.layout.polygons:
            if (masks is not None) and (polygon.mask not in masks):
                continue
            if polygon.mask.fill_space != "no":
                polygon.connect()


class LayoutFactory:
    def __init__(self, tech):
        if not isinstance(tech, tch.Technology):
            raise TypeError("tech has to be of type Technology")
        self.tech = tech
        self.gen_primlayout = _PrimitiveLayouter(self)

    def new_layout(self, *,
        sublayouts: Optional[Union[_SubLayout, SubLayouts]]=None,
        cls: Type[_Layout]=_Layout
    ):
        if sublayouts is None:
            sublayouts = SubLayouts()
        if isinstance(sublayouts, _SubLayout):
            sublayouts = SubLayouts(sublayouts)

        return _Layout(self, sublayouts)
        return cls(self, sublayouts)

    def new_primitivelayout(self, prim, **prim_params) -> _Layout:
        prim_params = prim.cast_params(prim_params)
        return self.gen_primlayout(prim, **prim_params)

    def new_circuitlayouter(self, *,
        circuit:ckt._Circuit, boundary: Optional[geo._Rectangular],
    ) -> _CircuitLayouter:
        return _CircuitLayouter(fab=self, circuit=circuit, boundary=boundary)

    def spec4bound(self, *, bound_spec, via=None):
        spec_out = {}
        if via is None:
            if isinstance(bound_spec, dict):
                specs = ("left", "bottom", "right", "top")
                if not all(spec in specs for spec in bound_spec.keys()):
                    raise ValueError(f"Bound spec for non-Via are {specs}")

                if "left" in bound_spec:
                    if "right" not in bound_spec:
                        raise ValueError(
                            "expecting both 'left' and 'right' spec or none of them"
                        )
                    left = bound_spec["left"]
                    right = bound_spec["right"]
                    spec_out.update({"x": (left + right)/2.0, "width": right - left})
                elif "right" in bound_spec:
                    raise ValueError(
                        "expecting both 'left' and 'right' or none of them"
                    )

                if "bottom" in bound_spec:
                    if "top" not in bound_spec:
                        raise ValueError(
                            "expecting both 'bottom' and 'top' spec or none of them"
                        )
                    bottom = bound_spec["bottom"]
                    top = bound_spec["top"]
                    spec_out.update({"y": (bottom + top)/2.0, "height": top - bottom})
                elif "top" in bound_spec:
                    raise ValueError(
                        "expecting both 'bottom' and 'top' spec or none of them"
                    )
            else:
                if not isinstance(bound_spec, geo.Rect):
                    bound_spec = geo.Rect.from_floats(
                        values=cast(
                            Tuple[float, float, float, float],
                            tuple(bound_spec),
                        ),
                    )
                spec_out.update({
                    "x": (bound_spec.left + bound_spec.right)/2.0,
                    "y": (bound_spec.bottom + bound_spec.top)/2.0,
                    "width": bound_spec.right - bound_spec.left,
                    "height": bound_spec.top - bound_spec.bottom,
                })
        else:
            if not isinstance(via, prm.Via):
                raise TypeError("via has to be 'None' or of type 'Via'")
            specs = (
                "space",
                "bottom_layer", "bottom_enclosure",
                "top_layer", "top_enclosure",
                "bottom_left", "bottom_bottom", "bottom_right", "bottom_top",
                "top_left", "top_bottom", "top_right", "top_top",
            )
            if not all(spec in specs for spec in bound_spec.keys()):
                raise ValueError(f"Bound specs for a Via are:\n  {specs}")

            try:
                space = bound_spec["space"]
            except KeyError:
                space = via.min_space
            else:
                spec_out["space"] = space

            try:
                bottom_layer = bound_spec["bottom_layer"]
            except KeyError:
                bottom_layer = via.bottom[0]
                idx = 0
            else:
                idx = via.bottom.index(bottom_layer)
            try:
                bottom_enc = bound_spec["bottom_enclosure"]
            except KeyError:
                bottom_enc = via.min_bottom_enclosure[idx]
            else:
                spec_out["bottom_enclosure"] = bottom_enc
            bottom_enc = bottom_enc.spec
            if isinstance(bottom_enc, float):
                bottom_enc = (bottom_enc, bottom_enc)

            try:
                top_layer = bound_spec["top_layer"]
            except KeyError:
                top_layer = via.top[0] if len(via.top) == 1 else None
                idx = 0
            else:
                idx = via.top.index(top_layer)
            try:
                top_enc = bound_spec["top_enclosure"]
            except KeyError:
                top_enc = via.min_top_enclosure[idx]
            else:
                spec_out["top_enclosure"] = top_enc

            top_enc = top_enc.spec
            if isinstance(top_enc, float):
                top_enc = (top_enc, top_enc)

            via_left = via_bottom = via_right = via_top = None
            if "bottom_left" in bound_spec:
                if "top_left" in bound_spec:
                    via_left = max((
                        bound_spec["bottom_left"] + bottom_enc[0],
                        bound_spec["top_left"] + top_enc[0],
                    ))
                else:
                    via_left = bound_spec["bottom_left"] + bottom_enc[0]
            elif "top_left" in bound_spec:
                via_left = bound_spec["top_left"] + top_enc[0]

            if "bottom_bottom" in bound_spec:
                if "top_bottom" in bound_spec:
                    via_bottom = max((
                        bound_spec["bottom_bottom"] + bottom_enc[1],
                        bound_spec["top_bottom"] + top_enc[1],
                    ))
                else:
                    via_bottom = bound_spec["bottom_bottom"] + bottom_enc[1]
            elif "top_bottom" in bound_spec:
                via_bottom = bound_spec["top_bottom"] + top_enc[1]

            if "bottom_right" in bound_spec:
                if "top_right" in bound_spec:
                    via_right = min((
                        bound_spec["bottom_right"] - bottom_enc[0],
                        bound_spec["top_right"] - top_enc[0],
                    ))
                else:
                    via_right = bound_spec["bottom_right"] - bottom_enc[0]
            elif "top_right" in bound_spec:
                via_right = bound_spec["top_right"] - top_enc[0]

            if "bottom_top" in bound_spec:
                if "top_top" in bound_spec:
                    via_top = min((
                        bound_spec["bottom_top"] - bottom_enc[1],
                        bound_spec["top_top"] - top_enc[1],
                    ))
                else:
                    via_top = bound_spec["bottom_top"] - bottom_enc[1]
            elif "top_top" in bound_spec:
                via_top = bound_spec["top_top"] - top_enc[1]

            if (via_left is not None) and (via_right is not None):
                width = via_right - via_left
                columns = int((width - via.width)/(via.width + space)) + 1
                if columns < 1:
                    raise ValueError("Not enough width for fitting one column")
                spec_out.update({
                    "x": self.tech.on_grid((via_left + via_right)/2.0),
                    "columns": columns,
                })
            elif (via_left is not None) or (via_right is not None):
                raise ValueError("left/right spec mismatch")

            if (via_bottom is not None) and (via_top is not None):
                height = via_top - via_bottom
                rows = int((height - via.width)/(via.width + space)) + 1
                if rows < 1:
                    raise ValueError("Not enough height for fitting one row")
                spec_out.update({
                    "y": self.tech.on_grid((via_bottom + via_top)/2.0),
                    "rows": rows,
                })
            elif (via_bottom is not None) or (via_top is not None):
                raise ValueError("bottom/top spec mismatch")

        if not spec_out:
            raise ValueError("No specs found")

        return spec_out


class Plotter:
    def __init__(self, plot_specs={}):
        self.plot_specs = dict(plot_specs)

    def plot(self, obj):
        if _util.is_iterable(obj):
            for item in obj:
                self.plot(item)
        elif isinstance(obj, (_Layout, _SubLayout)):
            for item in obj.polygons:
                self.plot(item)
        elif isinstance(obj, MaskPolygon):
            ax = plt.gca()
            draw_args = self.plot_specs.get(obj.mask.name, {})
            patch = descartes.PolygonPatch(obj.polygon, **draw_args)
            ax.add_patch(patch)
        else:
            raise NotImplementedError(f"plotting obj of type '{obj.__class__.__name__}'")
