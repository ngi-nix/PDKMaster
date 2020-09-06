import abc
from matplotlib import pyplot as plt
import descartes
from shapely import geometry as sh_geo, ops as sh_ops

from .. import _util
from ..technology import (
    net as net_, mask as msk, primitive as prm, technology_ as tch, dispatcher as dsp
)

__all__ = [
    "MaskPolygon", "MaskPolygons", "PrimitiveLayoutFactory",
    "Plotter",
]

def _rect(left, bottom, right, top, *, enclosure=None):
    if enclosure is not None:
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

    def grow(self, size):
        polygon = self.polygon.buffer(size, resolution=0)

        def manhattan_coords(coords):
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
                            coord = (next_coord[0], coord[1])
                        elif next_coord[1] == next2_coord[1]:
                            coord = (coord[0], next_coord[1])
                        else:
                            raise RuntimeError("two consecutive non-Manhattan points")
                    else:
                        if coord[0] == prev[0]:
                            coord = (coord[0], next_coord[1])
                        elif coord[1] == prev[1]:
                            coord = (next_coord[0], coord[1])
                        else:
                            raise RuntimeError(
                                "two consecutive non-Manhattan points:\n"
                                f"  {prev}, {coord}, {next_coord}"
                            )

                yield coord
                prev = coord

        def manhattan_polygon(polygon):
            return sh_geo.Polygon(
                shell=manhattan_coords(tuple(polygon.exterior.coords)),
                holes=tuple(
                    manhattan_coords(tuple(interior.coords))
                    for interior in polygon.interiors
                )
            )

        if _util.is_iterable(polygon):
            self.polygon = sh_ops.unary_union(
                tuple(manhattan_polygon(subpolygon) for subpolygon in polygon)
            )
        else:
            self.polygon = manhattan_polygon(polygon)

    def grown(self, size):
        polygon = MaskPolygon(self.mask, self.polygon)
        polygon.grow(size)
        return polygon

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

class PrimitiveLayoutFactory(dsp.PrimitiveDispatcher):
    def __init__(self, tech):
        if not isinstance(tech, tch.Technology):
            raise TypeError("tech has to be of type Technology")
        self.tech = tech

    def new_layout(self, prim, *, center=sh_geo.Point(0.0, 0.0), **prim_params):
        prim_params = prim.cast_params(prim_params)
        polygons = self(prim, center=center, **prim_params)
        return MaskPolygons(polygons)

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

        gate_left = centerx - 0.5*l
        gate_right = centerx + 0.5*l
        gate_top = centery + 0.5*w
        gate_bottom = centery - 0.5*w

        polygons = MaskPolygons()

        active = prim.gate.active
        sdw = prim.computed.min_sd_width
        active_left = gate_left - sdw
        active_bottom = gate_bottom
        active_right = gate_right + sdw
        active_top = gate_top
        polygons += MaskPolygon(
            active.mask,
            _rect(active_left, active_bottom, active_right, active_top),
        )

        poly = prim.gate.poly
        ext = prim.computed.min_polyactive_extension
        poly_left = gate_left
        poly_bottom = gate_bottom - ext
        poly_right = gate_right
        poly_top = gate_top + ext
        polygons += MaskPolygon(
            poly.mask,
            _rect(poly_left, poly_bottom, poly_right, poly_top),
        )

        if hasattr(prim, "well"):
            enc = active.min_well_enclosure[active.well.index(prim.well)]
            polygons += MaskPolygon(
                prim.well.mask,
                _rect(active_left, active_bottom, active_right, active_top, enclosure=enc)
            )

        for i, impl in enumerate(prim.implant):
            enc = prim.min_gateimplant_enclosure[i]
            polygons += MaskPolygon(
                impl.mask,
                _rect(gate_left, gate_bottom, gate_right, gate_top, enclosure=enc)
            )

        return polygons

class Plotter:
    def __init__(self, plot_specs={}):
        self.plot_specs = dict(plot_specs)

    def plot(self, obj):
        if isinstance(obj, MaskPolygon):
            ax = plt.gca()
            draw_args = self.plot_specs.get(obj.mask.name, {})
            patch = descartes.PolygonPatch(obj.polygon, **draw_args)
            ax.add_patch(patch)
        elif isinstance(obj, MaskPolygons):
            for polygon in obj:
                self.plot(polygon)
        else:
            raise NotImplementedError(f"plotting obj of type '{obj.__class__.__name__}'")
