"""The native technology primitives"""

from textwrap import dedent
from . import condition as cond, property_ as prop, mask as msk, _util

__all__ = ["Well", "Wire", "MOSFET"]

class _Primitive:
    def __init__(self, name):
        if not isinstance(name, str):
            raise TypeError("name argument of '{}' is not a string".format(self.__class__.__name__))
        
        self.name = name
        self._connects = set()

class _PrimitiveProperty(prop.Property):
    def __init__(self, primitive, name, *, type_=float):
        if not isinstance(primitive, _Primitive):
            raise RuntimeError("Internal error: primitive not of type 'Primitive'")
        super().__init__(primitive.name + "." + name, type_=type_)

class _DualPrimitiveProperty(prop.Property):
    def __init__(self, prim1, prim2, name, *, commutative):
        assert (
            isinstance(prim1, _Primitive) and isinstance(prim2, _Primitive)
            and isinstance(name, str) and isinstance(commutative, bool)
        ), "Internal error"

        name = "{}.{}.{}".format(prim1.name, prim2.name, name)
        if commutative:
            alias = "{}.{}.{}".format(prim2.name, prim1.name, name)
            super().__init__(name, alias)
        else:
            super().__init__(name)

        self.prim1 = prim1
        self.prim2 = prim2
        self.prop_name = name

class _PrimitiveMultiCondition(cond.Condition):
    def __init__(self, prim, others):
        assert (isinstance(prim, _Primitive) and len(others) != 0), "Internal error"
        super().__init__((prim, others))

        self.prim = prim
        self.others = others

    def __hash__(self):
        return hash((self.prim, self.others))

class _InsideCondition(_PrimitiveMultiCondition):
    pass
class _OutsideCondition(_PrimitiveMultiCondition):
    pass

class Marker(_Primitive):
    pass

class _WidthSpacePrimitive(_Primitive):
    def __init__(self, *,
        min_width, min_space, min_area=None, space_table=None,
        name,
    ):
        min_width = _util.i2f(min_width)
        min_space = _util.i2f(min_space)
        min_area = _util.i2f(min_area)

        if not (isinstance(min_width, float) and isinstance(min_space, float)):
            raise TypeError("min_width and min_space arguments for '{}' have to be floats".format(
                self.__class__.__name__,
            ))
        if not ((min_area is None) or isinstance(min_area, float)):
            raise TypeError("min_area argument for '{}' has to be 'None' or a float".format(
                self.__class__.__name__,
            ))
        if space_table is not None:
            try:
                space_table = tuple(space_table)
            except TypeError:
                raise TypeError("space_table has to 'None' or iterable of width-space specifications")
            for width_space_spec in space_table:
                try:
                    l = len(width_space_spec)
                except TypeError:
                    raise TypeError("width-space rows in space_table have to be iterable of length 2")
                else:
                    if l != 2:
                        raise TypeError("width-space rows in space_table have to be iterable of length 2")
                width = _util.i2f(width_space_spec[0])
                space = _util.i2f(width_space_spec[1])
                try:
                    iter(width)
                except TypeError:
                    if not isinstance(width, float):
                        raise TypeError("first element in a space_table row has to be a float or an iterable of two floats")
                else:
                    if not ((len(width) == 2) and all(isinstance(_util.i2f(w), float) for w in width)):
                        raise TypeError("first element in a space_table row has to be a float or an iterable of two floats")
                if not isinstance(space, float):
                    raise TypeError("second element in a space_table row has to be a float")

        super().__init__(name)
        self.min_width = min_width
        self.min_space = min_space
        self.min_area = min_area
        if space_table is None:
            space_table = ((min_width, min_space),)
        else:
            def conv_spacetable_row(row):
                width = _util.i2f(row[0])
                space = _util.i2f(row[1])
                try:
                    iter(width)
                except TypeError:
                    pass
                else:
                    width = tuple(_util.i2f(w) for w in width)
                return (width, space)

            space_table = tuple(conv_spacetable_row(row) for row in space_table)
        self.space_table = space_table

        self.width = _PrimitiveProperty(self, "width")
        self.space = _PrimitiveProperty(self, "space")
        self.area = _PrimitiveProperty(self, "area")

    def space_to(self, other):
        if not isinstance(other, _Primitive):
            raise TypeError("other has to be of type '_Primitive'")

        return _DualPrimitiveProperty(self, other, "space", commutative=True)

    def extend_over(self, other):
        if not isinstance(other, _Primitive):
            raise TypeError("other has to be of type '_Primitive'")

        return _DualPrimitiveProperty(self, other, "extend_over", commutative=False)

    def enclosed_by(self, other):
        if not isinstance(other, _Primitive):
            raise TypeError("other has to be of type '_Primitive'")

        return _DualPrimitiveProperty(self, other, "enclosed_by", commutative=False)

    def overlap_with(self, other):
        if not isinstance(other, _Primitive):
            raise TypeError("other has to be of type '_Primitive'")

        return _DualPrimitiveProperty(self, other, "overlap_with", commutative=True)

    def is_inside(self, other, *others):
        if isinstance(other, _Primitive):
            prims = (other, *others)
        else:
            try:
                prims = (*other, *others)
            except:
                raise TypeError("Outside mask not of type '_Primitive'")
        for l in prims:
            if not isinstance(l, _Primitive):
                raise TypeError("Outside mask not of type '_Primitive'")
        
        return _InsideCondition(self, prims)

    def is_outside(self, other, *others):
        if isinstance(other, _Primitive):
            prims = (other, *others)
        else:
            try:
                prims = (*other, *others)
            except:
                raise TypeError("Outside mask not of type '_Primitive'")
        for l in prims:
            if not isinstance(l, _Primitive):
                raise TypeError("Outside mask not of type '_Primitive'")
        
        return _OutsideCondition(self, prims)

