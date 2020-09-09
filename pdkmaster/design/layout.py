import abc
from matplotlib import pyplot as plt
import descartes
from shapely import geometry as sh_geo, ops as sh_ops

from .. import _util
from ..technology import (
    property_ as prp, net as net_, mask as msk, primitive as prm,
    technology_ as tch, dispatcher as dsp
)

__all__ = [
    "MaskPolygon", "MaskPolygons",
    "NetSubLayout", "MultiNetSubLayout", "NetlessSubLayout", "SubLayouts",
    "Layout", "PrimitiveLayoutFactory", "Plotter",
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
        self.polygon = _manhattan_polygon(
            self.polygon.simplify(1e-6).convex_hull, outer=False,
        )

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
                    raise NetOverlapError("Overlapping polygons on different nets")
        else:
            return False

class NetlessSubLayout(_SubLayout):
    def __init__(self, polygons):
        if isinstance(polygons, MaskPolygon):
            polygons = MaskPolygons(polygons)
        if not isinstance(polygons, MaskPolygons):
            raise TypeError("polygons has to be of type 'MaskPolygon' or 'MaskPolygons'")
        super().__init__(polygons)

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
                    add_polygon(self, p2)
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
                        logging.warning(
                            "Adding MultiNetSubLayout that overlaps with existing polygon "
                            "not implemented"
                        )
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

class PrimitiveLayoutFactory(dsp.PrimitiveDispatcher):
    def __init__(self, tech):
        if not isinstance(tech, tch.Technology):
            raise TypeError("tech has to be of type Technology")
        self.tech = tech

    def new_layout(self, prim, *, center=sh_geo.Point(0.0, 0.0), **prim_params):
        prim_params = prim.cast_params(prim_params)
        return self(prim, center=center, **prim_params)

    # Dispatcher implementation
    def _Primitive(self, prim, **params):
        raise NotImplementedError(
            f"Don't know how to generate minimal layout for primitive '{prim.name}'\n"
            f"of type '{prim.__class__.__name__}'"
        )

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
