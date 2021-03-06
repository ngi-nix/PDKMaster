# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
from math import floor, ceil
import abc
from typing import Tuple, Optional, cast

from .. import _util
from . import property_ as prp, rule as rle, mask as msk, wafer_ as wfr, primitive as prm


__all__ = ["Technology"]


class Technology(abc.ABC):
    class TechnologyError(Exception):
        pass
    class ConnectionError(Exception):
        pass

    class _ComputedSpecs:
        def __init__(self, tech):
            assert isinstance(tech, Technology), "Internal error"
            self.tech = tech

        def min_space(self,
            primitive1: "prm._Primitive", primitive2: Optional["prm._Primitive"],
        ) -> float:
            if (primitive2 is None) or (primitive1 == primitive2):
                try:
                    return cast(prm._WidthSpacePrimitive, primitive1).min_space
                except AttributeError:
                    raise AttributeError(
                        f"min_space between {primitive1} and {primitive2} not found",
                    )

            prims = self.tech.primitives
            for spacing in prims.__iter_type__(prm.Spacing):
                if ((
                    (primitive1 in spacing.primitives1)
                    and (primitive2 in spacing.primitives2)
                ) or (
                    (primitive1 in spacing.primitives2)
                    and (primitive2 in spacing.primitives1)
                )):
                    return spacing.min_space
            else:
                raise AttributeError(
                    f"min_space between {primitive1} and {primitive2} not found",
                )

        def min_width(self, primitive, *,
            up: bool=False, down: bool=False, min_enclosure: bool=False,
        ):
            assert primitive.min_width is not None, (
                "primitive has to have the min_with attribute"
            )

            def wupdown(via):
                if up and (primitive in via.bottom):
                    idx = via.bottom.index(primitive)
                    enc = via.min_bottom_enclosure[idx]
                    w = via.width
                elif down and (primitive in via.top):
                    idx = via.top.index(primitive)
                    enc = via.min_top_enclosure[idx]
                    w = via.width
                else:
                    enc = prp.Enclosure(0.0)
                    w = 0.0

                enc = enc.min() if min_enclosure else enc.max()
                return w + 2*enc

            return max((
                primitive.min_width,
                *(wupdown(via) for via in self.tech.primitives.__iter_type__(prm.Via)),
            ))

        def min_pitch(self, primitive, **kwargs):
            return self.min_width(primitive, **kwargs) + primitive.min_space

    @property
    @abc.abstractmethod
    def name(self) -> str:
        raise NotImplementedError
    @property
    @abc.abstractmethod
    def grid(self) -> float:
        raise NotImplementedError
    @property
    @abc.abstractmethod
    def substrate_type(self) -> str:
        raise NotImplementedError

    def __init__(self):
        self._init_done = False

        if not isinstance(self.name, str):
            raise TypeError("name Technology class attribute has to be a string")
        if not isinstance(self.substrate_type, str):
            raise TypeError("substrate_type Technology class attribute has to be a string")
        if not self.substrate_type in ("n", "p", "undoped"):
            raise ValueError("substrate_type Technology class attribute has to be 'n', 'p' or 'undoped'")

        self._primitives = prims = prm.Primitives()

        self._init()

        self._init_done = True
        self._substrate = None

        self._build_interconnect()
        self._build_rules()

        prims._freeze_()

        self.computed = self._ComputedSpecs(self)

    def on_grid(self, dim, *, mult=1, rounding="nearest"):
        dim = _util.i2f(dim)
        if not isinstance(dim, float):
            raise TypeError(
                f"dim has to be a float, not of type '{type(dim)}'"
            )
        if not isinstance(mult, int):
            raise TypeError(
                f"mult has to an int, not of type '{type(mult)}'"
            )
        if not isinstance(rounding, str):
            raise TypeError(
                f"rounding has to be a string, not of type '{type(rounding)}'"
            )
        flookup = {"nearest": round, "floor": floor, "ceiling": ceil}
        try:
            f = flookup[rounding]
        except KeyError:
            raise ValueError(
                f"rounding has to be one of {tuple(flookup.keys())}, not '{rounding}'"
            )

        return f(dim/(mult*self.grid))*mult*self.grid

    @property
    def dbu(self):
        """Return database unit compatible with technology grid"""
        igrid = int(round(1e6*self.grid))
        assert (igrid%10) == 0
        if (igrid%100) != 0:
            return 1e-5
        elif (igrid%1000) != 0:
            return 1e-4
        else:
            return 1e-3

    @abc.abstractmethod
    def _init(self):
        raise RuntimeError("abstract base method _init() has to be implemnted in subclass")

    def _build_interconnect(self):
        prims = self._primitives

        neworder = []
        def add_prims(prims2):
            for prim in prims2:
                if prim is None:
                    continue
                idx = prims.index(prim)
                if idx not in neworder:
                    neworder.append(idx)

        def get_name(prim):
            return prim.name

        # set that are build up when going over the primitives
        # bottomwires: primitives that still need to be bottomconnected by a via
        bottomwires = set()
        # implants: used implant not added yet
        implants = set() # Implants to add
        markers = set() # Markers to add
        # the wells, fixed
        wells = set(prims.__iter_type__(prm.Well))

        # Wells are the first primitives in line
        add_prims(sorted(wells, key=get_name))

        # process waferwires
        waferwires = set(prims.__iter_type__(prm.WaferWire))
        bottomwires.update(waferwires) # They also need to be connected
        conn_wells = set()
        for wire in waferwires:
            implants.update((*wire.implant, *wire.well))
            conn_wells.update(wire.well)
        if conn_wells != wells:
            raise prm.UnconnectedPrimitiveError((wells - conn_wells).pop())

        # process gatewires
        bottomwires.update(prims.__iter_type__(prm.GateWire))

        # Already add implants that are used in the waferwires
        add_prims(sorted(implants, key=get_name))
        implants = set()

        # Add the oxides
        for ww in waferwires:
            if ww.oxide is not None:
                add_prims(sorted(ww.oxide, key=get_name))

        # process vias
        vias = set(prims.__iter_type__(prm.Via))

        def allwires(wire):
            if isinstance(wire, prm.Resistor):
                yield allwires(wire.wire)
                for m in wire.indicator:
                    yield m
            if isinstance(wire, prm._PinAttribute) and wire.pin is not None:
                for p in wire.pin:
                    yield p
            if isinstance(wire, prm._BlockageAttribute) and wire.blockage is not None:
                yield wire.blockage
            yield wire

        connvias = set(filter(lambda via: any(w in via.bottom for w in bottomwires), vias))
        if connvias:
            viatops = set()
            while connvias:
                viabottoms = set()
                viatops = set()
                for via in connvias:
                    viabottoms.update(via.bottom)
                    viatops.update(via.top)

                noconn = viabottoms - bottomwires
                if noconn:
                    raise Technology.ConnectionError(
                        f"wires ({', '.join(wire.name for wire in noconn)}) not connected from bottom"
                    )

                for bottom in viabottoms:
                    add_prims(allwires(bottom))

                bottomwires -= viabottoms
                bottomwires.update(viatops)

                vias -= connvias
                connvias = set(filter(lambda via: any(w in via.bottom for w in bottomwires), vias))
            # Add the top layers of last via to the prims
            for top in viatops:
                add_prims(allwires(top))

        if vias:
            raise Technology.ConnectionError(
                f"vias ({', '.join(via.name for via in vias)}) not connected to bottom wires"
            )

        # Add via and it's blockage layers
        vias = tuple(prims.__iter_type__(prm.Via))
        add_prims((prim.blockage for prim in vias))
        # Now add all vias
        add_prims(vias)

        # process mosfets
        mosfets = set(prims.__iter_type__(prm.MOSFET))
        gates = set(mosfet.gate for mosfet in mosfets)
        actives = set(gate.active for gate in gates)
        polys = set(gate.poly for gate in gates)
        bottomwires.update(polys) # Also need to be connected
        for mosfet in mosfets:
            implants.update(mosfet.implant)
            if mosfet.well is not None:
                implants.add(mosfet.well)
            if mosfet.gate.inside is not None:
                markers.update(mosfet.gate.inside)

        add_prims((
            *sorted(implants, key=get_name),
            *sorted(actives, key=get_name), *sorted(polys, key=get_name),
            *sorted(markers, key=get_name), *sorted(gates, key=get_name),
            *sorted(mosfets, key=get_name),
        ))
        implants = set()
        markers = set()

        # proces pad openings
        padopenings = set(prims.__iter_type__(prm.PadOpening))
        viabottoms = set()
        for padopening in padopenings:
            add_prims(allwires(padopening.bottom))
        add_prims(padopenings)

        # process top metal wires
        add_prims(prims.__iter_type__(prm.TopMetalWire))

        # process resistors
        resistors = set(prims.__iter_type__(prm.Resistor))
        for resistor in resistors:
            markers.update(resistor.indicator)

        # process diodes
        diodes = set(prims.__iter_type__(prm.Diode))
        for diode in diodes:
            markers.update(diode.indicator)

        # process spacings/enclosures
        spacings = set(prims.__iter_type__(prm.Spacing))
        enclosures = set(prims.__iter_type__(prm.Enclosure))

        add_prims((*markers, *resistors, *diodes, *spacings, *enclosures))

        # process auxiliary
        def aux_key(aux: prm.Auxiliary) -> Tuple[int, int]:
            if (
                isinstance(aux.mask, msk.DesignMask)
                and (aux.mask.gds_layer is not None)
            ):
                return aux.mask.gds_layer
            else:
                return (1000000, 1000000)
        add_prims(sorted(prims.__iter_type__(prm.Auxiliary), key=aux_key))

        # reorder primitives
        unused = set(range(len(prims))) - set(neworder)
        if unused:
            raise prm.UnusedPrimitiveError(prims[unused.pop()])
        prims._reorder_(neworder)

    def _build_rules(self):
        prims = self._primitives
        self._rules = rules = rle.Rules()

        # grid
        rules += wfr.wafer.grid == self.grid

        # Generate the rule but don't add them yet.
        for prim in prims:
            prim._derive_rules(self)

        # First add substrate alias if needed. This will only be clear
        # after the rules have been generated.
        sub = self.substrate
        if isinstance(sub, msk._MaskAlias):
            self._rules += sub
        if sub != wfr.wafer:
            self._rules += msk.Connect(sub, wfr.wafer)

        # Now we can add the rules
        for prim in prims:
            self._rules += prim.rules

        rules._freeze_()

    @property
    def substrate(self):
        if not self._init_done:
            raise AttributeError("substrate may not be accessed during object initialization")
        if self._substrate is None:
            well_masks = tuple(
                prim.mask for prim in self._primitives.__iter_type__(prm.Well)
            )
            if not well_masks:
                self._substrate = wfr.wafer
            else:
                self._substrate = wfr.outside(well_masks, alias=f"substrate:{self.name}")
        return self._substrate

    @property
    def rules(self):
        return self._rules

    @property
    def primitives(self):
        return self._primitives

    @property
    def designmasks(self):
        masks = set()
        for prim in self._primitives:
            for mask in prim.designmasks:
                if mask not in masks:
                    yield mask
                    masks.add(mask)