class Implant(_WidthSpacePrimitive):
    def __init__(self, *, implant, **widthspace_args):
        if "name" not in widthspace_args:
            widthspace_args["name"] = implant.name
        if not isinstance(implant, msk.Mask):
            raise TypeError("implant param for '{}' has to be of type 'Mask'".format(
                self.__class__.__name__
            ))

        super().__init__(**widthspace_args)
        self.implant = implant

class Well(Implant):
    # Wells are non-overlapping by design
    def __init__(self, *, min_space_samenet=None, **implant_args):
        min_space_samenet = _util.i2f(min_space_samenet)
        if not ((min_space_samenet is None) or isinstance(min_space_samenet, float)):
            raise TypeError("min_space_samenet has to be 'None' or a float")
            
        super().__init__(**implant_args)
        self.min_space_samenet = self.min_space if min_space_samenet is None else min_space_samenet

class Substrate(_Primitive):
    # Wafer area not covered by wells
    def __init__(self):
        super().__init__("substrate")

class Deposition(_WidthSpacePrimitive):
    def __init__(self, mask, **widthspace_args):
        if not isinstance(mask, msk.Mask):
            raise TypeError("mask is not of type 'Mask'")
        if "name" not in widthspace_args:
            widthspace_args["name"] = mask.name

        super().__init__(**widthspace_args)
        self.mask = mask

class Wire(Deposition):
    def __init__(self, *, material,
        implant=None, marker=None, connects=None,
        **deposition_args,
    ):
        if not isinstance(material, (msk.Mask, Wire)):
            raise TypeError("material is not of type 'Mask' or 'Wire'")
        if isinstance(material, msk.Mask):
            if "name" not in deposition_args:
                deposition_args["name"] = material.name
        else: # Wire type
            deposition_args.update({
                "min_width": deposition_args.get("min_width", material.min_width),
                "min_space": deposition_args.get("min_space", material.min_space),
                "min_area": deposition_args.get("min_area", material.min_area),
            })
            if "name" not in deposition_args:
                raise TypeError("Missing keyword argument 'name' for material of type 'Wire'")
        if not ((implant is None) or isinstance(implant, msk.Mask)):
            raise TypeError("implant has to be 'None' type 'Mask'")
        if marker is not None:
            raise NotImplementedError("context handling for 'Wire'")
        if connects is not None:
            raise NotImplementedError("connects handling for 'Wire'")

        mask = material
        while isinstance(mask, Wire):
            mask = mask.material
        assert isinstance(mask, msk.Mask), "Internal Error"
        deposition_args["mask"] = mask
        super().__init__(**deposition_args)
        self.material = material
        self.implant = implant
        self.marker = marker
        self.connects = connects

