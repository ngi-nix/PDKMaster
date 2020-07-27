import abc

from . import _util, property_ as prp, condition as cnd, mask as msk, primitive as prm

__all__ = ["Technology"]

class Technology(abc.ABC):
    name = abc.abstractproperty()
    grid = abc.abstractproperty()

    def __init__(self):
        if not isinstance(self.name, str):
            raise AttributeError("name Technology class attribute has to be a string")
        self.grid = _util.i2f(self.grid)
        if not isinstance(self.grid, float):
            raise AttributeError("grid Technology class attribute has to be a float")

        self._masks = masks = msk.Masks()
        self._primitives = prims = prm.Primitives()

        prims += (prm.Marker("wafer"), prm.Substrate())

        self._init()

        masks.freeze()
        prims.freeze()

    @abc.abstractmethod
    def _init(self):
        raise RuntimeError("abstract base method _init() has to be implemnted in subclass")


    @property
    def masks(self):
        return self._masks

    @property
    def primitives(self):
        return self._primitives

