import abc, logging
from itertools import product
from matplotlib import pyplot as plt
import descartes
from shapely import geometry as sh_geo, ops as sh_ops

from .. import _util
from ..technology import (
    property_ as prp, net as net_, mask as msk, primitive as prm,
    technology_ as tch, dispatcher as dsp
)
from . import circuit as ckt

__all__ = [
    "MaskPolygon", "MaskPolygons",
    "NetSubLayout", "MultiNetSubLayout", "NetlessSubLayout", "SubLayouts",
    "Layout", "LayoutFactory", "Plotter",
]

class NetOverlapError(Exception):
    pass

def _rect(left, bottom, right, top, *, enclosure=None):
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

    return sh_geo.Polygon((
        (left, bottom), (right, bottom), (right, top), (left, top),
    ))

def _via_array(left, bottom, width, pitch, rows, columns):
    def subrect(rc):
        row = rc[0]
        column = rc[1]
        left2 = left + column*pitch
        bottom2 = bottom + row*pitch
        right2 = left2 + width
        top2 = bottom2 + width

        return sh_geo.Polygon((
            (left2, bottom2), (right2, bottom2), (right2, top2), (left2, top2),
        ))

    return sh_geo.MultiPolygon(tuple(
        map(subrect, product(range(rows), range(columns)))
    ))

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

        if not isinstance(polygon, self._geometry_types):
            raise TypeError(
                f"polygon has to be of type {self._geometry_types_str}"
            )
        self.polygon = polygon

    def dup(self):
        return MaskPolygon(self.mask, self.polygon)

    @property
    def bounds(self):
        return self.polygon.bounds

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
            raise TypeError("other has to be of type 'MaskPolygon'")
        return (
            (self.mask == other.mask)
            and self.polygon.intersects(other.polygon)
        )

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

class MaskPolygons(_util.TypedTuple):
    tt_index_attribute = "mask"
    tt_index_type = msk.DesignMask
    tt_element_type = MaskPolygon

    def dup(self):
        return MaskPolygons(mp.dup() for mp in self)

    def mps_bounds(self, *, mask=None):
        mps = self if mask is None else filter(
            lambda mp: mp.mask == mask, self,
        )
        boundslist = tuple(mp.bounds for mp in mps)
        return [
            min(bds[0] for bds in boundslist),
            min(bds[1] for bds in boundslist),
            max(bds[2] for bds in boundslist),
            max(bds[3] for bds in boundslist),
        ]

    def __getattr__(self, name):
        if isinstance(name, str):
            for elem in self._t:
                if elem.mask.name == name:
                    return elem
        return super().__getattr__(name)

    def __iadd__(self, other):
        if self._frozen:
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
        if self._frozen:
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
    def overlaps_with(self, sublayout):
        if not isinstance(sublayout, _SubLayout):
            raise TypeError("sublayout has to be of type '_SubLayout'")
        return False

    @abc.abstractmethod
    def dup(self):
        raise AssertionError("Internal error")

class NetSubLayout(_SubLayout):
    def __init__(self, net, polygons):
        if not isinstance(net, net_.Net):
            raise TypeError("net has to be of type '_Net'")
        self.net = net

        if isinstance(polygons, MaskPolygon):
            polygons = MaskPolygons(polygons)
        if not isinstance(polygons, MaskPolygons):
            raise TypeError("polygons has to be of type 'MaskPolygon' or 'MaskPolygons'")
        super().__init__(polygons)

    def dup(self):
        return NetSubLayout(self.net, self.polygons.dup())

    def __iadd__(self, other):
        assert (
            isinstance(other, NetSubLayout)
            and (self.net == other.net)
        ), "Internal error"
        self.polygons += other.polygons

        return self

    def overlaps_with(self, other):
        super().overlaps_with(other)

        if isinstance(other, MultiNetSubLayout):
            return other.overlaps_with(self)

        assert isinstance(other, (NetSubLayout, NetlessSubLayout)), "Internal error"

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
                        net = other.net
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

