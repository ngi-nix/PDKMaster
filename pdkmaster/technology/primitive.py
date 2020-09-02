"""The native technology primitives"""
from textwrap import dedent
from warnings import warn
from itertools import product, combinations
import abc

from .. import _util
from . import (
    rule as rle, property_ as prp, port as prt, mask as msk, wafer_ as wfr,
    edge as edg,
)

__all__ = ["Marker", "Auxiliary", "ExtraProcess",
           "Implant", "Well",
           "Insulator", "WaferWire", "GateWire", "MetalWire", "TopMetalWire",
           "Resistor",
           "Via", "PadOpening",
           "MOSFETGate", "MOSFET",
           "Spacing",
           "UnusedPrimitiveError", "UnconnectedPrimitiveError"]

class _Primitive(abc.ABC):
    _names = set()

    @abc.abstractmethod
    def __init__(self, name):
        if not isinstance(name, str):
            raise TypeError(f"name argument of '{self.__class__.__name__}' is not a string")
        if name in _Primitive._names:
            raise ValueError(f"primitive with name '{name}' already exists")
        _Primitive._names.update(name)
        self.name = name

        self.ports = prt.Ports()

        self._rules = None

    def __repr__(self):
        cname = self.__class__.__name__.split(".")[-1]
        return f"{cname}({self.name})"

    def __eq__(self, other):
        return (self.__class__ == other.__class__) and (self.name == other.name)

    def __hash__(self):
        return hash(self.name)

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
    @abc.abstractmethod
    def __init__(self, *, mask, grid=None, **primitive_args):
        if not "name" in primitive_args:
            primitive_args["name"] = mask.name
        super().__init__(**primitive_args)

        if not isinstance(mask, msk._Mask):
            raise TypeError("mask parameter for '{}' has to be of type 'Mask'".format(
                self.__class__.__name__
            ))
        if isinstance(mask, msk.DesignMask):
            self.ports += msk.MaskPort("conn", mask)
        self.mask = mask

        if grid is not None:
            grid = _util.i2f(grid)
            if not isinstance(grid, float):
                raise TypeError("grid parameter for '{}' has to be a float".format(self.__class__.__name__))
            self.grid = grid



    @abc.abstractmethod
    def _generate_rules(self, tech, *, gen_mask=True):
        super()._generate_rules(tech)

        if gen_mask and isinstance(self.mask, rle._Rule):
            self._rules += (self.mask,)
        if hasattr(self, "grid"):
            self._rules += (self.mask.grid == self.grid,)

    @property
    def designmasks(self):
        return self.mask.designmasks

    def _designmask_from_name(self, args):
        if "mask" in args:
            raise TypeError(f"{self.__class__.__name__} got unexpected keyword argument 'mask'")
        args["mask"] = msk.DesignMask(args["name"], gds_layer=args.pop("gds_layer", None))

class _PrimitiveProperty(prp.Property):
    def __init__(self, primitive, name):
        if not isinstance(primitive, _Primitive):
            raise RuntimeError("Internal error: primitive not of type 'Primitive'")
        super().__init__(primitive.name + "." + name)

class Marker(_MaskPrimitive):
    def __init__(self, name, **mask_args):
        mask_args["name"] = name
        self._designmask_from_name(mask_args)
        super().__init__(**mask_args)

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

    @property
    def designmasks(self):
        return super().designmasks

class Auxiliary(_MaskPrimitive):
    # Layer not used in other primitives but defined by foundry for the technology
    def __init__(self, name, **mask_args):
        mask_args["name"] = name
        self._designmask_from_name(mask_args)
        super().__init__(**mask_args)

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

    @property
    def designmasks(self):
        return super().designmasks