class Via(_Primitive):
    def __init__(self, *, material,
        bottom, top,
        width, min_space, min_bottom_enclosure=0.0, min_top_enclosure=0.0,
        name=None
    ):
        if not isinstance(material, msk.Mask):
            raise TypeError("material is not of type 'Mask'")

        try:
            iter(bottom)
        except TypeError:
            bottom = (bottom,)
            min_bottom_enclosure = (min_bottom_enclosure,)
        else:
            bottom = tuple(bottom)
            try:
                iter(min_bottom_enclosure)
            except TypeError:
                min_bottom_enclosure = len(bottom)*(min_bottom_enclosure,)
            else:
                min_bottom_enclosure = tuple(min_bottom_enclosure)
        if len(bottom) != len(min_bottom_enclosure):
            raise ValueError(
                "min_bottom_enclosure has to be single or an iterable with same length as the bottom parameter",
            )
        for i in range(len(bottom)):
            wire = bottom[i]
            encl = min_bottom_enclosure[i]
            if not isinstance(wire, Wire):
                raise TypeError("bottom has to be of type 'Wire' or an iterable of type 'Wire'")
            if not isinstance(encl, float):
                try:
                    ok = (len(encl) == 2) and all(isinstance(f, float) for f in encl)
                except TypeError:
                    ok = False
                if not ok:
                    raise TypeError(dedent(
                        """min_bottom_enclosure value has to be either:
                        * single float
                        * for non-iterable bottom: an iterable of float of length 2
                        * for iterable bottom: an iterable with same length as bottom, elems have to be float or tuple of float of length 2
                        """
                    ))
        try:
            iter(top)
        except TypeError:
            top = (top,)
            min_top_enclosure = (min_top_enclosure,)
        else:
            top = tuple(top)
            try:
                iter(min_top_enclosure)
            except TypeError:
                min_top_enclosure = len(top)*(min_top_enclosure,)
            else:
                min_top_enclosure = tuple(min_top_enclosure)
        if len(top) != len(min_top_enclosure):
            raise ValueError(
                "min_top_enclosure has to be single or an iterable with same length as the top parameter",
            )
        for i in range(len(top)):
            wire = top[i]
            encl = min_top_enclosure[i]
            if not isinstance(wire, Wire):
                raise TypeError("top has to be of type 'Wire' or an iterable of type 'Wire'")
            if not isinstance(encl, float):
                try:
                    ok = (len(encl) == 2) and all(isinstance(f, float) for f in encl)
                except TypeError:
                    ok = False
                if not ok:
                    raise TypeError(dedent(
                        """min_top_enclosure value has to be either:
                        * single float
                        * for non-iterable top: an iterable of float of length 2
                        * for iterable top: an iterable with same length as top, elems have to be float or tuple of float of length 2
                        """
                    ))
        
        width = _util.i2f(width)
        if not isinstance(width, float):
            raise TypeError("width has to be a float")
        min_space = _util.i2f(min_space)
        if not isinstance(min_space, float):
            raise TypeError("min_space has to be a float")

        if name is None:
            name = material.name
        if not isinstance(name, str):
            raise TypeError("name has to be 'None' or a string")

        self.material = material
        self.bottom = bottom
        self.top = top
        self.width = width
        self.min_space = min_space
        self.min_bottom_enclosure = min_bottom_enclosure
        self.min_top_enclosure = min_top_enclosure
        self.name = name

