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
        if not isinstance(polygon, self._geometry_types):
            raise TypeError(
                f"can olny add object of type {self._geometry_types_str}"
            )
        self.polygon = self.polygon.union(polygon)

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
            raise ValueError("Can't add layout to a frozen layout")
        if isinstance(other, MaskPolygons):
            self.update(other)
        else:
            super().__iadd__(other)

        return self

    def update(self, polygons):
        if not isinstance(polygons, MaskPolygons):
            raise TypeError(
                "Can only add update object of type 'MaskPolygons'\n"
                "with object of type 'MaskPolygons'"
            )
        new = []
        for polygon in polygons:
            try:
                p2 = self[polygon.mask]
            except:
                new.append(polygon)
            else:
                p2 += polygon.polygon
        self += new

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
