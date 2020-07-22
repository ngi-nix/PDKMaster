"""The native technology primitives"""

from . import property_ as prop, mask

__all__ = ["Interconnect", "MOSFET", "Primitives"]

class _Primitive:
    def __init__(self, name):
        if not isinstance(name, str):
            raise RuntimeError("Internal Error: name is not a string")
        
        self.name = name

class _PrimitiveProperty(prop.Property):
    def __init__(self, name, primitive, *, type_=float):
        super().__init__(name, type_=type_)
        if not isinstance(primitive, _Primitive):
            raise RuntimeError("Internal error: primitive not of type 'Primitive'")

class Interconnect(_Primitive):
    def __init__(self, lay, *, name=None):
        if not isinstance(lay, mask.Mask):
            raise TypeError("mask is not of type 'Mask'")
        if name is None:
            name = lay.name + "_interconnect"
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        super().__init__(name)

        self.mask = lay

class MOSFET(_Primitive):
    def __init__(
        self, name, *,
        poly, active, implant, well=None,
        model=None,
    ):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        super().__init__(name)
        if not isinstance(poly, mask.Mask):
            raise TypeError("poly has to of type 'Mask'")
        if not isinstance(active, mask.Mask):
            raise TypeError("active has to of type 'Mask'")
        ok = True
        try:
            for l in implant:
                if not isinstance(l, mask.Mask):
                    ok = False
                    break
        except:
            ok = isinstance(implant, mask.Mask)
        if not ok:
            raise TypeError("implant has to be of type 'Mask' or an iterable of type 'Mask'")
        if well is not None:
            ok = True
            try:
                for l in well:
                    if not isinstance(l, mask.Mask):
                        ok = False
                        break
            except:
                ok = isinstance(well, mask.Mask)
            if not ok:
                raise TypeError("well has to be of type 'Mask' or an iterable of type 'Mask'")
        if model is None:
            model = name
    
        self.poly = poly
        self.active = active
        self.implant = implant
        self.well = well
        self.gate = mask.Mask(name + ".gate")
        self.model = model

        self.l = prop.Property(name + ".l")
        self.w = prop.Property(name + ".w")

class Primitives:
    def __init__(self):
        self._primitives = {}

    def __getitem__(self, key):
        return self._primitives[key]

    def __getattr__(self, name):
        try:
            return self._primitives[name]
        except KeyError:
            raise AttributeError("Primitive '{}' not present".format(name))

    def __iadd__(self, other):
        e = TypeError("Can only add 'Primitive' object or an iterable of 'Primitive' objects to 'Primitives'")
        try:
            iter(other)
        except TypeError:
            prims = (other,)
        else:
            prims = tuple(other)
        for prim in prims:
            if not isinstance(prim, _Primitive):
                raise e
            if prim.name in self._primitives:
                raise ValueError("Primitive '{}' already exists".format(prim.name))

        self._primitives.update({prim.name: prim for prim in prims})

        return self

    def __iter__(self):
        return iter(self._primitives.values())