class _MOSFETGate(_WidthSpacePrimitive):
    def __init__(self, mosfet, poly, active, min_l, min_w, min_gate_space):
        if not (
            isinstance(mosfet, MOSFET)
            and isinstance(poly, Wire)
            and isinstance(active, Wire)
            and isinstance(min_gate_space, float)
        ):
            raise RuntimeError("Internal error")
        if min_w < min_l:
            raise NotImplementedError("transistor with minimum width smaller than minimum length")

        super().__init__(name=mosfet.name + ".gate", min_width=min_l, min_space=min_gate_space)
        self.poly = poly
        self.active = active

class MOSFET(_Primitive):
    def __init__(
        self, name, *,
        poly, active, implant=None, oxide=None, well,
        min_l=None, min_w=None,
        min_activepoly_space, min_sd_width,
        min_polyactive_extension, min_gateimplant_enclosure, min_gate_space=None,
        min_contactgate_space=None,
        model=None,
    ):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        super().__init__(name)

        if not isinstance(poly, Wire):
            raise TypeError("poly has to be of type 'Wire'")
        if not isinstance(active, Wire):
            raise TypeError("active has to be of type 'Wire'")
        ok = True
        try:
            iter(implant)
        except TypeError:
            implant = (implant,)
        else:
            implant = tuple(implant)
        for l in implant:
            if not isinstance(l, Implant):
                raise TypeError("implant has to be of type 'Implant' or an iterable of type 'Implant'")
        if not ((oxide is None) or (isinstance(oxide, Deposition) and not isinstance(oxide, Wire))):
            raise TypeError("oxide has to be 'None' or of type 'Deposition'")
        if not isinstance(well, (Well, Substrate)):
            raise TypeError("well has to be of type 'Well' or 'Substrate'")

        if min_l is None:
            min_l = poly.min_width
        min_l = _util.i2f(min_l)
        if not isinstance(min_l, float):
            raise TypeError("min_l has to be a float") 
        if min_l < poly.min_width:
            raise ValueError("min_l smaller than poly min_width")
        if min_w is None:
            min_w = active.min_width
        min_w = _util.i2f(min_w)
        if not isinstance(min_w, float):
            raise TypeError("min_w has to be a float") 
        if min_w < active.min_width:
            raise ValueError("min_w smaller than active min_width")
        min_activepoly_space = _util.i2f(min_activepoly_space)
        if not isinstance(min_activepoly_space, float):
            raise TypeError("min_activepoly_space has to be a float")
        min_sd_width = _util.i2f(min_sd_width)
        if not isinstance(min_sd_width, float):
            raise TypeError("min_sd_width has to be a float")
        min_polyactive_extension = _util.i2f(min_polyactive_extension)
        if not isinstance(min_polyactive_extension, float):
            raise TypeError("min_polyactive_extension has to be a float")
        min_gateimplant_enclosure = _util.i2f(min_gateimplant_enclosure)
        if not isinstance(min_gateimplant_enclosure, float):
            raise TypeError("min_gateimplant_enclosure has to be a float")
        if min_gate_space is None:
            min_gate_space = poly.min_space
        if not isinstance(min_gate_space, float):
            raise TypeError("min_gate_space has to be 'None' or a float")
        min_contactgate_space = _util.i2f(min_contactgate_space)
        if not ((min_contactgate_space is None) or isinstance(min_contactgate_space, float)):
            raise TypeError("min_contactgate_space has to be 'None' or a float")

        if model is None:
            model = name
        if not isinstance(model, str):
            raise TypeError("model has to be a string")

        super().__init__(name)
        self.poly = poly
        self.active = active
        self.implant = implant
        self.well = well
        self.gate = _MOSFETGate(self, poly, active, min_l, min_w, min_gate_space)

        self.min_l = min_l
        self.min_w = min_w
        self.min_activepoly_space = min_activepoly_space
        self.min_sd_width = min_sd_width
        self.min_polyactive_extension = min_polyactive_extension
        self.min_gateimplant_enclosure = min_gateimplant_enclosure
        self.min_gate_space = min_gate_space
        if min_contactgate_space is not None:
            self.min_contactgate_space = min_contactgate_space

        self.model = model

        self.l = _PrimitiveProperty(self, "l")
        self.w = _PrimitiveProperty(self, "w")

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