class NetlessSubLayout(_SubLayout):
    def __init__(self, polygons):
        if isinstance(polygons, MaskPolygon):
            polygons = MaskPolygons(polygons)
        if not isinstance(polygons, MaskPolygons):
            raise TypeError("polygons has to be of type 'MaskPolygon' or 'MaskPolygons'")
        super().__init__(polygons)

    def dup(self):
        return NetlessSubLayout(self.polygons.dup())

    def __iadd__(self, other):
        assert isinstance(other, NetlessSubLayout), "Internal error"
        self.polygons += other.polygons

        return self

    def overlaps_with(self, other):
        super().overlaps_with(other)

        if isinstance(other, (NetSubLayout, MultiNetSubLayout)):
            return other.overlaps_with(self)

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

class MultiNetSubLayout(_SubLayout):
    def __init__(self, sublayouts):
        if not _util.is_iterable(sublayouts):
            raise TypeError(
                "sublayouts has to be an iterable of 'NetSubLayout' and "
                "'NetlessSubLayout'"
            )
        sublayouts = tuple(sublayouts)
        if not all((
            isinstance(netlayout, (NetSubLayout, NetlessSubLayout))
            for netlayout in sublayouts
        )):
            raise TypeError(
                "sublayouts has to be an iterable of 'NetSubLayout' and "
                "'NetlessSubLayout'"
            )
        self.sublayouts = sublayouts

        super().__init__(MaskPolygons())
        self._update_maskpolygon()

    def dup(self):
        return MultiNetSubLayout(sl.dup() for sl in self.sublayouts)

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
                    if self_sublayout.overlaps_with(other):
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
                    if other_sublayout.overlaps_with(self_sublayout):
                        self_sublayout += other_sublayout
                        break
                else:
                    self.sublayouts += other_sublayout
            self._update_maskpolygon()

        return self

    def merge_from(self, other):
        """Extract overlapping polygon from other and add it to itself

        return wether other is now empty"""
        if not self.overlaps_with(other):
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
                other.polygons.tt_pop(self_polygon.mask)
            elif isinstance(other_polygon.polygon, sh_geo.MultiPolygon):
                # Take only parts of other polygon that overlap with out polygon
                for p2 in filter(
                    lambda p: self_polygon.polygon.intersects(p),
                    other_polygon.polygon,
                ):
                    add_polygon(self, MaskPolygon(other_polygon.mask, p2))
                    other_polygon.polygon = other_polygon.polygon.difference(p2)
                if not other_polygon.polygon:
                    other.polygons.tt_pop(self_polygon.mask)
            else:
                raise AssertionError("Internal error")

            return not other.polygons

    def overlaps_with(self, other):
        super().overlaps_with(other)

        assert len(self.polygons) == 1, "Internal error"
        self_polygon = self.polygons[0]

        for other_polygon in filter(
            lambda p: p.mask == self_polygon.mask,
            other.polygons,
        ):
            if self_polygon.overlaps_with(other_polygon):
                # Recursively call overlaps_with to check for wrong net overlaps.
                for sublayout in self.sublayouts:
                    if other.overlaps_with(sublayout):
                        return True
                else:
                    # This should not happen: joined polygon overlaps but none of
                    # the sublayout overlaps.
                    raise AssertionError("Internal error")
        else:
            return False

