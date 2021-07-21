"""The native technology primitives"""
# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
from itertools import product, combinations, chain
import abc
from typing import (
    Any, Generator, Iterable, Optional, List, Set, Dict, Tuple, Union, cast,
)

from ..typing import SingleOrMulti, OptSingleOrMulti, IntFloat
from .. import _util
from . import (
    rule as rle, property_ as prp, net as net_, mask as msk, wafer_ as wfr,
    edge as edg, technology_ as tch,
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
    @abc.abstractmethod
    def __init__(self, *, name: str):
        self.name = name

        self.ports = _PrimitivePorts()
        self.params = _Params()

        self._rules: Optional[Tuple[rle._Rule, ...]] = None

    def __repr__(self):
        cname = self.__class__.__name__.split(".")[-1]
        return f"{cname}({self.name})"

    def __eq__(self, other: object) -> bool:
        """Two primitives are the same if their name is the same"""
        return (isinstance(other, _Primitive)) and (self.name == other.name)

    def __hash__(self):
        return hash(self.name)

    @property
    def rules(self) -> Tuple[rle._Rule, ...]:
        if self._rules is None:
            raise AttributeError("Accessing rules before they are generated")
        return self._rules

    @abc.abstractmethod
    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Iterable[rle._Rule]:
        return tuple()

    def _derive_rules(self, tech: tch.Technology) -> None:
        if self._rules is not None:
            raise ValueError("Rules can only be generated once")
        self._rules = tuple(self._generate_rules(tech))

    @abc.abstractproperty
    def designmasks(self) -> Iterable[msk.DesignMask]:
        return tuple()

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


class _DerivedPrimitive(_Primitive):
    """A primitive that is derived from other primitives and not a
    Primitive that can be part of the primitive list of a technology.
    """
    def _generate_rules(self, tech: tch.Technology) -> Tuple[rle._Rule, ...]:
        """As _DerivedPrimitive will not be added to the list of primitives
        of a technology node, it does not need to generate rules.
        """
        raise RuntimeError("Internal error")


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


class _Params(_util.TypedListStrMapping[_Param]):
    _elem_type_ = _Param


class _PrimitiveNet(net_.Net):
    def __init__(self, prim, name):
        assert all((
            isinstance(prim, _Primitive),
            isinstance(name, str),
        )), "Internal error"

        super().__init__(name)
        self.prim = prim


class _PrimitivePorts(
    _util.IterableOverride[Union[_PrimitiveNet, wfr.SubstrateNet]],
    net_.Nets,
):
    _elem_type_ = (_PrimitiveNet, wfr.SubstrateNet)


class _MaskPrimitive(_Primitive):
    @abc.abstractmethod
    def __init__(self, *,
        name: Optional[str]=None, mask: msk._Mask, grid: Optional[IntFloat]=None,
        **primitive_args,
    ):
        if name is None:
            name = mask.name
        super().__init__(name=name, **primitive_args)

        self.mask = mask

        if grid is not None:
            grid = _util.i2f(grid)
        self.grid = grid

    @abc.abstractmethod
    def _generate_rules(self,
        tech: tch.Technology, *, gen_mask: bool=True,
    ) -> Generator[rle._Rule, None, None]:
        yield from super()._generate_rules(tech)

        if gen_mask and isinstance(self.mask, rle._Rule):
            yield cast(rle._Rule, self.mask)
        if self.grid is not None:
            yield cast(msk.DesignMask, self.mask).grid == self.grid

    @property
    def designmasks(self):
        return self.mask.designmasks


class _DesignMaskPrimitive(_MaskPrimitive):
    @property
    @abc.abstractmethod
    def fill_space(self) -> str:
        raise RuntimeError("Unimplemented abstract property")

    @abc.abstractmethod
    def __init__(self, *,
        name: str, gds_layer: OptSingleOrMulti[int].T=None,
        **super_args,
    ):
        if "mask" in super_args:
            raise TypeError(
                f"{self.__class__.__name__} got unexpected keyword argument 'mask'",
            )
        mask = msk.DesignMask(
            name=name, gds_layer=gds_layer, fill_space=self.fill_space,
        )
        super().__init__(name=name, mask=mask, **super_args)


class _BlockageAttribute(_Primitive):
    """Mixin class for primitives with a blockage attribute"""
    def __init__(self, blockage: Optional["Marker"]=None, **super_args):
        self.blockage = blockage
        super().__init__(**super_args)


class _PinAttribute(_Primitive):
    """Mixin class for primitives with a pin attribute"""
    def __init__(self,
        pin: OptSingleOrMulti["Marker"].T=None,
        **super_args,
    ):
        if pin is not None:
            pin = _util.v2t(pin)
        self.pin = pin
        super().__init__(**super_args)
        if pin is not None:
            self.params += _PrimitiveParam(
                self, "pin", allow_none=True, choices=self.pin,
            )


class _Intersect(_MaskPrimitive):
    """A primitive representing the overlap of a list of primitives"""
    def __init__(self, *, prims: Iterable[_MaskPrimitive]):
        prims2: Tuple[_MaskPrimitive, ...] = _util.v2t(prims)
        if len(prims2) < 2:
            raise ValueError(f"At least two prims needed for '{self.__class__.__name__}'")
        self.prims = prims2

        mask = msk.Intersect((p.mask for p in prims2))
        _MaskPrimitive.__init__(self, mask=mask)

    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Generator[rle._Rule, None, None]:
        return super()._generate_rules(tech, gen_mask=False)


class Marker(_DesignMaskPrimitive):
    fill_space = "yes"

    def __init__(self, **super_args):
        super().__init__(**super_args)

        self.params += (
            _Param(self, "width", allow_none=True),
            _Param(self, "height", allow_none=True),
        )

    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Iterable[rle._Rule]:
        return super()._generate_rules(tech)


class Auxiliary(_DesignMaskPrimitive):
    # Layer not used in other primitives but defined by foundry for the technology
    fill_space = "no"

    def __init__(self, **super_args):
        super().__init__(**super_args)

    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Iterable[rle._Rule]:
        return super()._generate_rules(tech)


SpaceTableRow = Tuple[
    Union[float, Tuple[float, float]],
    float,
]
class _WidthSpacePrimitive(_MaskPrimitive):
    @abc.abstractmethod
    def __init__(self, *,
        min_width: IntFloat, min_space: IntFloat,
        space_table: Optional[Iterable[Iterable[float]]]=None,
        min_area: Optional[IntFloat]=None,
        min_density: Optional[float]=None, max_density: Optional[float]=None,
        **maskprimitive_args
    ):
        self.min_width = min_width = _util.i2f(min_width)
        self.min_space = min_space = _util.i2f(min_space)
        self.min_area = min_area = _util.i2f(min_area)
        self.min_density = min_density
        if (
            (min_density is not None)
            and ((min_density < 0.0) or (min_density > 1.0))
        ):
            raise ValueError("min_density has be between 0.0 and 1.0")
        self.max_density = max_density
        if (
            (max_density is not None)
            and ((max_density < 0.0) or (max_density > 1.0))
        ):
            raise ValueError("max_density has be between 0.0 and 1.0")

        if space_table is not None:
            table: List[SpaceTableRow] = []
            for row in space_table:
                values = _util.i2f_recursive(row)
                if (
                    (len(values) != 2)
                    or not all(isinstance(v, float) for v in values)
                ):
                    raise TypeError(
                        "space_table rows have to have two elements"
                    )
                width, space = values
                if not (
                    isinstance(width, float)
                    or (
                        isinstance(width, tuple) and (len(width) == 2)
                        and all(isinstance(w, float) for w in width)
                    )
                ):
                    raise TypeError(
                        "first element in a space_table row has to be a float "
                        "or an iterable of two floats"
                    )
                if not isinstance(space, float):
                    raise TypeError(
                        "second element in a space_table row has to be a float"
                    )

                table.append((
                    cast(Union[float, Tuple[float, float]], width),
                    space,
                ))
            self.space_table = tuple(table)
        else:
            self.space_table = None

        super().__init__(**maskprimitive_args)

        self.params += (
            _Param(self, "width", default=self.min_width),
            _Param(self, "height", default=self.min_width),
        )

    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Generator[rle._Rule, None, None]:
        yield from super()._generate_rules(tech)

        yield from (
            self.mask.width >= self.min_width,
            self.mask.space >= self.min_space,
        )
        if self.min_area is not None:
            yield self.mask.area >= self.min_area
        if self.min_density is not None:
            yield self.mask.density >= self.min_density
        if self.max_density is not None:
            yield self.mask.density <= self.max_density
        if self.space_table is not None:
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
                yield msk.Spacing(submask, self.mask) >= row[1]
        if isinstance(self, _PinAttribute) and self.pin is not None:
            yield from (
                msk.Connect(self.mask, pin.mask) for pin in self.pin
            )


class ExtraProcess(_DesignMaskPrimitive, _WidthSpacePrimitive):
    def __init__(self, *, fill_space: str, **super_args):
        if not fill_space in ("no", "yes"):
            raise ValueError("fill_space has to be either 'yes' or 'no'")
        self._fill_space = fill_space
        super().__init__(**super_args)

    @property
    def fill_space(self) -> str:
        return self._fill_space


class Implant(_DesignMaskPrimitive, _WidthSpacePrimitive):
    fill_space = "yes"

    # Implants are supposed to be disjoint unless they are used as combined implant
    # MOSFET and other primitives
    def __init__(self, *, type_: str, **super_args):
        if type_ not in ("n", "p", "adjust"):
            raise ValueError("type_ has to be 'n', 'p' or adjust")
        self.type_ = type_

        super().__init__(**super_args)


class Well(Implant):
    # Wells are non-overlapping by design
    def __init__(self, *,
        min_space_samenet: Optional[IntFloat]=None, **super_args,
    ):
        super().__init__(**super_args)

        self.ports += _PrimitiveNet(self, "conn")

        if min_space_samenet is not None:
            min_space_samenet = _util.i2f(min_space_samenet)
            if min_space_samenet >= self.min_space:
                raise ValueError("min_space_samenet has to be smaller than min_space")
        self.min_space_samenet = min_space_samenet

    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Generator[rle._Rule, None, None]:
        yield from super()._generate_rules(tech)

        if self.min_space_samenet is not None:
            yield msk.SameNet(self.mask).space >= self.min_space_samenet


class Insulator(_DesignMaskPrimitive, _WidthSpacePrimitive):
    def __init__(self, *, fill_space: str, **super_args):
        if not fill_space in ("no", "yes"):
            raise ValueError("fill_space has to be either 'yes' or 'no'")
        self._fill_space = fill_space
        super().__init__(**super_args)

    @property
    def fill_space(self) -> str:
        return self._fill_space


class _Conductor(
    _BlockageAttribute, _PinAttribute, _WidthSpacePrimitive,
):
    @abc.abstractmethod
    def __init__(self, **super_args):
        super().__init__(**super_args)

        self.ports += _PrimitiveNet(self, "conn")

    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Generator[rle._Rule, None, None]:
        yield from super()._generate_rules(tech)

        # Generate a mask for connection, thus without resistor parts
        # or ActiveWire without gate etc.
        indicators = chain(*tuple(r.indicator for r in filter(
            lambda p: p.wire == self,
            tech.primitives.__iter_type__(Resistor),
        )))
        polys = tuple(g.poly for g in filter(
            lambda p: p.active == self,
            tech.primitives.__iter_type__(MOSFETGate)
        ))
        removes = set(p.mask for p in chain(indicators, polys))

        if removes:
            if len(removes) == 1:
                remmask = removes.pop()
            else:
                remmask = msk.Join(removes)
            self.conn_mask = self.mask.remove(remmask).alias(self.mask.name + "__conn")
            yield self.conn_mask
        else:
            self.conn_mask = self.mask


class WaferWire(_DesignMaskPrimitive, _Conductor):
    fill_space = "same_net"

    # The wire made from wafer material and normally isolated by LOCOS for old technlogies
    # and STI for other ones.
    def __init__(self, *,
        allow_in_substrate: bool,
        implant: SingleOrMulti[Implant].T,
        min_implant_enclosure: SingleOrMulti[prp.Enclosure].T,
        implant_abut: Union[str, SingleOrMulti[Implant].T],
        allow_contactless_implant: bool,
        well: SingleOrMulti[Well].T,
        min_well_enclosure: SingleOrMulti[prp.Enclosure].T,
        min_substrate_enclosure: OptSingleOrMulti[prp.Enclosure].T=None,
        allow_well_crossing: bool,
        oxide: OptSingleOrMulti[Insulator].T=None,
        min_oxide_enclosure: SingleOrMulti[Optional[prp.Enclosure]].T=None,
        **super_args
    ):
        self.allow_in_substrate = allow_in_substrate

        self.implant = implant = _util.v2t(implant)
        for impl in implant:
            if isinstance(impl, Well):
                raise TypeError(f"well '{impl.name}' may not be part of implant")
        self.min_implant_enclosure = min_implant_enclosure = _util.v2t(
            min_implant_enclosure, n=len(implant),
        )
        if isinstance(implant_abut, str):
            _conv: Dict[str, Tuple[Implant, ...]] = {
                "all": implant, "none": tuple()
            }
            if implant_abut not in _conv:
                raise ValueError(
                    "only 'all' or 'none' allowed for a string implant_abut"
                )
            implant_abut = _conv[implant_abut]
        else:
            implant_abut = _util.v2t(implant_abut)
        for impl in implant_abut:
            if impl not in implant:
                raise ValueError(
                    f"implant_abut member '{impl.name}' not in implant list"
                )
        self.implant_abut = implant_abut
        self.allow_contactless_implant = allow_contactless_implant

        self.well = well = _util.v2t(well)
        for w in well:
            if not any(impl.type_ == w.type_ for impl in implant):
                raise UnconnectedPrimitiveError(well)
        min_well_enclosure = _util.v2t(min_well_enclosure, n=len(well))
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
        elif min_substrate_enclosure is not None:
            raise TypeError(
                "min_substrate_enclosure should be 'None' if allow_in_substrate is 'False'"
            )
        if not isinstance(allow_well_crossing, bool):
            raise TypeError("allow_well_crossing has to be a bool")
        self.allow_well_crossing = allow_well_crossing
        self.min_substrate_enclosure = min_substrate_enclosure

        if oxide is not None:
            oxide = _util.v2t(oxide)
            min_oxide_enclosure = _util.v2t(min_oxide_enclosure, n=len(oxide))
        elif min_oxide_enclosure is not None:
            raise ValueError("min_oxide_enclosure provided with no oxide given")
        self.oxide = oxide
        self.min_oxide_enclosure = min_oxide_enclosure

        super().__init__(**super_args)

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
        if self.oxide is not None:
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
                assert self.oxide is not None
                assert self.min_oxide_enclosure is not None
                oxide_enclosure = params["oxide_enclosure"]
                if oxide_enclosure is None:
                    idx = self.oxide.index(oxide)
                    params["oxide_enclosure"] = self.min_oxide_enclosure[idx]

        return params

    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Generator[rle._Rule, None, None]:
        yield from super()._generate_rules(tech)

        for i, impl in enumerate(self.implant):
            sd_mask_impl = msk.Intersect((self.conn_mask, impl.mask)).alias(
                f"{self.conn_mask.name}:{impl.name}",
            )
            yield from (sd_mask_impl, msk.Connect(self.conn_mask, sd_mask_impl))
            if self.allow_in_substrate and (impl.type_ == tech.substrate_type):
                yield msk.Connect(sd_mask_impl, tech.substrate)
            if impl not in self.implant_abut:
                yield edg.MaskEdge(impl.mask).interact_with(self.mask).length == 0
            enc = self.min_implant_enclosure[i]
            yield self.mask.enclosed_by(impl.mask) >= enc
            for w in self.well:
                if impl.type_ == w.type_:
                    yield msk.Connect(sd_mask_impl, w.mask)
        for implduo in combinations((impl.mask for impl in self.implant_abut), 2):
            yield msk.Intersect(implduo).area == 0
        # TODO: allow_contactless_implant
        for i, w in enumerate(self.well):
            enc = self.min_well_enclosure[i]
            yield self.mask.enclosed_by(w.mask) >= enc
        if self.min_substrate_enclosure is not None:
            yield (
                self.mask.enclosed_by(tech.substrate)
                >= self.min_substrate_enclosure
            )
        if not self.allow_well_crossing:
            mask_edge = edg.MaskEdge(self.mask)
            yield from (
                mask_edge.interact_with(edg.MaskEdge(w.mask)).length == 0
                for w in self.well
            )

    def in_(self, prim: SingleOrMulti[_MaskPrimitive].T) -> "_WaferWireIntersect":
        return _WaferWireIntersect(waferwire=self, prim=prim)


class _WaferWireIntersect(_DerivedPrimitive, _Intersect):
    """Intersect of WaferWire with one or more of it's implants, wells and
    oxides"""
    def __init__(self, *,
        waferwire: WaferWire, prim: SingleOrMulti[_MaskPrimitive].T,
    ):
        ww_prims: Set[_MaskPrimitive] = set(waferwire.implant)
        if waferwire.well is not None:
            ww_prims.update(waferwire.well)
        if waferwire.oxide is not None:
            ww_prims.update(waferwire.oxide)
        prim = _util.v2t(prim)
        for p in prim:
            if p not in ww_prims:
                raise ValueError(
                    f"prim '{p.name}' not an implant, well or oxide layer for '{self.name}'"
                )
        self.waferwire = waferwire
        self.prim = prim

        super().__init__(prims=(waferwire, *prim))


class GateWire(_Conductor):
    fill_space = "same_net"

    def __init__(self, **super_args):
        super().__init__(**super_args)


class MetalWire(_Conductor):
    fill_space = "same_net"

    def __init__(self, **super_args):
        super().__init__(**super_args)


class TopMetalWire(MetalWire):
    pass


ViaBottom = Union[WaferWire, GateWire, MetalWire, "Resistor"]
ViaTop = Union[MetalWire, "Resistor"]
class Via(_BlockageAttribute, _MaskPrimitive):
    def __init__(self, *,
        bottom: SingleOrMulti[ViaBottom].T, top: SingleOrMulti[ViaTop].T,
        width: IntFloat, min_space: IntFloat,
        min_bottom_enclosure: SingleOrMulti[prp.Enclosure].T,
        min_top_enclosure: SingleOrMulti[prp.Enclosure].T,
        **super_args,
    ):
        super().__init__(**super_args)

        self.ports += _PrimitiveNet(self, "conn")

        self.bottom = bottom = _util.v2t(bottom)
        self.min_bottom_enclosure = min_bottom_enclosure = _util.v2t(min_bottom_enclosure, n=len(bottom))
        for b in bottom:
            if isinstance(b, TopMetalWire):
                raise TypeError(
                    f"TopMetalWire '{b.name} not allowed as top of Via '{self.name}'",
                )
        self.top = top = _util.v2t(top)
        self.min_top_enclosure = min_top_enclosure = _util.v2t(
            min_top_enclosure, n=len(top),
        )
        self.width = width = _util.i2f(width)
        self.min_space = min_space = _util.i2f(min_space)

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
            (cast(WaferWire, wire).implant for wire in filter(
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

    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Generator[rle._Rule, None, None]:
        yield from super()._generate_rules(tech)

        yield from (
            self.mask.width == self.width,
            self.mask.space >= self.min_space,
            msk.Connect((b.conn_mask for b in self.bottom), self.mask),
            msk.Connect(self.mask, (b.conn_mask for b in self.top)),
        )
        for i in range(len(self.bottom)):
            bot_mask = self.bottom[i].mask
            enc = self.min_bottom_enclosure[i]
            yield self.mask.enclosed_by(bot_mask) >= enc
        for i in range(len(self.top)):
            top_mask = self.top[i].mask
            enc = self.min_top_enclosure[i]
            yield self.mask.enclosed_by(top_mask) >= enc

    @property
    def designmasks(self):
        yield from super().designmasks
        for conn in self.bottom + self.top:
            yield from conn.designmasks

    def in_(self, prim: SingleOrMulti[_MaskPrimitive].T) -> "_ViaIntersect":
        return _ViaIntersect(via=self, prim=prim)


class _ViaIntersect(_DerivedPrimitive, _Intersect):
    """Intersect of WaferWire with one or more of it's implants, wells and
    oxides"""
    def __init__(self, *,
        via: Via, prim: SingleOrMulti[_MaskPrimitive].T,
    ):
        via_prims: Set[_MaskPrimitive] = set((*via.bottom, *via.top))
        prim = _util.v2t(prim)
        for p in prim:
            if isinstance(p, _WaferWireIntersect):
                p = p.waferwire
            if p not in via_prims:
                raise ValueError(
                    f"prim '{p.name}' not a bottom or top layer for Via '{via.name}'"
                )
        self.via = via
        self.prin = prim

        super().__init__(prims=(via, *prim))


class PadOpening(_Conductor):
    fill_space = "no"

    def __init__(self, *,
        bottom: MetalWire, min_bottom_enclosure: prp.Enclosure, **super_args,
    ):
        super().__init__(**super_args)

        if isinstance(bottom, TopMetalWire):
            raise TypeError(
                f"TopMetalWire '{bottom.name}' not allowed for PadOpening '{self.name}'",
            )
        self.bottom = bottom
        self.min_bottom_enclosure = min_bottom_enclosure

    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Generator[rle._Rule, None, None]:
        yield from super()._generate_rules(tech)

        yield (
            self.mask.enclosed_by(self.bottom.mask)
            >= self.min_bottom_enclosure
        )

    @property
    def designmasks(self):
        yield from super().designmasks
        yield self.bottom.mask


ResistorWire = Union[WaferWire, GateWire, MetalWire]
ResistorIndicator = Union[Marker, ExtraProcess]
class Resistor(_WidthSpacePrimitive):
    def __init__(self, name, *,
        wire: ResistorWire,
        contact: Optional[Via]=None, min_contact_space: Optional[IntFloat]=None,
        indicator: SingleOrMulti[ResistorIndicator].T,
        min_indicator_extension: SingleOrMulti[IntFloat].T,
        implant: Optional[Implant]=None,
        min_implant_enclosure: Optional[prp.Enclosure]=None,
        model: Optional[str]=None, model_params: Optional[Dict[str, str]]=None,
        sheetres: Optional[IntFloat]=None, **widthspace_args,
    ):
        # If both model and sheetres are specified, sheetres will be used for
        # LVS circuit generation in pyspice export.
        self.wire = wire

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

        self.indicator = indicator = _util.v2t(indicator)
        self.min_indicator_extension = min_indicator_extension = _util.v2t(
            _util.i2f_recursive(min_indicator_extension), n=len(indicator),
        )

        if implant is not None:
            if isinstance(implant, Well):
                raise TypeError(
                    f"Resistor implant may not be Well '{implant.name}'",
                )
            if isinstance(wire, WaferWire):
                if implant not in wire.implant:
                    raise ValueError(
                        f"implant '{implant.name}' is not valid for waferwire '{wire.name}'"
                    )
            elif not isinstance(wire, GateWire):
                raise ValueError(
                    f"Resistor {name}: "
                    "implant may only be provided for a wire of type "
                    "'WaferWire' or 'GateWire'"
                )
        elif min_implant_enclosure is not None:
            raise TypeError(
                "min_implant_enclosure has to be 'None' if no implant is given"
            )
        self.implant = implant
        self.min_implant_enclosure = min_implant_enclosure

        prims = (wire, *indicator)
        if implant:
            prims += (implant,)
        mask = msk.Intersect(prim.mask for prim in prims).alias(f"resistor:{name}")

        super().__init__(name=name, mask=mask, **widthspace_args)

        self.ports += (_PrimitiveNet(self, name) for name in ("port1", "port2"))

        if contact is not None:
            if wire not in (contact.bottom + contact.top):
                raise ValueError(
                    f"wire {wire.name} does not connect to via {contact.name}"
                )
            min_contact_space = _util.i2f(min_contact_space)
            if not isinstance(min_contact_space, float):
                raise TypeError(
                    "min_contact_space has to be a float"
                )
        elif min_contact_space is not None:
            raise TypeError(
                "min_contact_space has to be 'None' if no contact layer is given"
            )
        self.contact = contact
        self.min_contact_space = min_contact_space

        if (model is None) and (sheetres is None):
            raise TypeError(
                "Either model or sheetres have to be specified"
            )

        if model is not None:
            assert model_params is not None
            if not (set(model_params.keys()) == {"width", "height"}):
                raise ValueError(
                    "model_params has to be a dict with keys ('width', 'height')"
                )
        elif model_params is not None:
            raise TypeError("model_params provided without a model")
        self.model = model
        self.model_params = model_params

        sheetres = _util.i2f(sheetres)
        if sheetres is not None:
            if not isinstance(sheetres, float):
                raise ValueError(
                    f"sheetres has to be None or a float, not type {type(sheetres)}"
                )
        self.sheetres = sheetres

    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Generator[rle._Rule, None, None]:
        # Do not generate the default width/space rules.
        yield from _Primitive._generate_rules(self, tech)

        # TODO: Can we provide proper type for self.mask ?
        yield cast(msk.DesignMask, self.mask)
        self.conn_mask = msk.Intersect((self.mask, *(p.mask for p in self.indicator)))
        if self.min_width > self.wire.min_width:
            yield self.mask.width >= self.min_width
        if self.min_space > self.wire.min_space:
            yield self.mask.space >= self.min_space
        if self.min_area is not None:
            if (self.wire.min_area is None) or (self.min_area > self.wire.min_area):
                yield self.mask.area >= self.min_area
        for i, ind in enumerate(self.indicator):
            ext = self.min_indicator_extension[i]
            mask = self.wire.mask.remove(ind.mask)
            yield mask.width >= ext


DiodeIndicator = Union[Marker, ExtraProcess]
class Diode(_WidthSpacePrimitive):
    def __init__(self, *, name: Optional[str]=None,
        wire: WaferWire, indicator: SingleOrMulti[DiodeIndicator].T,
        min_indicator_enclosure: SingleOrMulti[prp.Enclosure].T,
        implant: Implant, min_implant_enclosure: Optional[prp.Enclosure]=None,
        well: Optional[Well]=None, min_well_enclosure: Optional[prp.Enclosure]=None,
        model: Optional[str]=None, **widthspace_args,
    ):
        self.wire = wire

        self.indicator = indicator = _util.v2t(indicator)

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

        self.min_indicator_enclosure = min_indicator_enclosure = _util.v2t(
            min_indicator_enclosure, n=len(indicator),
        )

        if isinstance(implant, Well):
            raise TypeError(f"implant '{implant.name}' is a well")
        if not implant in wire.implant:
            raise ValueError(
                f"implant '{implant.name}' is not valid for waferwire '{wire.name}'"
            )
        self.implant = implant
        self.min_implant_enclosure = min_implant_enclosure

        if "mask" in widthspace_args:
            raise TypeError("Diode got an unexpected keyword argument 'mask'")
        else:
            widthspace_args["mask"] = msk.Intersect(
                prim.mask for prim in (wire, *indicator, implant)
            ).alias(f"diode:{name}")

        super().__init__(name=name, **widthspace_args)

        self.ports += (_PrimitiveNet(self, name) for name in ("anode", "cathode"))

        if well is None:
            if not wire.allow_in_substrate:
                raise TypeError(f"wire '{wire.name}' has to be in a well")
            # TODO: check types of substrate and implant
            if min_well_enclosure is not None:
                raise TypeError("min_well_enclosure given without a well")
        else:
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
        self.min_well_enclosure = min_well_enclosure

        self.model = model

    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Generator[rle._Rule, None, None]:
        # Do not generate the default width/space rules.
        yield from _Primitive._generate_rules(self, tech)

        # TODO: Can we provide proper type for self.mask ?
        yield cast(msk.DesignMask, self.mask)
        if self.min_width > self.wire.min_width:
            yield self.mask.width >= self.min_width
        if self.min_space > self.wire.min_space:
            yield self.mask.space >= self.min_space
        for i, ind in enumerate(self.indicator):
            enc = self.min_indicator_enclosure[i]
            yield self.wire.mask.enclosed_by(ind.mask) >= enc
        if self.min_implant_enclosure is not None:
            enc = self.min_implant_enclosure
            yield self.mask.enclosed_by(self.implant.mask) >= enc


class MOSFETGate(_WidthSpacePrimitive):
    class _ComputedProps:
        def __init__(self, gate: "MOSFETGate"):
            self.gate = gate

        @property
        def min_l(self) -> float:
            min_l = self.gate.min_l
            if min_l is None:
                min_l = self.gate.poly.min_width
            return min_l

        @property
        def min_w(self) -> float:
            min_w = self.gate.min_w
            if min_w is None:
                min_w = self.gate.active.min_width
            return min_w

        @property
        def min_gate_space(self) -> float:
            s = self.gate.min_gate_space
            if s is None:
                s = self.gate.poly.min_space
            return s

        @property
        def min_sd_width(self) -> Optional[float]:
            return self.gate.min_sd_width

        @property
        def min_polyactive_extension(self) -> Optional[float]:
            return self.gate.min_polyactive_extension

    @property
    def computed(self):
        return MOSFETGate._ComputedProps(self)

    def __init__(self, *, name: Optional[str]=None,
        active: WaferWire, poly: GateWire, oxide: Optional[Insulator]=None,
        inside: OptSingleOrMulti[Marker].T=None,
        min_l: Optional[IntFloat]=None, min_w: Optional[IntFloat]=None,
        min_sd_width: Optional[IntFloat]=None,
        min_polyactive_extension: Optional[IntFloat]=None,
        min_gate_space: Optional[IntFloat]=None,
        contact: Optional[Via]=None,
        min_contactgate_space: Optional[IntFloat]=None,
        min_gateoxide_enclosure: Optional[prp.Enclosure]=None,
        min_gateinside_enclosure: OptSingleOrMulti[prp.Enclosure].T=None,
    ):
        self.active = active
        self.poly = poly

        prims = (poly, active)
        if oxide is not None:
            if (active.oxide is None) or (oxide not in active.oxide):
                raise ValueError(
                    f"oxide '{oxide.name}' is not valid for active '{active.name}'"
                )
            prims += (oxide,)
        elif min_gateoxide_enclosure is not None:
            raise TypeError("min_gateoxide_enclosure provided without an oxide")
        self.oxide = oxide
        self.min_gateoxide_enclosure = min_gateoxide_enclosure

        if inside is not None:
            inside = _util.v2t(inside)
            if not all(isinstance(l, Marker) for l in inside):
                raise TypeError(
                    "inside has to be 'None', of type 'Marker' or "
                    "an iterable of type 'Marker'"
                )
            prims += inside
            if min_gateinside_enclosure is not None:
                min_gateinside_enclosure = _util.v2t(min_gateinside_enclosure, n=len(inside))
        elif min_gateinside_enclosure is not None:
            raise TypeError("min_gateinside_enclosure provided without inside provided")
        self.inside = inside
        self.min_gateinside_enclosure = min_gateinside_enclosure

        if name is None:
            name = "gate({})".format(",".join(prim.name for prim in prims))
            gatename = "gate:" + "+".join(prim.name for prim in prims)
        else:
            gatename = f"gate:{name}"

        if min_l is not None:
            min_l = _util.i2f(min_l)
            self.min_l = min_l
        else:
            # local use only
            min_l = poly.min_width
            self.min_l = None

        if min_w is not None:
            min_w = _util.i2f(min_w)
            self.min_w = min_w
        else:
            # local use only
            min_w = active.min_width
            self.min_w = None

        if min_sd_width is not None:
            min_sd_width = _util.i2f(min_sd_width)
        self.min_sd_width = min_sd_width

        if min_polyactive_extension is not None:
            min_polyactive_extension = _util.i2f(min_polyactive_extension)
            if not isinstance(min_polyactive_extension, float):
                raise TypeError("min_polyactive_extension has to be a float")
        self.min_polyactive_extension = min_polyactive_extension

        if min_gate_space is not None:
            min_gate_space = _util.i2f(min_gate_space)
            self.min_gate_space = min_gate_space
        else:
            # Local use only
            min_gate_space = poly.min_space
            self.min_gate_space = None

        if min_contactgate_space is not None:
            min_contactgate_space = _util.i2f(min_contactgate_space)
        elif contact is not None:
            raise ValueError("contact layer provided without min_contactgate_space specification")
        self.contact = contact
        self.min_contactgate_space = min_contactgate_space

        mask = msk.Intersect(prim.mask for prim in prims).alias(gatename)
        super().__init__(
            name=name, mask=mask,
            min_width=min(min_l, min_w), min_space=min_gate_space,
        )

    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Generator[rle._Rule, None, None]:
        active_mask = self.active.mask
        poly_mask = self.poly.conn_mask

        # Update mask if it has no oxide
        extra_masks = tuple()
        if self.oxide is None:
            extra_masks += tuple(
                cast(Any, gate).oxide.mask for gate in filter(
                    lambda prim: (
                        isinstance(prim, MOSFETGate)
                        and prim.active == self.active
                        and prim.poly == self.poly
                        and (prim.oxide is not None)
                    ), tech.primitives,
                )
            )
        if self.inside is None:
            def get_key(gate: "MOSFETGate"):
                if gate.oxide is not None:
                    return frozenset((gate.active, gate.poly, gate.oxide))
                else:
                    return frozenset((gate.active, gate.poly))

            for gate in filter(
                lambda prim: (
                    isinstance(prim, MOSFETGate)
                    and (get_key(prim) == get_key(self))
                    and prim.inside is not None
                ), tech.primitives,
            ):
                extra_masks += tuple(inside.mask for inside in cast(Any, gate).inside)
        masks = (active_mask, poly_mask)
        if self.oxide is not None:
            masks += (self.oxide.mask,)
        if self.inside is not None:
            masks += tuple(inside.mask for inside in self.inside)
        if extra_masks:
            masks += (wfr.outside(extra_masks),)
        # Keep the alias but change the mask of the alias
        cast(msk._MaskAlias, self.mask).mask = msk.Intersect(masks)
        mask = self.mask

        mask_used = False
        rules: List[rle._Rule] = []
        if self.min_l is not None:
            rules.append(
                edg.Intersect(
                    (edg.MaskEdge(active_mask), edg.MaskEdge(self.mask))
                ).length >= self.min_l,
            )
        if self.min_w is not None:
            rules.append(
                edg.Intersect(
                    (edg.MaskEdge(poly_mask), edg.MaskEdge(self.mask))
                ).length >= self.min_w,
            )
        if self.min_sd_width is not None:
            rules.append(active_mask.extend_over(mask) >= self.min_sd_width)
            mask_used = True
        if self.min_polyactive_extension is not None:
            rules.append(
                poly_mask.extend_over(mask) >= self.min_polyactive_extension,
            )
            mask_used = True
        if self.min_gate_space is not None:
            rules.append(mask.space >= self.min_gate_space)
            mask_used = True
        if self.min_contactgate_space is not None:
            assert self.contact is not None
            rules.append(
                msk.Spacing(mask, self.contact.mask) >= self.min_contactgate_space,
            )
            mask_used = True

        if mask_used:
            # This rule has to be put before the other rules that use the alias
            yield cast(rle._Rule, mask)
        yield from _MaskPrimitive._generate_rules(self, tech, gen_mask=False)
        yield from rules


class MOSFET(_Primitive):
    class _ComputedProps:
        def __init__(self, mosfet: "MOSFET"):
            self.mosfet = mosfet

        def _lookup(self, name: str, allow_none: bool):
            mosfet = self.mosfet
            v = getattr(mosfet, name)
            if v is None:
                v = getattr(mosfet.gate.computed, name, None)
            if v is None:
                v = getattr(mosfet.gate, name, None)
            if not allow_none:
                assert v is not None, "needed attribute"
            return v

        @property
        def min_l(self) -> float:
            return cast(float, self._lookup("min_l", False))

        @property
        def min_w(self) -> float:
            return cast(float, self._lookup("min_w", False))

        @property
        def min_sd_width(self) -> float:
            return cast(float, self._lookup("min_sd_width", False))

        @property
        def min_polyactive_extension(self) -> float:
            return cast(float, self._lookup("min_polyactive_extension", False))

        @property
        def min_gate_space(self) -> float:
            return cast(float, self._lookup("min_gate_space", False))

        @property
        def contact(self) -> Optional[Via]:
            return cast(Optional[Via], self._lookup("contact", True))

        @property
        def min_contactgate_space(self) -> float:
            return cast(float, self._lookup("min_contactgate_space", False))

    @property
    def computed(self):
        return MOSFET._ComputedProps(self)

    def __init__(
        self, *, name: str,
        gate: MOSFETGate, implant: SingleOrMulti[Implant].T,
        well: Optional[Well]=None,
        min_l: Optional[IntFloat]=None, min_w: Optional[IntFloat]=None,
        min_sd_width: Optional[IntFloat]=None,
        min_polyactive_extension: Optional[IntFloat]=None,
        min_gateimplant_enclosure: SingleOrMulti[prp.Enclosure].T,
        min_gate_space: Optional[IntFloat]=None,
        contact: Optional[Via]=None,
        min_contactgate_space: Optional[IntFloat]=None,
        model: Optional[str]=None,
    ):
        super().__init__(name=name)

        self.gate = gate
        self.implant = implant = _util.v2t(implant)
        self.well = well

        if min_l is not None:
            min_l = _util.i2f(min_l)
            if min_l <= gate.computed.min_l:
                raise ValueError("min_l has to be bigger than gate min_l if not 'None'")
        self.min_l = min_l

        if min_w is not None:
            min_w = _util.i2f(min_w)
            if min_w <= gate.computed.min_w:
                raise ValueError("min_w has to be bigger than gate min_w if not 'None'")
        self.min_w = min_w

        if min_sd_width is not None:
            min_sd_width = _util.i2f(min_sd_width)
            if not isinstance(min_sd_width, float):
                raise TypeError("min_sd_width has to be a float")
        elif gate.min_sd_width is None:
            raise ValueError("min_sd_width has to be either provided for the transistor gate or the transistor itself")
        self.min_sd_width = min_sd_width

        if min_polyactive_extension is not None:
            min_polyactive_extension = _util.i2f(min_polyactive_extension)
        elif gate.min_polyactive_extension is None:
            raise ValueError("min_polyactive_extension has to be either provided for the transistor gate or the transistor itself")
        self.min_polyactive_extension = min_polyactive_extension

        self.min_gateimplant_enclosure = min_gateimplant_enclosure = _util.v2t(
            min_gateimplant_enclosure, n=len(implant),
        )

        if min_gate_space is not None:
            min_gate_space = _util.i2f(min_gate_space)
        self.min_gate_space = min_gate_space

        if min_contactgate_space is not None:
            min_contactgate_space = _util.i2f(min_contactgate_space)
            if contact is None:
                if gate.contact is None:
                    raise ValueError("no contact layer provided for min_contactgate_space specification")
                contact = gate.contact
        elif contact is not None:
            raise ValueError("contact layer provided without min_contactgate_space specification")
        self.min_contactgate_space = min_contactgate_space
        self.contact = contact

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
    def gate_prim(self) -> _Intersect:
        prims: Tuple[_MaskPrimitive, ...] = (self.gate, *self.implant)
        if self.well is not None:
            prims += (self.well,)

        return _Intersect(prims=prims)

    @property
    def gate_mask(self):
        return self._gate_mask

    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Generator[rle._Rule, None, None]:
        yield from super()._generate_rules(tech)

        markers = (self.well.mask if self.well is not None else tech.substrate,)
        if self.implant is not None:
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

        yield derivedgate_mask
        if self.min_l is not None:
            yield edg.Intersect(
                (derivedgate_edge, active_edge),
            ).length >= self.min_l
        if self.min_w is not None:
            yield edg.Intersect(
                (derivedgate_edge, poly_edge),
            ).length >= self.min_w
        if self.min_sd_width is not None:
            yield (
                active_mask.extend_over(derivedgate_mask) >= self.min_sd_width
            )
        if self.min_polyactive_extension is not None:
            yield (
                poly_mask.extend_over(derivedgate_mask)
                >= self.min_polyactive_extension
            )
        for i in range(len(self.implant)):
            impl_mask = self.implant[i].mask
            enc = self.min_gateimplant_enclosure[i]
            if isinstance(enc.spec, float):
                yield derivedgate_mask.enclosed_by(impl_mask) >= enc
            else:
                yield channel_edge.enclosed_by(impl_mask) >= enc.spec[0]
                yield fieldgate_edge.enclosed_by(impl_mask) >= enc.spec[1]
        if self.min_gate_space is not None:
            yield derivedgate_mask.space >= self.min_gate_space
        if self.min_contactgate_space is not None:
            assert self.contact is not None
            yield (
                msk.Spacing(derivedgate_mask, self.contact.mask)
                >= self.min_contactgate_space
            )

    @property
    def designmasks(self):
        yield from super().designmasks
        yield from self.gate.designmasks
        if self.implant is not None:
            for impl in self.implant:
                yield from impl.designmasks
        if self.well is not None:
            yield from self.well.designmasks
        if self.contact is not None:
            if (self.gate.contact is None) or (self.contact != self.gate.contact):
                yield from self.contact.designmasks


class Spacing(_Primitive):
    def __init__(self, *,
        primitives1: SingleOrMulti[_MaskPrimitive].T,
        primitives2: SingleOrMulti[_MaskPrimitive].T,
        min_space: IntFloat,
    ):
        primitives1 = _util.v2t(primitives1)
        primitives2 = _util.v2t(primitives2)
        min_space = cast(float, _util.i2f(min_space))

        name = "Spacing({})".format(",".join(
            (
                prims[0].name if len(prims) == 1
                else "({})".format(",".join(prim.name for prim in prims))
            ) for prims in (primitives1, primitives2)
        ))
        super().__init__(name=name)
        self.primitives1 = primitives1
        self.primitives2 = primitives2
        self.min_space = min_space

    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Generator[rle._Rule, None, None]:
        yield from super()._generate_rules(tech)

        yield from (
            msk.Spacing(prim1.mask,prim2.mask) >= self.min_space
            for prim1, prim2 in product(self.primitives1, self.primitives2)
        )

    @property
    def designmasks(self):
        return super().designmasks

    def __repr__(self):
        return self.name


class Enclosure(_Primitive):
    def __init__(self, *,
        prim: _MaskPrimitive, by: _MaskPrimitive, min_enclosure: prp.Enclosure,
    ):
        name = f"Enclosure(prim={prim!r},by={by!r},min_enclosure={min_enclosure!r})"
        super().__init__(name=name)

        self.prim = prim
        self.by = by
        self.min_enclosure = min_enclosure

    def _generate_rules(self,
        tech: tch.Technology,
    ) -> Generator[rle._Rule, None, None]:
        yield from super()._generate_rules(tech)

        yield self.prim.mask.enclosed_by(self.by.mask) >= self.min_enclosure

    @property
    def designmasks(self) -> Generator[msk.DesignMask, None, None]:
        yield from super().designmasks
        yield from self.prim.designmasks
        yield from self.by.designmasks

    def __repr__(self) -> str:
        return self.name


class Primitives(_util.TypedListStrMapping[_Primitive]):
    _elem_type_ = _Primitive

    def __iadd__(self, x: SingleOrMulti[_Primitive].T) -> "Primitives":
        x = _util.v2t(x)
        for elem in x:
            if isinstance(elem, _DerivedPrimitive):
                raise TypeError(f"_DerivedPrimite '{elem.name}' can't be added to 'Primitives'")
            if elem in self:
                raise ValueError(
                    f"Adding primitive with name '{elem.name}' twice"
                )
        return cast("Primitives", super().__iadd__(x))


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
