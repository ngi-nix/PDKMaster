"""The native technology primitives"""
from textwrap import dedent
from warnings import warn
from itertools import product
import abc

from . import _util, property_ as prp, mask as msk, wafer_ as wfr, edge as edg

__all__ = ["Marker", "Well", "Wire", "Via", "MOSFETGate", "MOSFET"]

class _Primitive(abc.ABC):
    def __init__(self, name):
        if not isinstance(name, str):
            raise TypeError("name argument of '{}' is not a string".format(self.__class__.__name__))

        self.name = name

        self._rules = None

    @property
    def rules(self):
        if self._rules is None:
            raise AttributeError("Accessing rules before they are generated")
        return self._rules

    @abc.abstractmethod
    def _generate_rules(self, tech):
        if self._rules is not None:
            raise ValueError("Rules can only be generated once")
        self._rules = tuple()

    @abc.abstractproperty
    def designmasks(self):
        return iter(tuple())

class _MaskPrimitive(_Primitive):
    def __init__(self, *, mask,
        enclosed_by=None, min_enclosure=0.0, grid=None, _want_designmask=False,
        **primitive_args
    ):
        if not _want_designmask:
            if not isinstance(mask, msk._Mask):
                raise TypeError("mask parameter for '{}' has to be of type 'Mask'".format(
                    self.__class__.__name__
                ))
        else:
            if not isinstance(mask, msk.DesignMask):
                raise TypeError("mask parameter for '{}' has to be of type 'DesignMask'".format(
                    self.__class__.__name__
                ))

        if enclosed_by is not None:
            enclosed_by = tuple(enclosed_by) if _util.is_iterable(enclosed_by) else (enclosed_by,)
            if _util.is_iterable(min_enclosure):
                min_enclosure = tuple(_util.i2f(minenc) for minenc in min_enclosure)
            else:
                min_enclosure = len(enclosed_by)*(_util.i2f(min_enclosure),)
            if not all(isinstance(enc, _MaskPrimitive) for enc in enclosed_by):
                raise TypeError("enclosed_by has to be of type '_Primitive' or an iterable of type '_Primitive'")
            if not all(isinstance(enc, float) for enc in min_enclosure):
                raise TypeError("min_enclosure has to be a float or an iterable of floats")
            if len(enclosed_by) != len(min_enclosure):
                raise ValueError("Wrong number of min_enclosure values given")
        if grid is not None:
            grid = _util.i2f(grid)
            if not isinstance(grid, float):
                raise TypeError("grid parameter for '{}' has to be a float".format(self.__class__.__name__))

        if not "name" in primitive_args:
            primitive_args["name"] = mask.name
        super().__init__(**primitive_args)
        self.mask = mask
        if grid is not None:
            self.grid = grid

        if enclosed_by is not None:
            self.enclosed_by = enclosed_by
            self.min_enclosure = min_enclosure

    @abc.abstractmethod
    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        if hasattr(self, "grid"):
            self._rules += (self.mask.grid == self.grid,)
        if hasattr(self, "enclosed_by"):
            for i in range(len(self.enclosed_by)):
                mask = self.enclosed_by[i].mask
                enclosure = self.min_enclosure[i]
                if isinstance(enclosure, float):
                    self._rules += (self.mask.enclosed_by(mask) >= enclosure,)
                else:
                    self._rules += (self.mask.enclosed_by_asymmetric(mask) >= enclosure,)

    @property
    def designmasks(self):
        return self.mask.designmasks

class _PrimitiveProperty(prp.Property):
    def __init__(self, primitive, name):
        if not isinstance(primitive, _Primitive):
            raise RuntimeError("Internal error: primitive not of type 'Primitive'")
        super().__init__(primitive.name + "." + name)

class Marker(_MaskPrimitive):
    def __init__(self, **mask_args):
        super().__init__(_want_designmask=True, **mask_args)

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

    @property
    def designmasks(self):
        return super().designmasks