class SubLayouts(_util.TypedTuple):
    tt_element_type = _SubLayout
    tt_index_attribute = None

    def dup(self):
        return SubLayouts(l.dup() for l in self)

    def __iadd__(self, other):
        other = tuple(other) if _util.is_iterable(other) else (other,)
        if not all(isinstance(sublayout, _SubLayout) for sublayout in other):
            raise TypeError(
                "Can only add '_SubLayout' object or iterable of '_SubLayout' objects\n"
                "to an 'SubLayouts' object"
            )

        # First try to add the sublayout to the multinet polygons
        multinets = tuple(self.tt_iter_type(MultiNetSubLayout))
        def add2multinet(other_sublayout):
            for multinet in multinets:
                if multinet.overlaps_with(other_sublayout):
                    return multinet.merge_from(other_sublayout)
            else:
                return False
        other = filter(lambda sl: not add2multinet(sl), other)

        # Now try to add to other sublayouts
        def add2other(other_sublayout):
            if isinstance(other_sublayout, MultiNetSubLayout):
                for sublayout in self:
                    if sublayout.overlaps_with(other_sublayout):
                        if other_sublayout.merge_from(sublayout):
                            self.tt_remove(sublayout)
                return False
            else:
                # Can only add to same type
                for sublayout in self.tt_iter_type(other_sublayout.__class__):
                    if (
                        # Add all netless together
                        isinstance(other_sublayout, NetlessSubLayout)
                        # or polygons on same net
                        or (sublayout.net == other_sublayout.net)
                    ):
                        sublayout += other_sublayout
                        return True
                else:
                    return False
        other = tuple(filter(lambda sl: not add2other(sl), other))

        if other:
            # Append remaining sublayouts
            return super().__iadd__(other)
        else:
            return self

class Layout:
    def __init__(self, sublayouts=None):
        if sublayouts is None:
            sublayouts = SubLayouts()
        if isinstance(sublayouts, _SubLayout):
            sublayouts = SubLayouts(sublayouts)
        if not isinstance(sublayouts, SubLayouts):
            raise TypeError(
                "sublayouts has to be of type '_SubLayout' or 'SubLayouts'"
            )
        self.sublayouts = sublayouts

    @property
    def polygons(self):
        for sublayout in self.sublayouts:
            for polygon in sublayout.polygons:
                yield polygon

    def dup(self):
        return Layout(SubLayouts(sl.dup() for sl in self.sublayouts))

    def bounds(self, *, mask=None):
        mps = self.polygons if mask is None else filter(
            lambda mp: mp.mask == mask, self.polygons,
        )
        boundslist = tuple(mp.bounds for mp in mps)
        return [
            min(bds[0] for bds in boundslist),
            min(bds[1] for bds in boundslist),
            max(bds[2] for bds in boundslist),
            max(bds[3] for bds in boundslist),
        ]

    def __iadd__(self, other):
        if self.sublayouts._frozen:
            raise ValueError("Can't add sublayouts to a frozen 'Layout' object")
        if not isinstance(other, (_SubLayout, SubLayouts)):
            raise TypeError(
                "Can only add '_SubLayout' or 'SubLayouts' object to a "
                "'Layout' object"
            )

        self.sublayouts += other

        return self

    def freeze(self):
        self.sublayouts.tt_freeze()