class _WidthSpacePrimitive(_MaskPrimitive):
    @abc.abstractmethod
    def __init__(self, *,
        min_width, min_space, space_table=None,
        min_area=None, min_density=None, max_density=None,
        **maskprimitive_args
    ):
        min_width = _util.i2f(min_width)
        min_space = _util.i2f(min_space)
        min_area = _util.i2f(min_area)

        if not (isinstance(min_width, float) and isinstance(min_space, float)):
            raise TypeError("min_width and min_space arguments for '{}' have to be floats".format(
                self.__class__.__name__,
            ))
        self.min_width = min_width
        self.min_space = min_space

        if min_area is not None:
            min_area = _util.i2f(min_area)
            if not isinstance(min_area, float):
                raise TypeError("min_area argument for '{}' has to be 'None' or a float".format(
                    self.__class__.__name__,
                ))
            self.min_area = min_area

        if min_density is not None:
            min_density = _util.i2f(min_density)
            if not isinstance(min_density, float):
                raise TypeError("min_density has to be 'None' or a float")
            if (min_density < 0.0) or (min_density > 1.0):
                raise ValueError("min_density has be between 0.0 and 1.0")
            self.min_density = min_density

        if max_density is not None:
            max_density = _util.i2f(max_density)
            if not isinstance(max_density, float):
                raise TypeError("max_density has to be 'None' or a float")
            if (max_density < 0.0) or (max_density > 1.0):
                raise ValueError("max_density has be between 0.0 and 1.0")
            self.max_density = max_density

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

            def conv_spacetable_row(row):
                width = _util.i2f(row[0])
                space = _util.i2f(row[1])
                if _util.is_iterable(width):
                    width = tuple(_util.i2f(w) for w in width)
                return (width, space)

            self.space_table = tuple(conv_spacetable_row(row) for row in space_table)

        super().__init__(**maskprimitive_args)

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        self._rules += (
            self.mask.width >= self.min_width,
            self.mask.space >= self.min_space,
        )
        if hasattr(self, "min_area"):
            self._rules += (self.mask.area >= self.min_area,)
        if hasattr(self, "min_density"):
            self._rules += (self.mask.density >= self.min_density,)
        if hasattr(self, "max_density"):
            self._rules += (self.mask.density <= self.max_density,)
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

class ExtraProcess(_WidthSpacePrimitive):
    def __init__(self, name, **widthspace_args):
        widthspace_args["name"] = name
        self._designmask_from_name(widthspace_args)
        super().__init__(**widthspace_args)

class Implant(_WidthSpacePrimitive):
    # Implants are supposed to be disjoint unless they are used as combined implant
    # MOSFET and other primitives
    def __init__(self, name, *, type_, **widthspace_args):
        widthspace_args["name"] = name
        self._designmask_from_name(widthspace_args)

        if not isinstance(type_, str):
            raise TypeError("type_ has to be a string")
        if type_ not in ("n", "p", "adjust"):
            raise ValueError("type_ has to be 'n', 'p' or adjust")
        self.type_ = type_

        super().__init__(**widthspace_args)

class Well(Implant):
    # Wells are non-overlapping by design
    def __init__(self, name, *, min_space_samenet=None, **implant_args):
        implant_args["name"] = name
        super().__init__(**implant_args)

        if min_space_samenet is not None:
            min_space_samenet = _util.i2f(min_space_samenet)
            if not isinstance(min_space_samenet, float):
                raise TypeError("min_space_samenet has to be 'None' or a float")
            if min_space_samenet >= self.min_space:
                raise ValueError("min_space_samenet has to be smaller than min_space")
            self.min_space_samenet = min_space_samenet

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        if hasattr(self, "min_space_samenet"):
            self._rules += (msk.SameNet(self.mask).space >= self.min_space_samenet,)

class Insulator(_WidthSpacePrimitive):
    def __init__(self, name, **widthspace_args):
        widthspace_args["name"] = name
        self._designmask_from_name(widthspace_args)
        super().__init__(**widthspace_args)

