# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
from math import floor, ceil
import abc

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

        def min_space(self, primitive1, primitive2):
            prims = self.tech.primitives
            for spacing in prims.tt_iter_type(prm.Spacing):
                if ((
                    (primitive1 in spacing.primitives1)
                    and (primitive2 in spacing.primitives2)
                ) or (
                    (primitive1 in spacing.primitives2)
                    and (primitive2 in spacing.primitives1)
                )):
                    return spacing.min_space

        def min_width(self, primitive, *, up=False, down=False, min_enclosure=False):
            if (
                (not isinstance(primitive, prm._Primitive))
                and hasattr(primitive, "min_width")
            ):
                raise TypeError(
                    "primitive has to be a '_Primitive' object with"
                    " the min_with attribute"
                )
            if not (isinstance(up, bool) and isinstance(down, bool)):
                raise TypeError("up and down have to be bools")

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
                *(wupdown(via) for via in self.tech.primitives.tt_iter_type(prm.Via)),
            ))

        def min_pitch(self, primitive, **kwargs):
            return self.min_width(primitive, **kwargs) + primitive.min_space

    name = abc.abstractproperty()
    grid = abc.abstractproperty()
    substrate_type = abc.abstractproperty()

    def __init__(self):
        self._init_done = False

        if not isinstance(self.name, str):
            raise TypeError("name Technology class attribute has to be a string")
        self.grid = _util.i2f(self.grid)
        if not isinstance(self.grid, float):
            raise TypeError("grid Technology class attribute has to be a float")
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

        prims.tt_freeze()

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
        wells = set(prims.tt_iter_type(prm.Well))

        # Wells are the first primitives in line
        add_prims(sorted(wells, key=get_name))

        # process waferwires
        waferwires = set(prims.tt_iter_type(prm.WaferWire))
        bottomwires.update(waferwires) # They also need to be connected
        conn_wells = set()
        for wire in waferwires:
            implants.update((*wire.implant, *wire.well))
            conn_wells.update(wire.well)
        if conn_wells != wells:
            raise prm.UnconnectedPrimitiveError((wells - conn_wells).pop())

        # process gatewires
        bottomwires.update(prims.tt_iter_type(prm.GateWire))

        # Already add implants that are used in the waferwires
        add_prims(sorted(implants, key=get_name))
        implants = set()

        # Add the oxides
        for ww in waferwires:
            if hasattr(ww, "oxide"):
                add_prims(sorted(ww.oxide))

        # process vias
        vias = set(prims.tt_iter_type(prm.Via))

        def allwires(wire):
            if isinstance(wire, prm.Resistor):
                yield allwires(wire.wire)
                for m in wire.marker:
                    yield m
            if hasattr(wire, "pin"):
                for p in wire.pin:
                    yield p
            if hasattr(wire, "blockage"):
                yield wire.blockage
            yield wire

        connvias = set(filter(lambda via: any(w in via.bottom for w in bottomwires), vias))
        if connvias:
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
        vias = tuple(prims.tt_iter_type(prm.Via))
        add_prims(prim.blockage for prim in filter(
            lambda p: hasattr(p, "blockage"), vias
        ))
        # Now add all vias
        add_prims(vias)

        # process mosfets
        mosfets = set(prims.tt_iter_type(prm.MOSFET))
        gates = set(mosfet.gate for mosfet in mosfets)
        actives = set(gate.active for gate in gates)
        polys = set(gate.poly for gate in gates)
        bottomwires.update(polys) # Also need to be connected
        for mosfet in mosfets:
            implants.update(mosfet.implant)
            if hasattr(mosfet, "well"):
                implants.add(mosfet.well)
            if hasattr(mosfet.gate, "inside"):
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
        padopenings = set(prims.tt_iter_type(prm.PadOpening))
        viabottoms = set()
        for padopening in padopenings:
            add_prims(allwires(padopening.bottom))
        add_prims(padopenings)

        # process top metal wires
        add_prims(prims.tt_iter_type(prm.TopMetalWire))

        # process resistors
        resistors = set(prims.tt_iter_type(prm.Resistor))
        for resistor in resistors:
            markers.update(resistor.indicator)

        # process diodes
        diodes = set(prims.tt_iter_type(prm.Diode))
        for diode in diodes:
            markers.update(diode.indicator)

        # process spacings
        spacings = set(prims.tt_iter_type(prm.Spacing))

        add_prims((*markers, *resistors, *diodes, *spacings))

        # process auxiliary
        def aux_key(aux):
            return (getattr(aux.mask, "gds_layer", (1000000, 1000000)), aux.name)
        add_prims(sorted(prims.tt_iter_type(prm.Auxiliary), key=aux_key))

        # reorder primitives
        unused = set(range(len(prims))) - set(neworder)
        if unused:
            raise prm.UnusedPrimitiveError(prims[unused.pop()])
        prims.tt_reorder(neworder)

    def _build_rules(self):
        prims = self._primitives
        self._rules = rules = rle.Rules()

        # grid
        rules += wfr.wafer.grid == self.grid

        # Generate the rule but don't add them yet.
        for prim in prims:
            prim._generate_rules(self)

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

        rules.tt_freeze()

    @property
    def substrate(self):
        if not self._init_done:
            raise AttributeError("substrate may not be accessed during object initialization")
        if self._substrate is None:
            well_masks = tuple(
                prim.mask for prim in self._primitives.tt_iter_type(prm.Well)
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