class _PrimitiveLayouter(dsp.PrimitiveDispatcher):
    def __init__(self, fab):
        assert isinstance(fab, LayoutFactory), "Internal error"
        self.fab = fab

    @property
    def tech(self):
        return self.fab.tech

    # Dispatcher implementation
    def _Primitive(self, prim, **params):
        raise NotImplementedError(
            f"Don't know how to generate minimal layout for primitive '{prim.name}'\n"
            f"of type '{prim.__class__.__name__}'"
        )

    def _WidthSpacePrimitive(self, prim, *, center, **widthspace_params):
        if not isinstance(center, sh_geo.Point):
            raise TypeError("center has to be of type Point from shapely")

        centerx, centery = tuple(center.coords)[0]

        width = widthspace_params["width"]
        height = widthspace_params["height"]

        left = centerx - 0.5*width
        right = left + width
        bottom = centery - 0.5*height
        top = bottom + height

        return Layout(
            NetSubLayout(
                prim.ports[0], MaskPolygon(
                    prim.mask, _rect(left, bottom, right, top),
                ),
            ),
        )

    def WaferWire(self, prim, *, center, **waferwire_params):
        implant = waferwire_params.pop("implant")
        implant_enclosure = waferwire_params.pop("implant_enclosure")
        assert implant_enclosure is not None

        well = waferwire_params.pop("well", None)
        well_enclosure = waferwire_params.pop("well_enclosure", None)


        centerx, centery = tuple(center.coords)[0]

        width = waferwire_params["width"]
        height = waferwire_params["height"]

        left = centerx - 0.5*width
        right = left + width
        bottom = centery - 0.5*height
        top = bottom + height

        layout = self._WidthSpacePrimitive(prim, center=center, **waferwire_params)

        layout += NetlessSubLayout(MaskPolygon(
                implant.mask,
                _rect(left, bottom, right, top, enclosure=implant_enclosure),
        ))
        if well is not None:
            net = (
                prim.ports[0] if (implant.type_ == well.type_)
                else prm._PrimitiveNet(prim, "well")
            )
            layout += NetSubLayout(
                net, MaskPolygon(
                    well.mask,
                    _rect(left, bottom, right, top, enclosure=well_enclosure),
                ),
            )

        return layout

    def Via(self, prim, *, center, **via_params):
        if not isinstance(center, sh_geo.Point):
            raise TypeError("center has to be of type Point from shapely")

        centerx, centery = tuple(center.coords)[0]

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

        bottom_left = centerx - 0.5*bottom_width
        bottom_bottom = centery - 0.5*bottom_height
        bottom_right = bottom_left + bottom_width
        bottom_top = bottom_bottom + bottom_height

        top_left = centerx - 0.5*top_width
        top_bottom = centery - 0.5*top_height
        top_right = top_left + top_width
        top_top = top_bottom + top_height

        via_bottom = centery - 0.5*via_height
        via_left = centerx - 0.5*via_width

        assert len(prim.ports) == 1, "Internal error"
        layout = Layout(
            NetSubLayout(
                prim.ports[0], MaskPolygons((
                    MaskPolygon(
                        bottom.mask,
                        _rect(bottom_left, bottom_bottom, bottom_right, bottom_top),
                    ),
                    MaskPolygon(
                        prim.mask,
                        _via_array(via_left, via_bottom, width, pitch, rows, columns),
                    ),
                    MaskPolygon(
                        top.mask,
                        _rect(top_left, top_bottom, top_right, top_top),
                    ),
                )),
            ),
        )
        try:
            impl = via_params["bottom_implant"]
        except KeyError:
            pass
        else:
            if impl is not None:
                enc = via_params["bottom_implant_enclosure"]
                assert enc is not None, "Internal error"
                layout += NetlessSubLayout(
                    MaskPolygon(
                        impl.mask, _rect(
                            bottom_left, bottom_bottom, bottom_right, bottom_top,
                            enclosure=enc,
                        ),
                    ),
                )
        try:
            well = via_params["bottom_well"]
        except KeyError:
            pass
        else:
            if well is not None:
                enc = via_params["bottom_well_enclosure"]
                assert enc is not None, "Internal error"
                net = (
                    prim.ports[0] if (impl.type_ == well.type_)
                    else prm._PrimitiveNet(prim, "well")
                )
                layout += NetSubLayout(
                    net, MaskPolygon(
                        well.mask, _rect(
                            bottom_left, bottom_bottom, bottom_right, bottom_top,
                            enclosure=enc,
                        ),
                    )
                )

        return layout

    def MOSFET(self, prim, *, center, **mos_params):
        if not isinstance(center, sh_geo.Point):
            raise TypeError("center has to be of type Point from shapely")

        centerx, centery = tuple(center.coords)[0]

        l = mos_params["l"]
        w = mos_params["w"]
        impl_enc = mos_params["activeimplant_enclosure"]
        gate_encs = mos_params["gateimplant_enclosures"]

        gate_left = centerx - 0.5*l
        gate_right = centerx + 0.5*l
        gate_top = centery + 0.5*w
        gate_bottom = centery - 0.5*w

        layout = Layout()

        active = prim.gate.active
        sdw = prim.computed.min_sd_width
        active_left = gate_left - sdw
        active_bottom = gate_bottom
        active_right = gate_right + sdw
        active_top = gate_top
        layout += MultiNetSubLayout((
            NetSubLayout(
                prim.ports.sourcedrain1,
                MaskPolygon(
                    active.mask,
                    _rect(active_left, active_bottom, gate_left, active_top),
                ),
            ),
            NetlessSubLayout(
                MaskPolygon(
                    active.mask,
                    _rect(gate_left, active_bottom, gate_right, active_top),
                ),
            ),
            NetSubLayout(
                prim.ports.sourcedrain2,
                MaskPolygon(
                    active.mask,
                    _rect(gate_right, active_bottom, active_right, active_top),
                ),
            ),
        ))
        for impl in prim.implant:
            if impl in active.implant:
                layout += NetlessSubLayout(MaskPolygon(
                    impl.mask, _rect(
                        active_left, active_bottom, active_right, active_top,
                        enclosure=impl_enc
                    ),
                ))

        poly = prim.gate.poly
        ext = prim.computed.min_polyactive_extension
        poly_left = gate_left
        poly_bottom = gate_bottom - ext
        poly_right = gate_right
        poly_top = gate_top + ext
        layout += NetSubLayout(
            prim.ports.gate,
            MaskPolygon(
                poly.mask,
                _rect(poly_left, poly_bottom, poly_right, poly_top),
            ),
        )

        if hasattr(prim, "well"):
            enc = active.min_well_enclosure[active.well.index(prim.well)]
            layout += NetSubLayout(
                prim.ports.bulk,
                MaskPolygon(
                    prim.well.mask,
                    _rect(active_left, active_bottom, active_right, active_top, enclosure=enc)
                ),
            )

        polygons = MaskPolygons()
        for i, impl in enumerate(prim.implant):
            enc = gate_encs[i]
            polygons += MaskPolygon(
                impl.mask,
                _rect(gate_left, gate_bottom, gate_right, gate_top, enclosure=enc)
            )
        layout += NetlessSubLayout(polygons)

        return layout