class WaferWire(_WidthSpacePrimitive):
    # The wire made from wafer material and normally isolated by LOCOS for old technlogies
    # and STI for other ones.
    def __init__(self, name, *,
        allow_in_substrate,
        implant, implant_abut, allow_contactless_implant,
        well, min_well_enclosure, min_substrate_enclosure=None, allow_well_crossing,
        **widthspace_args
    ):
        widthspace_args["name"] = name
        self._designmask_from_name(widthspace_args)

        if not isinstance(allow_in_substrate, bool):
            raise TypeError("allow_in_substrate has to be a bool")
        self.allow_in_substrate = allow_in_substrate

        implant = tuple(implant) if _util.is_iterable(implant) else (implant,)
        if not all(
            isinstance(impl, Implant) and not isinstance(impl, Well)
            for impl in implant
        ):
            raise TypeError("implant has to be of type 'Implant' that is not a 'Well' or an interable of that")
        self.implant = implant
        if isinstance(implant_abut, str):
            _conv = {"all": implant, "none": tuple()}
            if implant_abut not in _conv:
                raise ValueError("only 'all' or 'none' allowed for a string implant_abut")
            implant_abut = _conv[implant_abut]
        if not all(impl in implant for impl in implant_abut):
            raise ValueError("implant_abut has to be an iterable of 'Implant' that are also in implant")
        self.implant_abut = implant_abut
        if not isinstance(allow_contactless_implant, bool):
            raise TypeError("allow_contactless_implant has to be a bool")
        self.allow_contactless_implant = allow_contactless_implant

        well = tuple(well) if _util.is_iterable(well) else (well,)
        if not all(isinstance(w, Well) for w in well):
            raise TypeError("well has to be of type 'Well' or an iterable 'Well'")
        for w in well:
            if not any(impl.type_ == w.type_ for impl in implant):
                raise UnconnectedPrimitiveError(well)
        self.well = well
        min_well_enclosure = (
            tuple(_util.i2f(enc) for enc in min_well_enclosure) if _util.is_iterable(min_well_enclosure)
            else (_util.i2f(min_well_enclosure),)
        )
        if len(min_well_enclosure) == 1 and len(well) > 1:
            min_well_enclosure *= len(well)
        if not all(isinstance(enc, float) for enc in min_well_enclosure):
            raise TypeError("min_well_enclosure has to be a float or an iterable of float")
        if len(well) != len(min_well_enclosure):
            raise ValueError("mismatch between number of well and number of min_well_enclosure")
        self.min_well_enclosure = min_well_enclosure
        if allow_in_substrate:
            if min_substrate_enclosure is None:
                if len(min_well_enclosure) == 1:
                    min_substrate_enclosure = min_well_enclosure[0]
                else:
                    raise TypeError("min_substrate_enclosure has be provided when providing multi min_well_enclosure values")
            min_substrate_enclosure = _util.i2f(min_substrate_enclosure)
            if not isinstance(min_substrate_enclosure, float):
                raise TypeError("min_substrate_enclosure has to be 'None' or a float")
            self.min_substrate_enclosure = min_substrate_enclosure
        elif min_substrate_enclosure is not None:
            raise TypeError("min_substrate_enclosure should be 'None' if allow_in_substrate is 'False'")
        if not isinstance(allow_well_crossing, bool):
            raise TypeError("allow_well_crossing has to be a bool")
        self.allow_well_crossing = allow_well_crossing

        super().__init__(**widthspace_args)

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        for impl in self.implant:
            if self.allow_in_substrate and (impl.type_ == tech.substrate_type):
                self._rules += (msk.Connect(msk.Intersect((self.mask, impl.mask)), tech.substrate),)
            if impl not in self.implant_abut:
                self._rules += (edg.MaskEdge(impl.mask).interact_with(self.mask).length == 0,)
        for implduo in combinations((impl.mask for impl in self.implant_abut), 2):
            self._rules += (msk.Intersect(implduo).area == 0,)
        # TODO: allow_contactless_implant
        for impl, w in product(self.implant, self.well):
            if impl.type_ == w.type_:
                self._rules += (msk.Connect(w.mask, msk.Intersect((self.mask, impl.mask))),)
        for i in range(len(self.well)):
            w = self.well[i]
            enc = self.min_well_enclosure[i]
            self._rules += (self.mask.enclosed_by(w.mask) >= enc,)
        if hasattr(self, "min_substrate_enclosure"):
            self._rules += (self.mask.enclosed_by(tech.substrate) >= self.min_substrate_enclosure,)
        if not self.allow_well_crossing:
            mask_edge = edg.MaskEdge(self.mask)
            self._rules += tuple(mask_edge.interact_with(w.mask).length == 0 for w in self.well)

