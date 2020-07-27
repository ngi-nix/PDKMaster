from . import property_ as prp, condition as cnd, mask as msk, primitive as prm

__all__ = ["Technology"]

class Technology:
    def __init__(self, name):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")

        self.name = name
        self.grid = prp.Property(name + ".grid")
        self._constraints = cnd.Conditions()
        self._masks = msk.Masks()
        self._primitives = prims = prm.Primitives()

        prims += (prm.Marker("wafer"), prm.Substrate())

    @property
    def constraints(self):
        return self._constraints
    @constraints.setter
    def constraints(self, v):
        if v != self._constraints:
            raise AttributeError("You can update constraints attribute only with '+=' operator")

    @property
    def masks(self):
        return self._masks
    @masks.setter
    def masks(self, v):
        if v != self._masks:
            raise AttributeError("You can update constraints attribute only with '+=' operator")

    @property
    def primitives(self):
        return self._primitives
    @primitives.setter
    def primitives(self, v):
        if v != self._primitives:
            raise AttributeError("You can update primitives attribute only with '+=' operator")