class _CircuitLayouter:
    def __init__(self, fab, circuit):
        assert isinstance(fab, LayoutFactory), "Internal error"
        self.fab = fab

        if not isinstance(circuit, ckt._Circuit):
            raise TypeError("circuit has to be of type '_Circuit'")
        self.circuit = circuit

        self.layout = Layout()

    @property
    def tech(self):
        return self.circuit.layoutfab.tech

    def place(self, inst, *, x, y):
        if not isinstance(inst, ckt._Instance):
            raise TypeError("inst has to be of type '_Instance'")
        if inst not in self.circuit.instances:
            raise ValueError(
                f"inst '{inst.name}' is not part of circuit '{self.circuit.name}'"
            )
        x = _util.i2f(x)
        y = _util.i2f(y)
        if not all((isinstance(x, float), isinstance(y, float))):
            raise TypeError("x and y have to be floats")

        instlayout = self.fab.new_primitivelayout(
            inst.prim, center=sh_geo.Point(x, y), **inst.params,
        )
        for sublayout in instlayout.sublayouts:
            if isinstance(sublayout, NetSubLayout):
                sublayout.net = ckt._InstanceNet(inst, sublayout.net)
            elif isinstance(sublayout, MultiNetSubLayout):
                for sublayout2 in sublayout.sublayouts:
                    if isinstance(sublayout2, NetSubLayout):
                        sublayout2.net = ckt._InstanceNet(inst, sublayout2.net)

        def _portnets():
            for net in self.circuit.nets:
                for port in net.childports:
                    yield (port, net)
        portnets = dict(_portnets())

        def connect_ports(sublayouts):
            for sublayout in sublayouts:
                if isinstance(sublayout, NetSubLayout):
                    try:
                        net = portnets[sublayout.net]
                    except KeyError:
                        net = ckt._InstanceNet(inst, sublayout.net)
                    sublayout.net = net
                elif isinstance(sublayout, MultiNetSubLayout):
                    connect_ports(sublayout.sublayouts)
                elif not isinstance(sublayout, NetlessSubLayout):
                    raise AssertionError("Internal error")

        connect_ports(instlayout.sublayouts)
        self.layout += instlayout.sublayouts

        return instlayout

    def add_wire(self, *, net, well_net=None, wire, x, y, **wire_params):
        if not isinstance(net, net_.Net):
            raise TypeError("net has to be of type 'Net'")
        if net not in self.circuit.nets:
            raise ValueError(
                f"net '{net.name}' is not a net from circuit '{self.circuit.name}'"
            )
        if not (
            hasattr(wire, "ports")
            and (len(wire.ports) == 1)
            and (wire.ports[0].name == "conn")
        ):
            raise TypeError("A wire has to have one port named 'conn'")

        wirelayout = self.fab.new_primitivelayout(
            wire, center=sh_geo.Point(x, y), **wire_params,
        )
        for sublayout in wirelayout.sublayouts:
            if isinstance(sublayout, NetSubLayout):
                if sublayout.net.name == "well":
                    if well_net is None:
                        raise TypeError(
                            "No well_net provided for WaferWire with a well"
                        )
                    sublayout.net = well_net
                else:
                    assert sublayout.net.name == "conn", "Internal error"
                    sublayout.net = net
            elif not isinstance(sublayout, NetlessSubLayout):
                raise AssertionError("Internal error")

        self.layout += wirelayout.sublayouts

        return wirelayout

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

    def new_primitivelayout(self, prim, *,
        center=sh_geo.Point(0.0, 0.0), **prim_params
    ):
        prim_params = prim.cast_params(prim_params)
        return self.gen_primlayout(prim, center=center, **prim_params)

    def new_circuitlayouter(self, circuit):
        return _CircuitLayouter(self, circuit)

    def spec4bound(self, *, bound_spec, via=None):
        spec_out = {}
        if via is None:
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
            if not isinstance(via, prm.Via):
                raise TypeError("via has to be 'None' or of type 'Via'")
            specs = (
                "bottom_layer", "bottom_enclosure",
                "top_layer", "top_enclosure",
                "bottom_left", "bottom_bottom", "bottom_right", "bottom_top",
                "top_left", "top_bottom", "top_right", "top_top",
            )
            if not all(spec in specs for spec in bound_spec.keys()):
                raise ValueError(f"Bound specs for a Via are:\n  {specs}")

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
                columns = int((width - via.width)/(via.width + via.min_space)) + 1
                if columns < 1:
                    raise ValueError("Not enough widht for fitting one column")
                spec_out.update({
                    "x": (via_left + via_right)/2.0,
                    "columns": columns,
                })
            elif (via_left is not None) or (via_right is not None):
                raise ValueError("left/right spec mismatch")

            if (via_bottom is not None) and (via_top is not None):
                height = via_top - via_bottom
                rows = int((height - via.width)/(via.width + via.min_space)) + 1
                if rows < 1:
                    raise ValueError("Not enough height for fitting one row")
                spec_out.update({
                    "y": (via_bottom + via_top)/2.0,
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
        elif isinstance(obj, (Layout, _SubLayout)):
            for item in obj.polygons:
                self.plot(item)
        elif isinstance(obj, MaskPolygon):
            ax = plt.gca()
            draw_args = self.plot_specs.get(obj.mask.name, {})
            patch = descartes.PolygonPatch(obj.polygon, **draw_args)
            ax.add_patch(patch)
        else:
            raise NotImplementedError(f"plotting obj of type '{obj.__class__.__name__}'")