class GateWire(_WidthSpacePrimitive):
    def __init__(self, name, **widthspace_args):
        widthspace_args["name"] = name
        self._designmask_from_name(widthspace_args)
        super().__init__(**widthspace_args)

class MetalWire(_WidthSpacePrimitive):
    def __init__(self, name, **widthspace_args):
        widthspace_args["name"] = name
        self._designmask_from_name(widthspace_args)
        super().__init__(**widthspace_args)

class TopMetalWire(MetalWire):
    pass

class Resistor(_WidthSpacePrimitive):
    def __init__(self, name=None, *,
        wire, indicator, min_enclosure,
        **widthspace_args,
    ):
        if not isinstance(wire, (WaferWire, GateWire, MetalWire)):
            raise TypeError(
                "wire has to be of type '(Wafer|Gate|Metal)Wire'"
            )
        self.wire = wire

        if not _util.is_iterable(indicator):
            indicator = (indicator,)
        if not all(isinstance(prim, (Marker, ExtraProcess)) for prim in indicator):
            raise TypeError(
                "indicator has to be of type 'Marker' or 'ExtraProcess' "
                "or an iterable of those"
            )
        self.indicator = indicator

        if "mask" in widthspace_args:
            raise TypeError("Resistor got an unexpected keyword argument 'mask'")
        else:
            widthspace_args["mask"] = msk.Intersect(prim.mask for prim in (wire, *indicator))

        if "grid" in widthspace_args:
            raise TypeError("Resistor got an unexpected keyword argument 'grid'")

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

        if name is not None:
            widthspace_args["name"] = name
        super().__init__(**widthspace_args)

        min_enclosure = (
            tuple(_util.i2f(encl) for encl in min_enclosure)
            if _util.is_iterable(min_enclosure)
            else (_util.i2f(min_enclosure),)
        )
        if not all(isinstance(enc, float) for enc in min_enclosure):
            raise TypeError("min_enclosure has to be a float or an iterable of float")
        if len(min_enclosure) == 1:
            min_enclosure = len(indicator)*min_enclosure
        if len(min_enclosure) != len(indicator):
            raise ValueError("mismatch in number of indicator and min_enclosure")
        self.min_enclosure = min_enclosure

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

class Via(_MaskPrimitive):
    def __init__(self, name, *,
        bottom, top,
        width, min_space, min_bottom_enclosure=0.0, min_top_enclosure=0.0,
        **primitive_args,
    ):
        primitive_args["name"] = name
        self._designmask_from_name(primitive_args)
        if _util.is_iterable(bottom):
            bottom = tuple(bottom)
            if _util.is_iterable(min_bottom_enclosure):
                min_bottom_enclosure = tuple(min_bottom_enclosure)
            else:
                min_bottom_enclosure = len(bottom)*(min_bottom_enclosure,)
        else:
            bottom = (bottom,)
            min_bottom_enclosure = (
                tuple(min_bottom_enclosure) if _util.is_iterable(min_bottom_enclosure)
                else min_bottom_enclosure,
            )
        if len(bottom) != len(min_bottom_enclosure):
            raise ValueError(
                "min_bottom_enclosure has to be single or an iterable with same length as the bottom parameter",
            )
        for i in range(len(bottom)):
            wire = bottom[i]
            encl = min_bottom_enclosure[i]
            if not (
                isinstance(wire, (WaferWire, GateWire, MetalWire, Resistor))
                and not isinstance(wire, TopMetalWire)
            ):
                raise TypeError(
                    "bottom has to be of type '(Wafer|Gate|Metal)Wire' or 'Resistor'\n"
                    "or an iterable of those"
                )
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
            min_top_enclosure = (
                tuple(min_top_enclosure) if _util.is_iterable(min_top_enclosure)
                else min_top_enclosure,
            )
        if len(top) != len(min_top_enclosure):
            raise ValueError(
                "min_top_enclosure has to be single or an iterable with same length as the top parameter",
            )
        for i in range(len(top)):
            wire = top[i]
            encl = min_top_enclosure[i]
            if not isinstance(wire, (MetalWire, Resistor)):
                raise TypeError("top has to be of type 'MetalWire' or 'Resistor' or an iterable of those")
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

        super().__init__(**primitive_args)
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

