from . import property_ as prop, condition as cond, mask, primitive as prim

__all__ = ["Technology"]

class Technology:
    def __init__(self, name):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")

        self.name = name
        self.grid = prop.Property(name + ".grid")
        self._constraints = cond.Conditions()
        self._masks = masks = mask.Masks()
        self._primitives = prim.Primitives()

        masks += mask.Mask("wafer")

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