class _WidthSpacePrimitive(_MaskPrimitive):
    def __init__(self, *,
        min_width, min_space, min_area=None, space_table=None,
        **maskprimitive_args
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
                if _util.is_iterable(width):
                    if not ((len(width) == 2) and all(isinstance(_util.i2f(w), float) for w in width)):
                        raise TypeError("first element in a space_table row has to be a float or an iterable of two floats")
                else:
                    if not isinstance(width, float):
                        raise TypeError("first element in a space_table row has to be a float or an iterable of two floats")
                if not isinstance(space, float):
                    raise TypeError("second element in a space_table row has to be a float")

        super().__init__(**maskprimitive_args)
        self.min_width = min_width
        self.min_space = min_space
        if min_area is not None:
            self.min_area = min_area
        if space_table is not None:
            def conv_spacetable_row(row):
                width = _util.i2f(row[0])
                space = _util.i2f(row[1])
                if _util.is_iterable(width):
                    width = tuple(_util.i2f(w) for w in width)
                return (width, space)

            self.space_table = tuple(conv_spacetable_row(row) for row in space_table)

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        self._rules += (
            self.mask.width >= self.min_width,
            self.mask.space >= self.min_space,
        )
        if hasattr(self, "min_area"):
            self._rules += (self.mask.area >= self.min_area,)
        if hasattr(self, "space_table"):
            for row in self.space_table:
                w = row[0]
                if isinstance(w, float):
                    submask = self.mask.parts_with(
                        condition=self.mask.width >= w,
                    )
                else:
                    submask = self.mask.parts_with(condition=(
                        self.mask.width >= w[0],
                        self.mask.length >= w[1],
                    ))
                self._rules += (msk.Spacing(submask, self.mask) >= row[1],)

class Implant(_WidthSpacePrimitive):
    # Implants are supposed to be disjoint unless they are used as combined implant
    # MOSFET and other primitives
    def __init__(self, **widthspace_args):
        if "_want_designmask" in widthspace_args:
            raise TypeError("got unexpected keyword argument '_want_designmaks'")
        super().__init__(_want_designmask=True, **widthspace_args)

class Well(Implant):
    # Wells are non-overlapping by design
    def __init__(self, *, min_space_samenet=None, **implant_args):
        min_space_samenet = _util.i2f(min_space_samenet)
        if not ((min_space_samenet is None) or isinstance(min_space_samenet, float)):
            raise TypeError("min_space_samenet has to be 'None' or a float")
            
        super().__init__(**implant_args)
        if min_space_samenet is not None:
            self.min_space_samenet = min_space_samenet

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        if hasattr(self, "min_space_samenet"):
            if not any(
                (isinstance(prim, DerivedWire)
                and hasattr(prim, "connects")
                and prim.connects == self
                ) for prim in tech.primitives
            ):
                raise tech.TechnologyError(f"min_space_samenet specified for '{self.name}' but it is not connected")
            self._rules += (msk.SameNet(self.mask).space >= self.min_space_samenet,)

class Deposition(_WidthSpacePrimitive):
    # Layer for material deposition, if it is conducting Wire subclass should be used
    def __init__(self, **widthspace_args):
        if "_want_designmask" in widthspace_args:
            raise TypeError("got unexpected keyword argument '_want_designmaks'")
        super().__init__(_want_designmask=True, **widthspace_args)

class Wire(Deposition):
    # Deposition layer that also a conductor
    pass

class DerivedWire(_WidthSpacePrimitive):
    def __init__(self, *, wire, marker,
        min_enclosure=0.0, connects=None,
        **widthspace_args,
    ):
        if not isinstance(wire, (Wire, DerivedWire)):
            raise TypeError("wire has to be of type 'Wire' or 'DerivedWire'")
        self.wire = wire

        if not _util.is_iterable(marker):
            marker = (marker,)
        if not all(isinstance(prim, (Implant, Marker)) for prim in marker):
            raise TypeError("marker has to be of type 'Implant' or 'Marker' or an iterable of those")
        self.marker = marker

        if "mask" in widthspace_args:
            raise TypeError("DerivedWire got an unexpected keyword argument 'mask'")
        else:
            widthspace_args["mask"] = msk.Intersect(prim.mask for prim in (wire, *marker))

        if "grid" in widthspace_args:
            raise TypeError("DerivedWire got an unexpected keyword argument 'grid'")

        if "min_width" in widthspace_args:
            if widthspace_args["min_width"] < wire.min_width:
                raise ValueError("min_width may not be smaller than base wire min_width")
        else:
            widthspace_args["min_width"] = wire.min_width

        if "min_space" in widthspace_args:
            if widthspace_args["min_space"] < wire.min_space:
                raise ValueError("min_space may not be smaller than base wire min_space")
        else:
            widthspace_args["min_space"] = wire.min_space

        super().__init__(**widthspace_args)

        min_enclosure = (_util.i2f(encl) for encl in min_enclosure) if _util.is_iterable(min_enclosure) else (_util.i2f(min_enclosure),)
        if not all(isinstance(enc, float) for enc in min_enclosure):
            raise TypeError("min_enclosure has to be a float or an iterable of float")
        if len(min_enclosure) == 1:
            min_enclosure = len(marker)*min_enclosure
        if len(min_enclosure) != len(marker):
            raise ValueError("mismatch in number of marker and min_enclosure")
        self.min_enclosure = min_enclosure

        if connects is not None:
            if not isinstance(connects, Well):
                raise TypeError("connects has to be 'None' or of type 'Well'")
            self.connects = connects

    def _generate_rules(self, tech):
        # Do not generate the default width/space rules.
        _Primitive._generate_rules(self, tech)

        if self.min_width > self.wire.min_width:
            self._rules += (self.mask.width >= self.min_width,)
        if self.min_space > self.wire.min_space:
            self._rules += (self.mask.space >= self.min_space,)
        if hasattr(self, "min_area"):
            if (not hasattr(self.wire, "min_area")) or (self.min_area > self.wire.min_area):
                self._rules += (self.mask.area >= self.min_area,)
        if hasattr(self, "connects"):
            self._rules += (msk.Connect(self.mask, self.connects.mask),)

    @property
    def designmasks(self):
        for mask in super().designmasks:
            yield mask
        if hasattr(self, "connects"):
            for mask in self.connects.designmasks:
                yield mask

class Via(_MaskPrimitive):
    def __init__(self, *,
        bottom, top,
        width, min_space, min_bottom_enclosure=0.0, min_top_enclosure=0.0,
        **primitive_args,
    ):
        if "_want_designmask" in primitive_args:
            raise TypeError("got unexpected keyword argument '_want_designmaks'")
        if _util.is_iterable(bottom):
            bottom = tuple(bottom)
            if _util.is_iterable(min_bottom_enclosure):
                min_bottom_enclosure = tuple(min_bottom_enclosure)
            else:
                min_bottom_enclosure = len(bottom)*(min_bottom_enclosure,)
        else:
            bottom = (bottom,)
            min_bottom_enclosure = (min_bottom_enclosure,)
        if len(bottom) != len(min_bottom_enclosure):
            raise ValueError(
                "min_bottom_enclosure has to be single or an iterable with same length as the bottom parameter",
            )
        for i in range(len(bottom)):
            wire = bottom[i]
            encl = min_bottom_enclosure[i]
            if not isinstance(wire, (Wire, DerivedWire)):
                raise TypeError("bottom has to be of type 'Wire' or 'DerivedWire' or an iterable of those")
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
        if _util.is_iterable(top):
            top = tuple(top)
            if _util.is_iterable(min_top_enclosure):
                min_top_enclosure = tuple(min_top_enclosure)
            else:
                min_top_enclosure = len(top)*(min_top_enclosure,)
        else:
            top = (top,)
            min_top_enclosure = (min_top_enclosure,)
        if len(top) != len(min_top_enclosure):
            raise ValueError(
                "min_top_enclosure has to be single or an iterable with same length as the top parameter",
            )
        for i in range(len(top)):
            wire = top[i]
            encl = min_top_enclosure[i]
            if not isinstance(wire, (Wire, DerivedWire)):
                raise TypeError("top has to be of type 'Wire' or 'DerivedWire' or an iterable of those")
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

        if "name" not in primitive_args:
            if "mask" in primitive_args:
                primitive_args["name"] = primitive_args["mask"].name

        super().__init__(_want_designmask=True, **primitive_args)
        self.bottom = bottom
        self.top = top
        self.width = width
        self.min_space = min_space
        self.min_bottom_enclosure = min_bottom_enclosure
        self.min_top_enclosure = min_top_enclosure

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        self._rules += (
            self.mask.width == self.width,
            self.mask.space >= self.min_space,
            # *(
            #     self.mask.enclosed_by(self.bottom[i].mask) >= self.min_bottom_enclosure[i]
            #     for i in range(len(self.bottom))
            # ),
            # *(
            #     self.mask.enclosed_by(self.top[i].mask) >= self.min_top_enclosure[i]
            #     for i in range(len(self.top))
            # ),
        )
        self._rules += (msk.Connect((b.mask for b in self.bottom), self.mask),)
        for i in range(len(self.bottom)):
            if isinstance(self.min_bottom_enclosure[i], float):
                self._rules += (self.mask.enclosed_by(self.bottom[i].mask) >= self.min_bottom_enclosure[i],)
            else:
                self._rules += (self.mask.enclosed_by_asymmetric(self.bottom[i].mask) >= self.min_bottom_enclosure[i],)
        self._rules += (msk.Connect(self.mask, (b.mask for b in self.top)),)
        for i in range(len(self.top)):
            if isinstance(self.min_top_enclosure[i], float):
                self._rules += (self.mask.enclosed_by(self.top[i].mask) >= self.min_top_enclosure[i],)
            else:
                self._rules += (self.mask.enclosed_by_asymmetric(self.top[i].mask) >= self.min_top_enclosure[i],)

    @property
    def designmasks(self):
        for mask in super().designmasks:
            yield mask
        for conn in self.bottom + self.top:
            for mask in conn.designmasks:
                yield mask

class Spacing(_Primitive):
    def __init__(self, *, primitives1, primitives2, min_space):
        primitives1 = tuple(primitives1) if _util.is_iterable(primitives1) else (primitives1,)
        if not all(isinstance(prim, _MaskPrimitive) for prim in primitives1):
            raise TypeError("primitives1 has to be of type '_Primitive' or an iterable of type '_Primitive'")
        primitives2 = tuple(primitives2) if _util.is_iterable(primitives2) else (primitives2,)
        if not all(isinstance(prim, _MaskPrimitive) for prim in primitives2):
            raise TypeError("primitives2 has to be of type '_Primitive' or an iterable of type '_Primitive'")
        min_space = _util.i2f(min_space)
        if not isinstance(min_space, float):
            raise TypeError("min_space has to be a float")

        name = "spacing({})".format(",".join(
            (
                prims[0].name if len(prims) == 1
                else "({})".format(",".join(prim.name for prim in prims))
            ) for prims in (primitives1, primitives2)
        ))
        super().__init__(name)
        self.primitives1 = primitives1
        self.primitives2 = primitives2
        self.min_space = min_space

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        self._rules += tuple(
            msk.Spacing(prim1.mask,prim2.mask) >= self.min_space
            for prim1, prim2 in product(self.primitives1, self.primitives2)
        )

    @property
    def designmasks(self):
        return super().designmasks

class MOSFETGate(_WidthSpacePrimitive):
    def __init__(self, *, name=None, poly, active, oxide=None,
        min_l=None, min_w=None,
        min_sd_width=None, min_polyactive_extension=None, min_gate_space=None,
        contact=None, min_contactgate_space=None,
    ):
        if not isinstance(poly, (Wire, DerivedWire)):
            raise TypeError("poly has to be of type 'Wire' or 'DerivedWire'")
        if isinstance(poly, DerivedWire):
            raise NotImplementedError("poly of type 'DerivedWire'")
        self.poly = poly

        if not isinstance(active, (Wire, DerivedWire)):
            raise TypeError("active has to be of type 'Wire' or 'DerivedWire'")
        if isinstance(active, DerivedWire):
            raise NotImplementedError("active of type 'DerivedWire'")
        self.active = active

        prims = (poly, active)
        if oxide is not None:
            if not (isinstance(oxide, Deposition) and not isinstance(oxide, Wire)):
                raise TypeError("oxide has to be 'None' or of type 'Deposition'")
            self.oxide = oxide
            prims += (oxide,)

        if name is None:
            name = "gate({})".format(",".join(prim.name for prim in prims))
            gatename = "gate:" + "+".join(prim.name for prim in prims)
        else:
            gatename = f"gate:{name}"
        if not isinstance(name, str):
            raise TypeError("name has to be 'None' or a string")

        if min_l is not None:
            min_l = _util.i2f(min_l)
            if not isinstance(min_l, float):
                raise TypeError("min_l has to be 'None' or a float")
            self.min_l = min_l
        else:
            # Local use only
            min_l = poly.min_width

        if min_w is not None:
            min_w = _util.i2f(min_w)
            if not isinstance(min_w, float):
                raise TypeError("min_w has to be 'None' or a float")
            self.min_w = min_w
        else:
            # Local use only
            min_w = active.min_width

        if min_sd_width is not None:
            min_sd_width = _util.i2f(min_sd_width)
            if not isinstance(min_sd_width, float):
                raise TypeError("min_sd_width has to be a float")
            self.min_sd_width = min_sd_width

        if min_polyactive_extension is not None:
            min_polyactive_extension = _util.i2f(min_polyactive_extension)
            if not isinstance(min_polyactive_extension, float):
                raise TypeError("min_polyactive_extension has to be a float")
            self.min_polyactive_extension = min_polyactive_extension

        if min_gate_space is not None:
            min_gate_space = _util.i2f(min_gate_space)
            if not isinstance(min_gate_space, float):
                raise TypeError("min_gate_space has to be 'None' or a float")
            self.min_gate_space = min_gate_space
        else:
            # Local use only
            min_gate_space = poly.min_space

        if min_contactgate_space is not None:
            min_contactgate_space = _util.i2f(min_contactgate_space)
            if not isinstance(min_contactgate_space, float):
                raise TypeError("min_contactgate_space has to be 'None' or a float")
            self.min_contactgate_space = min_contactgate_space
            if not isinstance(contact, Via):
                raise TypeError("contact has to be of type 'Via'")
            self.contact = contact
        elif contact is not None:
            raise ValueError("contact layer provided without min_contactgate_space specification")

        mask = msk.Intersect(prim.mask for prim in prims).alias(gatename)
        super().__init__(
            name=name, mask=mask,
            min_width=min(min_l, min_w), min_space=min_gate_space,
        )

    def _generate_rules(self, tech):
        _MaskPrimitive._generate_rules(self, tech)
        active_mask = self.active.mask
        poly_mask = self.poly.mask

        if hasattr(self, "oxide"):
            mask = self.mask
        else:
            # Override mask
            oxide_masks = tuple(
                gate.oxide.mask for gate in filter(
                    lambda prim: (
                        isinstance(prim, MOSFETGate)
                        and prim.active == self.active
                        and prim.poly == self.poly
                        and hasattr(prim, "oxide")
                    ), tech.primitives,
                )
            )
            if len(oxide_masks) == 0:
                mask = self.mask
            else:
                if len(oxide_masks) == 1:
                    oxides_mask = oxide_masks[0]
                else:
                    oxides_mask = msk.Join(oxide_masks)
                mask = msk.Intersect(
                    (active_mask, poly_mask, wfr.wafer.remove(oxides_mask)),
                ).alias(self.mask.name)

        mask_used = False
        if hasattr(self, "min_l"):
            self._rules += (edg.Intersect((edg.MaskEdge(active_mask), edg.MaskEdge(self.mask))).length >= self.min_l,)
        if hasattr(self, "min_w"):
            self._rules += (edg.Intersect((edg.MaskEdge(poly_mask), edg.MaskEdge(self.mask))).length >= self.min_w,)
        if hasattr(self, "min_sd_width"):
            self._rules += (active_mask.extend_over(mask) >= self.min_sd_width,)
            mask_used = True
        if hasattr(self, "min_polyactive_extension"):
            self._rules += (poly_mask.extend_over(mask) >= self.min_polyactive_extension,)
            mask_used = True
        if hasattr(self, "min_gate_space"):
            self._rules += (mask.space >= self.min_gate_space,)
            mask_used = True
        if hasattr(self, "min_contactgate_space"):
            self._rules += (msk.Spacing(mask, self.contact.mask) >= self.min_contactgate_space,)
            mask_used = True
        if mask_used:
            self._rules += (mask,)

class MOSFET(_Primitive):
    def __init__(
        self, name, *,
        gate, implant=None, well=None,
        min_l=None, min_w=None,
        min_sd_width=None, min_polyactive_extension=None,
        min_gateimplant_enclosure, min_gate_space=None,
        contact=None, min_contactgate_space=None,
        model=None,
    ):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        super().__init__(name)

        if not isinstance(gate, MOSFETGate):
            raise TypeError("gate has to be of type 'MOSFETGate'")
        self.gate = gate

        if implant is not None:
            implant = tuple(implant) if _util.is_iterable(implant) else (implant,)
            if not all(isinstance(l, Implant) for l in implant):
                raise TypeError("implant has to be 'None', of type 'Implant' or an iterable of type 'Implant'")
            self.implant = implant
        elif not isinstance(gate.active, DerivedWire):
            raise TypeError("active wire of gate has to be of type 'DerivedWire' if implant is 'None'")

        if well is not None:
            if not isinstance(well, Well):
                raise TypeError("well has to be 'None' or of type 'Well'")
            self.well = well

        if min_l is not None:
            min_l = _util.i2f(min_l)
            if not isinstance(min_l, float):
                raise TypeError("min_l has to be 'None' or a float")
            if min_l <= gate.min_l:
                raise ValueError("min_l has to be bigger than gate min_l if not 'None'")
            self.min_l = min_l

        if min_w is not None:
            min_w = _util.i2f(min_w)
            if not isinstance(min_w, float):
                raise TypeError("min_w has to be 'None' or a float")
            if min_w <= gate.min_w:
                raise ValueError("min_w has to be bigger than gate min_w if not 'None'")
            self.min_w = min_w

        if min_sd_width is not None:
            min_sd_width = _util.i2f(min_sd_width)
            if not isinstance(min_sd_width, float):
                raise TypeError("min_sd_width has to be a float")
            self.min_sd_width = min_sd_width
        elif not hasattr(gate, "min_sd_width"):
            raise ValueError("min_sd_width has to be either provided for the transistor gate or the transistor itself")

        if min_polyactive_extension is not None:
            min_polyactive_extension = _util.i2f(min_polyactive_extension)
            if not isinstance(min_polyactive_extension, float):
                raise TypeError("min_polyactive_extension has to be a float")
            self.min_polyactive_extension = min_polyactive_extension
        elif not hasattr(gate, "min_polyactive_extension"):
            raise ValueError("min_polyactive_extension has to be either provided for the transistor gate or the transistor itself")

        min_gateimplant_enclosure = _util.i2f(min_gateimplant_enclosure)
        if not isinstance(min_gateimplant_enclosure, float):
            raise TypeError("min_gateimplant_enclosure has to be a float")
        self.min_gateimplant_enclosure = min_gateimplant_enclosure

        if min_gate_space is not None:
            min_gate_space = _util.i2f(min_gate_space)
            if not isinstance(min_gate_space, float):
                raise TypeError("min_gate_space has to be 'None' or a float")
            self.min_gate_space = min_gate_space

        if min_contactgate_space is not None:
            min_contactgate_space = _util.i2f(min_contactgate_space)
            if not isinstance(min_contactgate_space, float):
                raise TypeError("min_contactgate_space has to be 'None' or a float")
            self.min_contactgate_space = min_contactgate_space
            if contact is None:
                if not hasattr(gate, "contact"):
                    raise ValueError("no contact layer provided for min_contactgate_space specification")
                contact = gate.contact
            elif not isinstance(contact, Via):
                raise TypeError("contact has to be of type 'Via'")
            self.contact = contact
        elif contact is not None:
            raise ValueError("contact layer provided without min_contactgate_space specification")

        if model is None:
            model = name
        if not isinstance(model, str):
            raise TypeError("model has to be 'None' or a string")
        self.model = model

        self.l = _PrimitiveProperty(self, "l")
        self.w = _PrimitiveProperty(self, "w")

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        markers = (self.well if hasattr(self, "well") else tech.substrate,)
        if hasattr(self, "implant"):
            markers += self.implant
        markedgate_mask = msk.Intersect(
            (self.gate.mask, *(marker.mask for marker in markers))
        ).alias(f"gate:mosfet:{self.name}")
        markedgate_edge = edg.MaskEdge(markedgate_mask)
        poly_mask = self.gate.poly.mask
        poly_edge = edg.MaskEdge(poly_mask)
        active_mask = self.gate.active.mask
        active_edge = edg.MaskEdge(active_mask)

        self._rules += (markedgate_mask,)
        if hasattr(self, "min_l"):
            self._rules += (edg.Intersect((markedgate_edge, active_edge)).length >= self.min_l,)
        if hasattr(self, "min_w"):
            self._rules += (edg.Intersect((markedgate_edge, poly_edge)).length >= self.min_w,)
        if hasattr(self, "min_sd_width"):
            self._rules += (active_mask.extend_over(markedgate_mask) >= self.min_sd_width,)
        if hasattr(self, "min_polyactive_extension"):
            self._rules += (poly_mask.extend_over(markedgate_mask) >= self.min_polyactive_extension,)
        self._rules += tuple(markedgate_mask.enclosed_by(impl.mask) >= self.min_gateimplant_enclosure for impl in self.implant)
        if hasattr(self, "min_gate_space"):
            self._rules += (markedgate_mask.space >= self.min_gate_space,)
        if hasattr(self, "min_contactgate_space"):
            self.rules += (msk.Spacing(markedgate_mask, self.contact.mask) >= self.min_contactgate_space,)

    @property
    def designmasks(self):
        for mask in super().designmasks:
            yield mask
        for mask in self.gate.designmasks:
            yield mask
        if hasattr(self, "implant"):
            for impl in self.implant:
                for mask in impl.designmasks:
                    yield mask
        if hasattr(self, "well"):
            for mask in self.well.designmasks:
                yield mask
        if hasattr(self, "contact"):
            if (not hasattr(self.gate, "contact")) or (self.contact != self.gate.contact):
                for mask in self.contact.designmasks:
                    yield mask

class Primitives:
    def __init__(self):
        self._primitives = {}
        self._frozen = False

    def __getitem__(self, key):
        return self._primitives[key]

    def __getattr__(self, name):
        try:
            return self._primitives[name]
        except KeyError:
            raise AttributeError("Primitive '{}' not present".format(name))

    def freeze(self):
        self._frozen = True

    def __iadd__(self, other):
        if self._frozen:
            raise ValueError("Can't add primitive when frozen")
        e = TypeError("Can only add 'Primitive' object or an iterable of 'Primitive' objects to 'Primitives'")
        prims = tuple(other) if _util.is_iterable(other) else (other,)
        for prim in prims:
            if not isinstance(prim, _Primitive):
                raise e
            if prim.name in self._primitives:
                raise ValueError("Primitive '{}' already exists".format(prim.name))

        self._primitives.update({prim.name: prim for prim in prims})

        return self

    def __iter__(self):
        return iter(self._primitives.values())