class PadOpening(_WidthSpacePrimitive):
    def __init__(self, name, *, bottom, min_bottom_enclosure, **widthspace_args):
        widthspace_args["name"] = name
        self._designmask_from_name(widthspace_args)
        super().__init__(**widthspace_args)

        if not (isinstance(bottom, MetalWire) and not isinstance(bottom, TopMetalWire)):
            raise TypeError("bottom has to be of type 'MetalWire'")
        self.bottom = bottom
        min_bottom_enclosure = _util.i2f(min_bottom_enclosure)
        if not isinstance(min_bottom_enclosure, float):
            raise TypeError("min_bottom_enclosure has to be a float")
        self.min_bottom_enclosure = min_bottom_enclosure

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        self._rules += (self.mask.enclosed_by(self.bottom.mask) >= self.min_bottom_enclosure,)

    @property
    def designmasks(self):
        for mask in super().designmasks:
            yield mask
        yield self.bottom.mask

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

        name = "Spacing({})".format(",".join(
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

    def __repr__(self):
        return self.name

class MOSFETGate(_WidthSpacePrimitive):
    class _ComputedProps:
        def __init__(self, gate):
            self.gate = gate

        @property
        def min_l(self):
            gate = self.gate
            try:
                return gate.min_l
            except AttributeError:
                return gate.poly.min_width

        @property
        def min_w(self):
            gate = self.gate
            try:
                return gate.min_w
            except AttributeError:
                return gate.active.min_width

        @property
        def min_gate_space(self):
            gate = self.gate
            try:
                return gate.min_gate_space
            except AttributeError:
                return gate.poly.min_space

        @property
        def min_sd_width(self):
            gate = self.gate
            return gate.min_sd_width

        @property
        def min_polyactive_extension(self):
            gate = self.gate
            return gate.min_polyactive_extension

    @property
    def computed(self):
        return MOSFETGate._ComputedProps(self)

    def __init__(self, name=None, *, active, poly, oxide=None,
        min_l=None, min_w=None,
        min_sd_width=None, min_polyactive_extension=None, min_gate_space=None,
        contact=None, min_contactgate_space=None,
    ):
        if not isinstance(active, WaferWire):
            raise TypeError("active has to be of type 'WaferWire'")
        self.active = active

        if not isinstance(poly, GateWire):
            raise TypeError("poly has to be of type 'GateWire'")
        self.poly = poly

        prims = (poly, active)
        if oxide is not None:
            if not isinstance(oxide, Insulator):
                raise TypeError("oxide has to be 'None' or of type 'Insulator'")
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
        _MaskPrimitive._generate_rules(self, tech, gen_mask=False)
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
    class _ComputedProps:
        def __init__(self, mosfet):
            self.mosfet = mosfet

        def _lookup(self, name, allow_none):
            mosfet = self.mosfet
            try:
                return getattr(mosfet, name)
            except AttributeError:
                if not allow_none:
                    return getattr(mosfet.gate.computed, name)
                else:
                    return getattr(mosfet.gate, name, None)

        @property
        def min_l(self):
            return self._lookup("min_l", False)

        @property
        def min_w(self):
            return self._lookup("min_w", False)

        @property
        def min_sd_width(self):
            return self._lookup("min_sd_width", False)

        @property
        def min_polyactive_extension(self):
            return self._lookup("min_polyactive_extension", False)

        @property
        def min_gate_space(self):
            return self._lookup("min_gate_space", False)

        @property
        def contact(self):
            return self._lookup("contact", True)

        @property
        def min_contactgate_space(self):
            return self._lookup("min_contactgate_space", True)

    @property
    def computed(self):
        return MOSFET._ComputedProps(self)

    def __init__(
        self, name, *,
        gate, implant, well=None,
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

        implant = tuple(implant) if _util.is_iterable(implant) else (implant,)
        if not all(isinstance(l, Implant) for l in implant):
            raise TypeError("implant has to be 'None', of type 'Implant' or an iterable of type 'Implant'")
        self.implant = implant

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

        min_gateimplant_enclosure = (
            tuple(tuple(
                _util.i2f(v) for v in enc) if _util.is_iterable(enc) else _util.i2f(enc)
                for enc in min_gateimplant_enclosure
            )
            if _util.is_iterable(min_gateimplant_enclosure)
            else (_util.i2f(min_gateimplant_enclosure),)
        )
        if len(implant) == 1 and len(min_gateimplant_enclosure) == 2:
            min_gateimplant_enclosure = (min_gateimplant_enclosure,)
        if len(implant) > 1 and len(min_gateimplant_enclosure) == 1:
            min_gateimplant_enclosure *= len(implant)
        if not all(
            (isinstance(enc, float)
             or (len(enc) == 2 and all(isinstance(v, float) for v in enc))
            ) for enc in min_gateimplant_enclosure
        ):
            raise TypeError(
                "min_gateimplant_enclosure has to be either:\n"
                "* a float\n"
                "* an iterable with same length as implant and with elements eihter:\n"
                "  * a float\n"
                "  * a length 2 iterable of float"
            )
        if len(implant) != len(min_gateimplant_enclosure):
            raise ValueError("length mismatch between min_gateimplant_enclosure and implant")
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

        if model is not None:
            if not isinstance(model, str):
                raise TypeError("model has to be 'None' or a string")
            self.model = model

        # MOSFET is symmetric so both diffusion regions can be source or drain
        bulkport = (
            msk.MaskPort("bulk", well.mask) if well is not None
            else wfr.SubstratePort("bulk")
        )
        self.ports += (
            msk.MaskPort("sourcedrain1", gate.active.mask),
            msk.MaskPort("sourcedrain2", gate.active.mask),
            msk.MaskPort("gate", gate.poly.mask),
            bulkport,
        )

        self.l = _PrimitiveProperty(self, "l")
        self.w = _PrimitiveProperty(self, "w")

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        markers = (self.well.mask if hasattr(self, "well") else tech.substrate,)
        if hasattr(self, "implant"):
            markers += tuple(impl.mask for impl in self.implant)
        markedgate_mask = msk.Intersect((self.gate.mask, *markers)).alias(f"gate:mosfet:{self.name}")
        markedgate_edge = edg.MaskEdge(markedgate_mask)
        poly_mask = self.gate.poly.mask
        poly_edge = edg.MaskEdge(poly_mask)
        channel_edge = edg.Intersect((markedgate_edge, poly_edge))
        active_mask = self.gate.active.mask
        active_edge = edg.MaskEdge(active_mask)
        fieldgate_edge = edg.Intersect((markedgate_edge, active_edge))

        self._rules += (markedgate_mask,)
        if hasattr(self, "min_l"):
            self._rules += (edg.Intersect((markedgate_edge, active_edge)).length >= self.min_l,)
        if hasattr(self, "min_w"):
            self._rules += (edg.Intersect((markedgate_edge, poly_edge)).length >= self.min_w,)
        if hasattr(self, "min_sd_width"):
            self._rules += (active_mask.extend_over(markedgate_mask) >= self.min_sd_width,)
        if hasattr(self, "min_polyactive_extension"):
            self._rules += (poly_mask.extend_over(markedgate_mask) >= self.min_polyactive_extension,)
        for i in range(len(self.implant)):
            impl_mask = self.implant[i].mask
            enc = self.min_gateimplant_enclosure[i]
            if isinstance(enc, float):
                self._rules += (markedgate_mask.enclosed_by(impl_mask) >= enc,)
            else:
                self._rules += (
                    channel_edge.enclosed_by(impl_mask) >= enc[0],
                    fieldgate_edge.enclosed_by(impl_mask) >= enc[1],
                )
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

class Primitives(_util.TypedTuple):
    tt_element_type = _Primitive

class UnusedPrimitiveError(Exception):
    def __init__(self, primitive):
        assert isinstance(primitive, _Primitive)
        super().__init__(
            f"primitive '{primitive.name}' defined but not used"
        )
class UnconnectedPrimitiveError(Exception):
    def __init__(self, primitive):
        assert isinstance(primitive, _Primitive)
        super().__init__(
            f"primitive '{primitive.name}' is not connected"
        )
