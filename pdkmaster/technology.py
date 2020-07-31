import abc

from . import _util, property_ as prp, condition as cnd, mask as msk, primitive as prm

__all__ = ["Technology"]

class Technology(abc.ABC):
    name = abc.abstractproperty()
    grid = abc.abstractproperty()

    def __init__(self):
        self._init_done = False

        if not isinstance(self.name, str):
            raise AttributeError("name Technology class attribute has to be a string")
        self.grid = _util.i2f(self.grid)
        if not isinstance(self.grid, float):
            raise AttributeError("grid Technology class attribute has to be a float")

        self._masks = masks = msk.Masks()
        self._primitives = prims = prm.Primitives()

        masks += (msk.Wafer(),)

        self._init()
        self._build_rules()

        masks.freeze()
        prims.freeze()

        self._substrate = None
        self._init_done = True

    @abc.abstractmethod
    def _init(self):
        raise RuntimeError("abstract base method _init() has to be implemnted in subclass")

    def _build_rules(self):
        masks = self._masks
        prims = self._primitives
        self._rules = rules = cnd.Conditions()

        # grid
        rules += masks.wafer.grid == self.grid

        for prim in prims:
            prim._generate_rules(self)
            rules += prim.rules

        rules.freeze()

    @property
    def substrate(self):
        if not self._init_done:
            raise AttributeError("substrate may not be accessed during object initialization")
        if self._substrate is None:
            wells = filter(isinstance(prim, prm.Well) for prim in self.primitives)
            if not wells:
                self._substrate = self.masks.wafer
            else:
                self._substrate = self.masks.wafer.remove(msk.Mask.join(wells))
        return self._substrate

    @property
    def rules(self):
        return self._rules

    @property
    def masks(self):
        return self._masks

    @property
    def primitives(self):
        return self._primitives

