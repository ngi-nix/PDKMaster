"""The native technology primitives"""
# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
from textwrap import dedent
from warnings import warn
from itertools import product, combinations, chain
import abc

from .. import _util
from . import (
    rule as rle, property_ as prp, net as net_, mask as msk, wafer_ as wfr,
    edge as edg,
)

__all__ = ["Marker", "Auxiliary", "ExtraProcess",
           "Implant", "Well",
           "Insulator", "WaferWire", "GateWire", "MetalWire", "TopMetalWire",
           "Via", "PadOpening",
           "Resistor", "Diode",
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
        _Primitive._names.add(name)
        self.name = name

        self.ports = _PrimitivePorts()
        self.params = _Params()

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

    def cast_params(self, params):
        casted = {}
        for param in self.params:
            try:
                default = param.default
            except AttributeError:
                try:
                    v = params.pop(param.name)
                except KeyError:
                    if param.allow_none:
                        v = None
                    else:
                        raise ValueError(
                            f"Missing required parameter '{param.name}' for"
                            f" primitive '{self.name}'"
                        )
            else:
                v = params.pop(param.name, default)
            casted[param.name] = param.cast(v)

        if len(self.ports) > 0:
            try:
                portnets = params.pop("portnets")
            except KeyError:
                # Specifying nets is optional
                pass
            else:
                # If nets are specified all nets need to be specified
                portnames = set(p.name for p in self.ports)
                portnetnames = set(portnets.keys())
                if (
                    (portnames != portnetnames)
                    or (len(self.ports) != len(portnets)) # Detect removal of doubles in set
                ):
                    raise ValueError(
                        f"Nets for ports {portnetnames} specified but prim '{self.name}'"
                        f" has ports {portnames}"
                    )
                casted["portnets"] = portnets

        if len(params) > 0:
            raise TypeError(
                f"primitive '{self.name}' got unexpected parameter(s) "
                f"{tuple(params.keys())}"
            )

        return casted

class _Param(prp.Property):
    def __init__(self, primitive, name, *, allow_none=False, default=None):
        if not isinstance(primitive, _Primitive):
            raise RuntimeError("Internal error: primitive not of type 'Primitive'")
        super().__init__(name, allow_none=allow_none)

        if default is not None:
            try:
                default = self.cast(default)
            except TypeError:
                raise TypeError(
                    f"default can't be converted to type '{self.value_type_str}'"
                )
            self.default = default

    def cast(self, value):
        if (value is None) and hasattr(self, "default"):
            return self.default
        else:
            return super().cast(value)

class _IntParam(_Param):
    value_conv = None
    value_type = int
    value_type_str = "int"

class _PrimitiveParam(_Param):
    value_conv = None
    value_type = _Primitive
    value_type_str = "'_Primitive'"

    def __init__(self, primitive, name, *, allow_none=False, default=None, choices=None):
        if choices is not None:
            if not _util.is_iterable(choices):
                raise TypeError(
                    "choices has to be iterable of '_Primitive' objects"
                )
            choices = tuple(choices)
            if not all(isinstance(prim, _Primitive) for prim in choices):
                raise TypeError(
                    "choices has to be iterable of '_Primitive' objects"
                )
            self.choices = choices

        super().__init__(primitive, name, allow_none=allow_none, default=default)

    def cast(self, value):
        value = super().cast(value)
        if hasattr(self, "choices"):
            if not ((value is None) or (value in self.choices)):
                raise ValueError(
                    f"Param '{self.name}' is not one of the allowed values:\n"
                    f"    {self.choices}"
            )

        return value

class _EnclosureParam(_Param):
    value_type_str = "'Enclosure'"

    def cast(self, value):
        if value is None:
            if hasattr(self, "default"):
                value = self.default
            elif not self.allow_none:
                raise TypeError(
                    f"'None' value not allowed for parameter '{self.name}'"
                )
        elif not isinstance(value, prp.Enclosure):
            try:
                value = prp.Enclosure(value)
            except:
                raise TypeError(
                    f"value {repr(value)} can't be converted to an Enclosure object"
                )

        return value

class _EnclosuresParam(_Param):
    value_type_str = "iterable of 'Enclosure'"

    def __init__(self, primitive, name, *, allow_none=False, default=None, n, ):
        if not isinstance(n, int):
            raise TypeError("n has to be an int")
        self.n = n
        super().__init__(primitive, name, allow_none=allow_none, default=default)

    def cast(self, value):
        if value is None:
            if hasattr(self, "default"):
                value = self.default
            elif not self.allow_none:
                raise TypeError(
                    f"'None' value not allowed for parameter '{self.name}'"
                )
        elif not _util.is_iterable(value):
            try:
                value = self.n*(prp.Enclosure(value),)
            except:
                raise TypeError(
                    f"param '{self.name}' has to be an enclosure value or an iterable \n"
                    f"of type 'Enclosure' with length {self.n}"
                )
        else:
            try:
                value = tuple(
                    (None if elem is None
                     else elem if isinstance(elem, prp.Enclosure)
                     else prp.Enclosure(elem)
                    ) for elem in value
                )
            except:
                raise TypeError(
                    f"param '{self.name}' has to be an iterable of enclosure values"
                    f"with length {self.n}"
                )
        return value

class _Params(_util.TypedTuple):
    tt_element_type = _Param

class _PrimitiveNet(net_.Net):
    def __init__(self, prim, name):
        assert all((
            isinstance(prim, _Primitive),
            isinstance(name, str),
        )), "Internal error"

        super().__init__(name)
        self.prim = prim

class _PrimitivePorts(net_.Nets):
    tt_element_type = (_PrimitiveNet, wfr.SubstrateNet)

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

    def _designmask_from_name(self, args, *, fill_space):
        if "mask" in args:
            raise TypeError(
                f"{self.__class__.__name__} got unexpected keyword argument 'mask'",
            )
        args["mask"] = msk.DesignMask(
            args["name"], gds_layer=args.pop("gds_layer", None),
            fill_space=fill_space,
        )

    def _blockage_attribute(self, args):
        blockage = args.pop("blockage", None)
        if blockage is not None:
            if not isinstance(blockage, Marker):
                raise TypeError(
                    f"blockage argument for {self.__class__.__name__} has to None,"
                    " or of type 'Marker',\n"
                    f"not of type '{type(blockage)}'"
                )
            self.blockage = blockage

class Marker(_MaskPrimitive):
    def __init__(self, name, **mask_args):
        mask_args["name"] = name
        self._designmask_from_name(mask_args, fill_space="yes")
        super().__init__(**mask_args)

        self.params += (
            _Param(self, "width", allow_none=True),
            _Param(self, "height", allow_none=True),
        )

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

    @property
    def designmasks(self):
        return super().designmasks

class Auxiliary(_MaskPrimitive):
    # Layer not used in other primitives but defined by foundry for the technology
    def __init__(self, name, **mask_args):
        mask_args["name"] = name
        self._designmask_from_name(mask_args, fill_space="no")
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

        self.params += (
            _Param(self, "width", default=self.min_width),
            _Param(self, "height", default=self.min_width),
        )

    def _pin_attribute(self, args):
        pin = args.pop("pin", None)
        if pin is not None:
            pin = _util.v2t(pin)
            if not all(isinstance(p, Marker) for p in pin):
                raise TypeError(
                    f"pin argument for {self.__class__.__name__} has to None, "
                    "of type 'Marker' or an iterable of type 'Marker'"
                )
            self.pin = pin

    def _pin_params(self):
        if hasattr(self, "pin"):
            self.params += _PrimitiveParam(
                self, "pin", allow_none=True, choices=self.pin,
            )

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
    def __init__(self, name, *, fill_space, **widthspace_args):
        if not isinstance(fill_space, str):
            raise TypeError("fill_space has to be a string")
        if not fill_space in ("no", "yes"):
            raise ValueError("fill_space has to be either 'yes' or 'no'")
        widthspace_args["name"] = name
        self._designmask_from_name(widthspace_args, fill_space=fill_space)
        super().__init__(**widthspace_args)

class Implant(_WidthSpacePrimitive):
    # Implants are supposed to be disjoint unless they are used as combined implant
    # MOSFET and other primitives
    def __init__(self, name, *, type_, **widthspace_args):
        widthspace_args["name"] = name
        self._designmask_from_name(widthspace_args, fill_space="yes")

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

        self.ports += _PrimitiveNet(self, "conn")

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
    def __init__(self, name, *, fill_space, **widthspace_args):
        if not isinstance(fill_space, str):
            raise TypeError("fill_space has to be a string")
        if not fill_space in ("no", "yes"):
            raise ValueError("fill_space has to be either 'yes' or 'no'")
        widthspace_args["name"] = name
        self._designmask_from_name(widthspace_args, fill_space=fill_space)
        super().__init__(**widthspace_args)

class _Conductor(_WidthSpacePrimitive):
    @abc.abstractmethod
    def __init__(self, **widthspace_args):
        super().__init__(**widthspace_args)

        self.ports += _PrimitiveNet(self, "conn")

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        # Generate a mask for connection, thus without resistor parts
        # or ActiveWire without gate etc.
        indicators = chain(*tuple(r.indicator for r in filter(
            lambda p: p.wire == self,
            tech.primitives.tt_iter_type(Resistor),
        )))
        polys = tuple(g.poly for g in filter(
            lambda p: p.active == self,
            tech.primitives.tt_iter_type(MOSFETGate)
        ))
        removes = set(p.mask for p in chain(indicators, polys))

        if removes:
            if len(removes) == 1:
                remmask = removes.pop()
            else:
                remmask = msk.Join(removes)
            self.conn_mask = self.mask.remove(remmask).alias(self.mask.name + "__conn")
            self._rules += (self.conn_mask,)
        else:
            self.conn_mask = self.mask

class WaferWire(_Conductor):
    # The wire made from wafer material and normally isolated by LOCOS for old technlogies
    # and STI for other ones.
    def __init__(self, name, *,
        allow_in_substrate,
        implant, min_implant_enclosure, implant_abut, allow_contactless_implant,
        well, min_well_enclosure, min_substrate_enclosure=None, allow_well_crossing,
        oxide=None, min_oxide_enclosure=None,
        **widthspace_args
    ):
        widthspace_args["name"] = name
        self._designmask_from_name(widthspace_args, fill_space="same_net")

        if not isinstance(allow_in_substrate, bool):
            raise TypeError("allow_in_substrate has to be a bool")
        self.allow_in_substrate = allow_in_substrate

        implant = tuple(implant) if _util.is_iterable(implant) else (implant,)
        if not all(isinstance(impl, Implant) for impl in implant):
            raise TypeError("implant has to be of type 'Implant' that is not a 'Well' or an interable of that")
        self.implant = implant
        min_implant_enclosure = _util.v2t(min_implant_enclosure)
        if not all(isinstance(enc, prp.Enclosure) for enc in min_implant_enclosure):
            raise TypeError(
                "min_implant_enclosure has to be of type 'Enclosure' or an "
                "iterable of type 'Enclosure'"
            )
        if len(min_implant_enclosure) == 1 and len(implant) > 1:
            min_implant_enclosure *= len(implant)
        if len(implant) != len(min_implant_enclosure):
            raise ValueError(
                "mismatch between number of implant and number of min_implant_enclosure"
            )
        self.min_implant_enclosure = min_implant_enclosure
        if isinstance(implant_abut, str):
            _conv = {"all": implant, "none": tuple()}
            if implant_abut not in _conv:
                raise ValueError(
                    "only 'all' or 'none' allowed for a string implant_abut"
                )
            implant_abut = _conv[implant_abut]
        if not all(impl in implant for impl in implant_abut):
            raise ValueError(
                "implant_abut has to be an iterable of 'Implant' that are also in implant"
            )
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
        min_well_enclosure = _util.v2t(min_well_enclosure)
        if not all(isinstance(enc, prp.Enclosure) for enc in min_well_enclosure):
            raise TypeError(
                "min_well_enclosure has to be of type 'Enclosure' or an "
                "iterable of type 'Enclosure'"
            )
        if len(min_well_enclosure) == 1 and len(well) > 1:
            min_well_enclosure *= len(well)
        if len(well) != len(min_well_enclosure):
            raise ValueError(
                "mismatch between number of well and number of min_well_enclosure"
            )
        self.min_well_enclosure = min_well_enclosure
        if allow_in_substrate:
            if min_substrate_enclosure is None:
                if len(min_well_enclosure) == 1:
                    min_substrate_enclosure = min_well_enclosure[0]
                else:
                    raise TypeError(
                        "min_substrate_enclosure has be provided when providing multi min_well_enclosure values"
                    )
            if not isinstance(min_substrate_enclosure, prp.Enclosure):
                raise TypeError(
                    "min_substrate_enclosure has to be 'None' or of type 'Enclosure'"
                )
            self.min_substrate_enclosure = min_substrate_enclosure
        elif min_substrate_enclosure is not None:
            raise TypeError(
                "min_substrate_enclosure should be 'None' if allow_in_substrate is 'False'"
            )
        if not isinstance(allow_well_crossing, bool):
            raise TypeError("allow_well_crossing has to be a bool")
        self.allow_well_crossing = allow_well_crossing

        if oxide is not None:
            oxide = _util.v2t(oxide)
            if not all(isinstance(o, Insulator) for o in oxide):
                raise TypeError(
                    "oxide has to be 'None', of type 'Insulator' or "
                    "an iterable of type 'Insulator'"
                )
            self.oxide = oxide

            min_oxide_enclosure = _util.v2t(min_oxide_enclosure, n=len(oxide))
            if not all(
                (enc is None) or isinstance(enc, prp.Enclosure)
                for enc in min_oxide_enclosure
            ):
                raise TypeError(
                    "min_oxide_enclosure has to be 'None', of type 'Enclosure'\n"
                    "or an iterable of 'None' and type 'Enclosure'"
                )
            self.min_oxide_enclosure = min_oxide_enclosure
        elif min_oxide_enclosure is not None:
            raise ValueError("min_oxide_enclosure provided with no oxide given")

        self._pin_attribute(widthspace_args)
        self._blockage_attribute(widthspace_args)
        super().__init__(**widthspace_args)
        self._pin_params()

        if len(implant) > 1:
            self.params += (
                _PrimitiveParam(self, "implant", choices=self.implant),
                _EnclosureParam(self, "implant_enclosure", allow_none=True),
            )
        else:
            self.params += (
                _EnclosureParam(
                    self, "implant_enclosure",
                    default=min_implant_enclosure[0],
                ),
            )
        if (len(well) > 1) or allow_in_substrate:
            self.params += (
                _PrimitiveParam(
                    self, "well", allow_none=allow_in_substrate,
                    choices=self.well
                ),
                _EnclosureParam(self, "well_enclosure", allow_none=True),
            )
        else:
            self.params += (
                _EnclosureParam(
                    self, "well_enclosure", default=min_well_enclosure[0],
                ),
            )
        if hasattr(self, "oxide"):
            self.params += (
                _PrimitiveParam(self, "oxide", choices=self.oxide, allow_none=True),
                _EnclosureParam(self, "oxide_enclosure", allow_none=True),
            )

    def cast_params(self, params):
        well_net = params.pop("well_net", None)
        params = super().cast_params(params)

        def _check_param(name):
            return (name in params) and (params[name] is not None)

        if "implant" in params:
            implant = params["implant"]
        else:
            params["implant"] = implant = self.implant[0]
        if params["implant_enclosure"] is None:
            idx = self.implant.index(implant)
            params["implant_enclosure"] = self.min_implant_enclosure[idx]

        if "well" in params:
            well = params["well"]
            if (well is not None) and (params["well_enclosure"] is None):
                idx = self.well.index(well)
                params["well_enclosure"] = self.min_well_enclosure[idx]
        elif (len(self.well) == 1) and (not self.allow_in_substrate):
            params["well"] = well = self.well[0]
        else:
            well = None
        if well is not None:
            if well_net is None:
                raise TypeError(
                    f"No well net specified for primitive '{self.name}' in a well"
                )
            params["well_net"] = well_net
        elif well_net is not None:
            raise TypeError(
                f"Well net specified for primitive '{self.name}' not in a well"
            )

        if ("oxide" in params):
            oxide = params["oxide"]
            if oxide is not None:
                oxide_enclosure = params["oxide_enclosure"]
                if oxide_enclosure is None:
                    idx = self.oxide.index(oxide)
                    params["oxide_enclosure"] = self.min_oxide_enclosure[idx]

        return params

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        for i, impl in enumerate(self.implant):
            sd_mask_impl = msk.Intersect((self.conn_mask, impl.mask)).alias(
                f"{self.conn_mask.name}:{impl.name}",
            )
            self._rules += (sd_mask_impl, msk.Connect(self.conn_mask, sd_mask_impl))
            if self.allow_in_substrate and (impl.type_ == tech.substrate_type):
                self._rules += (msk.Connect(sd_mask_impl, tech.substrate),)
            if impl not in self.implant_abut:
                self._rules += (edg.MaskEdge(impl.mask).interact_with(self.mask).length == 0,)
            enc = self.min_implant_enclosure[i]
            self._rules += (self.mask.enclosed_by(impl.mask) >= enc,)
            for w in self.well:
                if impl.type_ == w.type_:
                    self._rules += (msk.Connect(sd_mask_impl, w.mask),)
        for implduo in combinations((impl.mask for impl in self.implant_abut), 2):
            self._rules += (msk.Intersect(implduo).area == 0,)
        # TODO: allow_contactless_implant
        for i, w in enumerate(self.well):
            enc = self.min_well_enclosure[i]
            self._rules += (self.mask.enclosed_by(w.mask) >= enc,)
        if hasattr(self, "min_substrate_enclosure"):
            self._rules += (
                self.mask.enclosed_by(tech.substrate) >= self.min_substrate_enclosure,
            )
        if not self.allow_well_crossing:
            mask_edge = edg.MaskEdge(self.mask)
            self._rules += tuple(
                mask_edge.interact_with(edg.MaskEdge(w.mask)).length == 0
                for w in self.well
            )

class GateWire(_Conductor):
    def __init__(self, name, **widthspace_args):
        widthspace_args["name"] = name
        self._designmask_from_name(widthspace_args, fill_space="same_net")
        self._pin_attribute(widthspace_args)
        self._blockage_attribute(widthspace_args)
        super().__init__(**widthspace_args)
        self._pin_params()

class MetalWire(_Conductor):
    def __init__(self, name, **widthspace_args):
        widthspace_args["name"] = name
        self._designmask_from_name(widthspace_args, fill_space="same_net")
        self._pin_attribute(widthspace_args)
        self._blockage_attribute(widthspace_args)
        super().__init__(**widthspace_args)
        self._pin_params()

class TopMetalWire(MetalWire):
    pass

class Via(_MaskPrimitive):
    def __init__(self, name, *,
        bottom, top,
        width, min_space, min_bottom_enclosure, min_top_enclosure,
        **primitive_args,
    ):
        primitive_args["name"] = name
        self._designmask_from_name(primitive_args, fill_space="no")
        self._blockage_attribute(primitive_args)
        super().__init__(**primitive_args)

        self.ports += _PrimitiveNet(self, "conn")

        bottom = _util.v2t(bottom)
        min_bottom_enclosure = _util.v2t(min_bottom_enclosure)
        if len(min_bottom_enclosure) == 1:
            min_bottom_enclosure *= len(bottom)
        if ((not all(isinstance(enc, prp.Enclosure) for enc in min_bottom_enclosure))
            or (len(bottom) != len(min_bottom_enclosure))
        ):
            raise ValueError(
                "min_bottom_enclosure has to of type 'Enclosure' or an "
                "iterable of type 'Enclosure'\n"
                "with same length as the bottom parameter"
            )
        if not all((
            isinstance(wire, (WaferWire, GateWire, MetalWire, Resistor))
            and not isinstance(wire, TopMetalWire)
        ) for wire in bottom):
                raise TypeError(
                    "bottom has to be of type '(Wafer|Gate|Metal)Wire' or 'Resistor'\n"
                    "or an iterable of those"
                )
        self.bottom = bottom
        self.min_bottom_enclosure = min_bottom_enclosure

        top = _util.v2t(top)
        min_top_enclosure = _util.v2t(min_top_enclosure)
        if len(min_top_enclosure) == 1:
            min_top_enclosure *= len(top)
        if ((not all(isinstance(enc, prp.Enclosure) for enc in min_top_enclosure))
            or (len(top) != len(min_top_enclosure))
        ):
            raise ValueError(
                "min_top_enclosure has to of type 'Enclosure' or an "
                "iterable of type 'Enclosure'\n"
                "with same length as the top parameter"
            )
        if not all(isinstance(wire, (MetalWire, Resistor)) for wire in top):
                raise TypeError(
                    "top has to be of type 'MetalWire' or 'Resistor'\n"
                    "or an iterable of those"
                )
        self.top = top
        self.min_top_enclosure = min_top_enclosure
        
        width = _util.i2f(width)
        if not isinstance(width, float):
            raise TypeError("width has to be a float")
        self.width = width

        min_space = _util.i2f(min_space)
        if not isinstance(min_space, float):
            raise TypeError("min_space has to be a float")
        self.min_space = min_space

        self.params += (
            _Param(self, "space", default=min_space),
            _IntParam(self, "rows", allow_none=True),
            _IntParam(self, "columns", allow_none=True),
            _EnclosureParam(self, "bottom_enclosure", allow_none=True),
            _Param(self, "bottom_width", allow_none=True),
            _Param(self, "bottom_height", allow_none=True),
            _EnclosureParam(self, "top_enclosure", allow_none=True),
            _Param(self, "top_width", allow_none=True),
            _Param(self, "top_height", allow_none=True),
        )
        if len(bottom) > 1:
            self.params += _PrimitiveParam(self, "bottom", choices=bottom)
        choices = sum(
            (wire.implant for wire in filter(
                lambda w: isinstance(w, WaferWire),
                bottom,
            )),
            tuple(),
        )
        if choices:
            self.params += (
                _PrimitiveParam(
                    self, "bottom_implant", allow_none=True, choices=choices,
                ),
                _EnclosureParam(
                    self, "bottom_implant_enclosure", allow_none=True,
                ),
                _PrimitiveParam(self, "bottom_well", allow_none=True),
                _EnclosureParam(self, "bottom_well_enclosure", allow_none=True),
            )
        if len(top) > 1:
            self.params += _PrimitiveParam(self, "top", choices=top)

    def cast_params(self, params):
        well_net = params.pop("well_net", None)
        params = super().cast_params(params)

        def _check_param(name):
            return (name in params) and (params[name] is not None)

        has_bottom = _check_param("bottom")
        # has_bottom_enclosure = _check_param("bottom_enclosure")
        has_bottom_implant = _check_param("bottom_implant")
        has_bottom_implant_enclosure = _check_param("bottom_implant_enclosure")
        has_bottom_well = _check_param("bottom_well")
        has_bottom_well_enclosure = _check_param("bottom_well_enclosure")
        has_bottom_width = _check_param("bottom_width")
        has_bottom_height = _check_param("bottom_height")

        has_top = _check_param("top")

        has_rows = _check_param("rows")
        has_columns = _check_param("columns")
        has_top_width = _check_param("top_width")
        has_top_height = _check_param("top_height")

        if has_bottom:
            bottom = params["bottom"]
        else:
            bottom = params["bottom"] = self.bottom[0]
        if bottom not in self.bottom:
            raise ValueError(
                f"bottom primitive '{bottom.name}' not valid for via '{self.name}'"
            )
        if isinstance(bottom, WaferWire):
            impl = params["bottom_implant"]
            if impl is None:
                raise ValueError(
                    "bottom_implant parameter not provided for use of\n"
                    f"bottom '{bottom.name}' for via '{self.name}'"
                )
            elif impl not in bottom.implant:
                raise ValueError(
                    f"bottom_implant '{impl.name}' not a valid implant for "
                    f"bottom wire '{bottom.name}'"
                )

            if not has_bottom_implant_enclosure:
                idx = bottom.implant.index(impl)
                params["bottom_implant_enclosure"] = bottom.min_implant_enclosure[idx]

            if has_bottom_well:
                bottom_well = params["bottom_well"]
                if bottom_well not in bottom.well:
                    raise ValueError(
                        f"bottom_well '{bottom_well.name}' not a valid well for "
                        f"bottom wire '{bottom.name}'"
                    )
                if not has_bottom_well_enclosure:
                    idx = bottom.well.index(bottom_well)
                    params["bottom_well_enclosure"] = (
                        bottom.min_well_enclosure[idx]
                    )
                params["well_net"] = well_net
            elif not bottom.allow_in_substrate:
                raise ValueError(
                    f"bottom wire '{bottom.name}' needs a well"
                )
        elif has_bottom_implant:
            bottom_implant = params["bottom_implant"]
            raise ValueError(
                f"bottom_implant '{bottom_implant.name}' not a valid implant for "
                f"bottom wire '{bottom.name}'"
            )
        elif has_bottom_implant_enclosure:
            raise TypeError(
                "bottom_implant_enclosure wrongly provided for bottom wire "
                f"'{bottom.name}'"
            )
        elif has_bottom_well:
            bottom_well = params["bottom_well"]
            raise ValueError(
                f"bottom_well '{bottom_well.name}' not a valid well for "
                f"bottom wire '{bottom.name}'"
            )
        elif has_bottom_well_enclosure:
            raise TypeError(
                "bottom_well_enclosure wrongly provided for bottom wire "
                f"'{bottom.name}'"
            )

        if has_top:
            top = params["top"]
        else:
            top = params["top"] = self.top[0]
        if top not in self.top:
            raise ValueError(
                f"top primitive '{top.name}' not valid for via '{self.name}'"
            )

        if not any((has_rows, has_bottom_height, has_top_height)):
            params["rows"] = 1

        if not any((has_columns, has_bottom_width, has_top_width)):
            params["columns"] = 1

        return params

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        self._rules += (
            self.mask.width == self.width,
            self.mask.space >= self.min_space,
            msk.Connect((b.conn_mask for b in self.bottom), self.mask),
            msk.Connect(self.mask, (b.conn_mask for b in self.top)),
        )
        for i in range(len(self.bottom)):
            bot_mask = self.bottom[i].mask
            enc = self.min_bottom_enclosure[i]
            self._rules += (self.mask.enclosed_by(bot_mask) >= enc,)
        for i in range(len(self.top)):
            top_mask = self.top[i].mask
            enc = self.min_top_enclosure[i]
            self._rules += (self.mask.enclosed_by(top_mask) >= enc,)

    @property
    def designmasks(self):
        for mask in super().designmasks:
            yield mask
        for conn in self.bottom + self.top:
            for mask in conn.designmasks:
                yield mask

class PadOpening(_Conductor):
    def __init__(self, name, *, bottom, min_bottom_enclosure, **widthspace_args):
        widthspace_args["name"] = name
        self._designmask_from_name(widthspace_args, fill_space="no")
        super().__init__(**widthspace_args)

        if not (isinstance(bottom, MetalWire) and not isinstance(bottom, TopMetalWire)):
            raise TypeError("bottom has to be of type 'MetalWire'")
        self.bottom = bottom
        if not isinstance(min_bottom_enclosure, prp.Enclosure):
            raise TypeError("min_bottom_enclosure has to be of type 'Enclosure'")
        self.min_bottom_enclosure = min_bottom_enclosure

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        self._rules += (
            self.mask.enclosed_by(self.bottom.mask) >= self.min_bottom_enclosure,
        )

    @property
    def designmasks(self):
        for mask in super().designmasks:
            yield mask
        yield self.bottom.mask

class Resistor(_WidthSpacePrimitive):
    def __init__(self, name, *,
        wire, contact=None, min_contact_space=None, indicator, min_indicator_extension,
        implant=None, min_implant_enclosure=None,
        model=None, model_params=None, sheetres=None, **widthspace_args,
    ):
        # If both model and sheetres are specified, sheetres will be used for
        # LVS circuit generation in pyspice export.
        if not isinstance(wire, (WaferWire, GateWire, MetalWire)):
            raise TypeError(
                "wire has to be of type '(Wafer|Gate|Metal)Wire'"
            )
        self.wire = wire

        indicator = _util.v2t(indicator)
        if not all(isinstance(prim, (Marker, ExtraProcess)) for prim in indicator):
            raise TypeError(
                "indicator has to be of type 'Marker' or 'ExtraProcess' "
                "or an iterable of those"
            )
        self.indicator = indicator

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

        min_indicator_extension = _util.v2t(_util.i2f_recursive(min_indicator_extension))
        if not all(isinstance(enc, float) for enc in min_indicator_extension):
            raise TypeError(
                "min_indicator_extension has to be a float or an iterable of floats"
            )
        if len(min_indicator_extension) == 1:
            min_indicator_extension = len(indicator)*min_indicator_extension
        if len(min_indicator_extension) != len(indicator):
            raise ValueError("mismatch in number of indicator and min_indicator_extension")
        self.min_indicator_extension = min_indicator_extension

        if implant is not None:
            if not isinstance(implant, Implant) and not isinstance(implant, Well):
                raise TypeError(
                    "implant has to be 'None' or of type 'Implant'"
                )
            if isinstance(wire, WaferWire):
                if not implant in wire.implant:
                    raise ValueError(
                        f"implant '{implant.name}' is not valid for waferwire '{wire.name}'"
                    )
            self.implant = implant
            if min_implant_enclosure is not None:
                if not isinstance(min_implant_enclosure, prp.Enclosure):
                    raise TypeError(
                        "min_implant_enclosure has to be 'None' or of type 'Enclosure'"
                    )
                self.min_implant_enclosure = min_implant_enclosure
            elif not isinstance(wire, WaferWire):
                raise TypeError(
                    "min_implant_enclosure may not be 'None' for wire type other than"
                    " 'WaferWire'"
                )
        elif min_implant_enclosure is not None:
            raise TypeError(
                "min_implant_enclosure has to be 'None' if no implant is given"
            )

        if "mask" in widthspace_args:
            raise TypeError("Resistor got an unexpected keyword argument 'mask'")
        else:
            prims = (wire, *indicator)
            if implant:
                prims += (implant,)
            widthspace_args["mask"] = msk.Intersect(prim.mask for prim in prims).alias(
                f"resistor:{name}"
            )

        widthspace_args["name"] = name
        super().__init__(**widthspace_args)

        self.ports += (_PrimitiveNet(self, name) for name in ("port1", "port2"))

        if contact is not None:
            if not isinstance(contact, Via):
                raise TypeError("contact has to be 'None' or of type 'Via'")
            if wire not in (contact.bottom + contact.top):
                raise ValueError(
                    f"wire {wire.name} does not connect to via {contact.name}"
                )
            min_contact_space = _util.i2f(min_contact_space)
            if not isinstance(min_contact_space, float):
                raise TypeError(
                    "min_contact_space has to be a float"
                )
            self.contact = contact
            self.min_contact_space = min_contact_space
        elif min_contact_space is not None:
            raise TypeError(
                "min_contact_space has to be 'None' if no contact layer is given"
            )

        if (model is None) and (sheetres is None):
            raise TypeError(
                "Either model or sheetres has to be not 'None'"
            )

        if model is not None:
            if not isinstance(model, str):
                raise TypeError("model has to be 'None' or a string")
            self.model = model
            if not isinstance(model_params, dict):
                raise TypeError(
                    "model_params has to be a dict with keys ('width', 'height')"
                )
            if not (set(model_params.keys()) == {"width", "height"}):
                raise ValueError(
                    "model_params has to be a dict with keys ('width', 'height')"
                )
            self.model_params = model_params
        elif model_params is not None:
            raise TypeError("model_params provided without a model")

        sheetres = _util.i2f(sheetres)
        if sheetres is not None:
            if not isinstance(sheetres, float):
                raise ValueError(
                    f"sheetres has to be None or a float, not type {type(sheetres)}"
                )
            self.sheetres = sheetres

    def _generate_rules(self, tech):
        # Do not generate the default width/space rules.
        _Primitive._generate_rules(self, tech)

        self._rules += (self.mask,)
        if self.min_width > self.wire.min_width:
            self._rules += (self.mask.width >= self.min_width,)
        if self.min_space > self.wire.min_space:
            self._rules += (self.mask.space >= self.min_space,)
        if hasattr(self, "min_area"):
            if (not hasattr(self.wire, "min_area")) or (self.min_area > self.wire.min_area):
                self._rules += (self.mask.area >= self.min_area,)
        for i, ind in enumerate(self.indicator):
            ext = self.min_indicator_extension[i]
            mask = self.wire.mask.remove(ind.mask)
            self._rules += (mask.width >= ext,)

class Diode(_WidthSpacePrimitive):
    def __init__(self, name=None, *,
        wire, indicator, min_indicator_enclosure=None,
        implant, min_implant_enclosure=None,
        well=None, min_well_enclosure=None,
        model=None, **widthspace_args,
    ):
        if not isinstance(wire, WaferWire):
            raise TypeError(
                "wire has to be of type 'WaferWire'"
            )
        self.wire = wire

        indicator = _util.v2t(indicator)
        if not all(isinstance(prim, (Marker, ExtraProcess)) for prim in indicator):
            raise TypeError(
                "indicator has to be of type 'Marker' or 'ExtraProcess' "
                "or an iterable of those"
            )
        self.indicator = indicator

        if "mask" in widthspace_args:
            raise TypeError("Resistor got an unexpected keyword argument 'mask'")
        else:
            widthspace_args["mask"] = msk.Intersect(
                prim.mask for prim in (wire, *indicator)
            )

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

        self.ports += (_PrimitiveNet(self, name) for name in ("anode", "cathode"))

        min_indicator_enclosure = _util.v2t(min_indicator_enclosure)
        if not all(isinstance(enc, prp.Enclosure) for enc in min_indicator_enclosure):
            raise TypeError(
                "min_indicator_enclosure has to be of type 'Enclosure'"
                " or an iterable of those"
            )
        if len(min_indicator_enclosure) == 1:
            min_indicator_enclosure *= len(indicator)
        if len(min_indicator_enclosure) != len(indicator):
            raise ValueError(
                "mismatch in number of indicators and min_indicator_enclosures"
            )
        self.min_indicator_enclosure = min_indicator_enclosure

        if not isinstance(implant, Implant) and not isinstance(implant, Well):
            raise TypeError("implant has to be of type 'Implant'")
        if not implant in wire.implant:
            raise ValueError(
                f"implant '{implant.name}' is not valid for waferwire '{wire.name}'"
            )
        self.implant = implant
        if min_implant_enclosure is not None:
            if not isinstance(min_implant_enclosure, prp.Enclosure):
                raise TypeError(
                    "min_implant_enclosure has to be 'None' or of type 'Enclosure'"
                )
            self.min_implant_enclosure = min_implant_enclosure

        if well is None:
            if not wire.allow_in_substrate:
                raise TypeError(f"wire '{wire.name}' has to be in a well")
            # TODO: check types of substrate and implant
            if min_well_enclosure is not None:
                raise TypeError("min_well_enclosure given without a well")
        else:
            if not isinstance(well, Well):
                raise TypeError("well has to be of type 'Well'")
            if well not in wire.well:
                raise ValueError(
                    f"well '{well.name}' is not a valid well for wire '{wire.name}'"
                )
            if well.type_ == implant.type_:
                raise ValueError(
                    f"type of implant '{implant.name}' may not be the same as"
                    " type of well '{well.name}' for a diode"
                )
            self.well = well

        if model is not None:
            if not isinstance(model, str):
                raise TypeError("model has to be 'None' or a string")
            self.model = model

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

    def __init__(self, name=None, *, active, poly, oxide=None, inside=None,
        min_l=None, min_w=None,
        min_sd_width=None, min_polyactive_extension=None, min_gate_space=None,
        contact=None, min_contactgate_space=None,
        min_gateoxide_enclosure=None, min_gateinside_enclosure=None,
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
            if not hasattr(active, "oxide") or (oxide not in active.oxide):
                raise ValueError(
                    f"oxide '{oxide.name}' is not valid for active '{active.name}'"
                )
            self.oxide = oxide
            prims += (oxide,)
            if min_gateoxide_enclosure is not None:
                if not isinstance(min_gateoxide_enclosure, prp.Enclosure):
                    raise TypeError(
                        "min_gateoxide_enclosure has to be None or of type 'Enclosure'"
                    )
                self.min_gateoxide_enclosure = min_gateoxide_enclosure
        elif min_gateoxide_enclosure is not None:
            raise TypeError("min_gateoxide_enclosure provided without an oxide")

        if inside is not None:
            inside = _util.v2t(inside)
            if not all(isinstance(l, Marker) for l in inside):
                raise TypeError(
                    "inside has to be 'None', of type 'Marker' or "
                    "an iterable of type 'Marker'"
                )
            self.inside = inside
            prims += inside
            if min_gateinside_enclosure is not None:
                min_gateinside_enclosure = _util.v2t(min_gateinside_enclosure)
                if len(min_gateinside_enclosure) == 1:
                    min_gateinside_enclosure *= len(inside)
                if not all(isinstance(enc, prp.Enclosure) for enc in min_gateinside_enclosure):
                    raise TypeError(
                        "min_gateinside_enclosure has to be None of type 'Enclosure' "
                        "or an iterable of type 'Enclosure'"
                    )
                self.min_gateinside_enclosure = min_gateinside_enclosure
        elif min_gateinside_enclosure is not None:
            raise TypeError("min_gateinside_enclosure provided without inside provided")

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
        poly_mask = self.poly.conn_mask

        # Update mask if it has no oxide
        extra_masks = tuple()
        if not hasattr(self, "oxide"):
            extra_masks += tuple(
                gate.oxide.mask for gate in filter(
                    lambda prim: (
                        isinstance(prim, MOSFETGate)
                        and prim.active == self.active
                        and prim.poly == self.poly
                        and hasattr(prim, "oxide")
                    ), tech.primitives,
                )
            )
        if not hasattr(self, "inside"):
            def get_key(gate):
                if hasattr(gate, "oxide"):
                    return frozenset((gate.active, gate.poly, gate.oxide))
                else:
                    return frozenset((gate.active, gate.poly))

            for gate in filter(
                lambda prim: (
                    isinstance(prim, MOSFETGate)
                    and (get_key(prim) == get_key(self))
                    and hasattr(prim, "inside")
                ), tech.primitives,
            ):
                extra_masks += tuple(inside.mask for inside in gate.inside)
        masks = (active_mask, poly_mask)
        if hasattr(self, "oxide"):
            masks += (self.oxide.mask,)
        if hasattr(self, "inside"):
            masks += tuple(inside.mask for inside in self.inside)
        if extra_masks:
            masks += (wfr.outside(extra_masks),)
        # Keep the alias but change the mask of the alias
        self.mask.mask = msk.Intersect(masks)
        mask = self.mask

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
            # This rule has to be put before the other rules that use the alias
            self._rules = (mask,) + self._rules

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
            if min_l <= gate.computed.min_l:
                raise ValueError("min_l has to be bigger than gate min_l if not 'None'")
            self.min_l = min_l

        if min_w is not None:
            min_w = _util.i2f(min_w)
            if not isinstance(min_w, float):
                raise TypeError("min_w has to be 'None' or a float")
            if min_w <= gate.computed.min_w:
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

        min_gateimplant_enclosure = _util.v2t(min_gateimplant_enclosure)
        if len(min_gateimplant_enclosure) == 1:
            min_gateimplant_enclosure *= len(implant)
        if not (
            all(isinstance(enc, prp.Enclosure) for enc in min_gateimplant_enclosure)
            and len(implant) == len(min_gateimplant_enclosure)
        ):
            raise TypeError(
                "min_gateimplant_enclosure has to be of type 'Enclosure' or an "
                "iterable of type 'Enclosure'\n"
                "with same length as the implant parameter"
            )
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
        bulknet = (
            _PrimitiveNet(self, "bulk") if well is not None
            else wfr.SubstrateNet("bulk")
        )
        self.ports += (
            _PrimitiveNet(self, "sourcedrain1"),
            _PrimitiveNet(self, "sourcedrain2"),
            _PrimitiveNet(self, "gate"),
            bulknet,
        )

        for impl in implant:
            try:
                idx = gate.active.implant.index(impl)
            except:
                continue
            else:
                impl_act_enc = gate.active.min_implant_enclosure[idx]
                break
        else:
            raise AssertionError("Internal error")

        self.params += (
            _Param(self, "l", default=self.computed.min_l),
            _Param(self, "w", default=self.computed.min_w),
            _EnclosureParam(
                self, "activeimplant_enclosure",
                default=impl_act_enc,
            ),
            _Param(self, "sd_width", default=self.computed.min_sd_width),
            _Param(
                self, "polyactive_extension",
                default=self.computed.min_polyactive_extension,
            ),
            _EnclosuresParam(
                self, "gateimplant_enclosures", n=len(implant),
                default=min_gateimplant_enclosure,
            ),
        )

        spc = self.computed.min_gate_space
        if spc is not None:
            self.params += _Param(self, "gate_space", default=spc)
        spc = self.computed.min_contactgate_space
        if spc is not None:
            self.params += _Param(self, "contactgate_space", default=spc)

    @property
    def gate_mask(self):
        return self._gate_mask

    def _generate_rules(self, tech):
        super()._generate_rules(tech)

        markers = (self.well.mask if hasattr(self, "well") else tech.substrate,)
        if hasattr(self, "implant"):
            markers += tuple(impl.mask for impl in self.implant)
        derivedgate_mask = msk.Intersect((self.gate.mask, *markers)).alias(
            f"gate:mosfet:{self.name}",
        )
        self._gate_mask = derivedgate_mask
        derivedgate_edge = edg.MaskEdge(derivedgate_mask)
        poly_mask = self.gate.poly.mask
        poly_edge = edg.MaskEdge(poly_mask)
        channel_edge = edg.Intersect((derivedgate_edge, poly_edge))
        active_mask = self.gate.active.mask
        active_edge = edg.MaskEdge(active_mask)
        fieldgate_edge = edg.Intersect((derivedgate_edge, active_edge))

        self._rules += (derivedgate_mask,)
        if hasattr(self, "min_l"):
            self._rules += (
                edg.Intersect((derivedgate_edge, active_edge)).length >= self.min_l,
            )
        if hasattr(self, "min_w"):
            self._rules += (
                edg.Intersect((derivedgate_edge, poly_edge)).length >= self.min_w,
            )
        if hasattr(self, "min_sd_width"):
            self._rules += (
                active_mask.extend_over(derivedgate_mask) >= self.min_sd_width,
            )
        if hasattr(self, "min_polyactive_extension"):
            self._rules += (
                poly_mask.extend_over(derivedgate_mask) >= self.min_polyactive_extension,
            )
        for i in range(len(self.implant)):
            impl_mask = self.implant[i].mask
            enc = self.min_gateimplant_enclosure[i]
            if isinstance(enc.spec, float):
                self._rules += (derivedgate_mask.enclosed_by(impl_mask) >= enc,)
            else:
                self._rules += (
                    channel_edge.enclosed_by(impl_mask) >= enc.spec[0],
                    fieldgate_edge.enclosed_by(impl_mask) >= enc.spec[1],
                )
        if hasattr(self, "min_gate_space"):
            self._rules += (derivedgate_mask.space >= self.min_gate_space,)
        if hasattr(self, "min_contactgate_space"):
            self.rules += (msk.Spacing(derivedgate_mask, self.contact.mask) >= self.min_contactgate_space,)

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
