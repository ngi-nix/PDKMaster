import abc

from .. import _util
from . import property_ as prp, rule as rle, mask as msk, wafer_ as wfr, primitive as prm

__all__ = ["Technology"]

class Technology(abc.ABC):
    class TechnologyError(Exception):
        pass

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

        self._checks()

        self._build_rules()

        prims.freeze()

    @abc.abstractmethod
    def _init(self):
        raise RuntimeError("abstract base method _init() has to be implemnted in subclass")

    def _checks(self):
        used_implants = set()
        used_wells = set()
        used_gates = set()
        topconnected_wires = set()
        bottomconnected_wires = set()

        for prim in self._primitives:
            if isinstance(prim, prm.BottomWire):
                bottomconnected_wires.add(prim)
            elif isinstance(prim, prm.TopWire):
                topconnected_wires.add(prim)
            elif isinstance(prim, prm.PadOpening):
                topconnected_wires.add(prim.bottom)
            elif isinstance(prim, prm.WaferWire):
                used_implants.update((*prim.implant, *prim.well))
                used_wells.update(prim.well)
            elif isinstance(prim, prm.Via):
                topconnected_wires.update(prim.bottom)
                bottomconnected_wires.update(prim.top)
            elif isinstance(prim, prm.MOSFET):
                used_implants.update(
                    filter(lambda impl: impl.type_ == "adjust", prim.implant)
                )
                used_gates.add(prim.gate)
            elif isinstance(prim, prm.Via):
                topconnected_wires.update(prim.bottom)
                bottomconnected_wires.update(prim.top)

        for prim in self._primitives:
            if isinstance(prim, prm.Implant) and (prim not in used_implants):
                raise prm.UnusedPrimitiveError(
                    f"implant '{prim.name}' defined but not used"
                )
            if isinstance(prim, prm.Well) and (prim not in used_wells):
                raise prm.UnusedPrimitiveError(
                    f"implant '{prim.name}' defined but not used"
                )
            if isinstance(prim, prm.Wire):
                if prim not in topconnected_wires:
                    raise prm.UnconnectedPrimitiveError(
                        f"wire '{prim.name}' is not connected from the top"
                    )
                if prim not in bottomconnected_wires:
                    raise prm.UnconnectedPrimitiveError(
                        f"wire '{prim.name}' is not connected from the bottom"
                    )
            if isinstance(prim, prm.MOSFETGate) and (prim not in used_gates):
                raise prm.UnconnectedPrimitiveError(
                    f"gate '{prim.name}' defined but not used"
                )

        for gate in used_gates:
            if gate not in self._primitives:
                raise Technology.TechnologyError(
                    f"gate '{gate.name}' used for MOSFET but is not in primitives attribute"
                )
    def _build_rules(self):
        prims = self._primitives
        self._rules = rules = rle.Rules()

        # grid
        rules += wfr.wafer.grid == self.grid

        for prim in prims:
            prim._generate_rules(self)
            rules += prim.rules

        rules.freeze()

    @property
    def substrate(self):
        if not self._init_done:
            raise AttributeError("substrate may not be accessed during object initialization")
        if self._substrate is None:
            well_masks = tuple(
                prim.mask for prim in
                filter(lambda p: isinstance(p, prm.Well), self._primitives)
            )
            if not well_masks:
                self._substrate = wfr.wafer
            else:
                self._substrate = wfr.wafer.remove(
                    well_masks[0] if len(well_masks) == 1 else msk.Join(well_masks),
                )
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

