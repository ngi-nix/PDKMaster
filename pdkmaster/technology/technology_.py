import abc

from .. import _util
from . import property_ as prp, rule as rle, mask as msk, wafer_ as wfr, primitive as prm

__all__ = ["Technology"]

class Technology(abc.ABC):
    class TechnologyError(Exception):
        pass

    name = abc.abstractproperty()
    grid = abc.abstractproperty()

    def __init__(self):
        self._init_done = False

        if not isinstance(self.name, str):
            raise AttributeError("name Technology class attribute has to be a string")
        self.grid = _util.i2f(self.grid)
        if not isinstance(self.grid, float):
            raise AttributeError("grid Technology class attribute has to be a float")

        self._primitives = prims = prm.Primitives()

        self._init()
        self._build_rules()

        prims.freeze()

        self._substrate = None
        self._init_done = True

    @abc.abstractmethod
    def _init(self):
        raise RuntimeError("abstract base method _init() has to be implemnted in subclass")

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

