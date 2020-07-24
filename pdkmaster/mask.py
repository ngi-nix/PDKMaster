from . import _util, condition as cond, property_ as prop

__all__ = ["Mask", "Masks"]

class _MaskProperty(prop.Property):
    def __init__(self, mask, name):
        assert (isinstance(mask, Mask) and isinstance(name, str)), "Internal error"

        super().__init__(mask.name + "." + name)
        self.mask = mask
        self.prop_name = name

class _DualMaskProperty(prop.Property):
    def __init__(self, mask1, mask2, name, *, commutative):
        assert (
            isinstance(mask1, Mask) and isinstance(mask2, Mask)
            and isinstance(name, str) and isinstance(commutative, bool)
        ), "Internal error"

        name = "{}.{}.{}".format(mask1.name, mask2.name, name)
        if commutative:
            alias = "{}.{}.{}".format(mask2.name, mask1.name, name)
            super().__init__(name, alias)
        else:
            super().__init__(name)

        self.mask1 = mask1
        self.mask2 = mask2
        self.prop_name = name

class _MultiMaskCondition(cond.Condition):
    def __init__(self, mask, others):
        assert (isinstance(mask, Mask)
                and (len(others) > 0)
                and all(isinstance(mask, Mask) for mask in others)
               ), "Internal error"
        super().__init__((mask, others))

        self.mask = mask
        self.others = others

    def __hash__(self):
        return hash((self.mask, *self.others))

class _InsideCondition(_MultiMaskCondition):
    pass
class _OutsideCondition(_MultiMaskCondition):
    pass

class Mask:
    def __init__(self, name):
        self.name = name
        self.width = _MaskProperty(self, "width")
        self.space = _MaskProperty(self, "space")
        self.grid = _MaskProperty(self, "grid")

    def space_to(self, other):
        if not isinstance(other, Mask):
            raise TypeError("other has to be of type 'Mask'")

        return _DualMaskProperty(self, other, "space", commutative=True)

    def extend_over(self, other):
        if not isinstance(other, Mask):
            raise TypeError("other has to be of type 'Mask'")

        return _DualMaskProperty(self, other, "extend_over", commutative=False)

    def enclosed_by(self, other):
        if not isinstance(other, Mask):
            raise TypeError("other has to be of type 'Mask'")

        return _DualMaskProperty(self, other, "enclosed_by", commutative=False)

    def overlap_with(self, other):
        if not isinstance(other, Mask):
            raise TypeError("other has to be of type 'Mask'")

        return _DualMaskProperty(self, other, "overlap_with", commutative=True)

    def is_inside(self, other, *others):
        if isinstance(other, Mask):
            masks = (other, *others)
        else:
            try:
                masks = (*other, *others)
            except:
                raise TypeError("Outside mask not of type 'Mask'")
        for l in masks:
            if not isinstance(l, Mask):
                raise TypeError("Outside mask not of type 'Mask'")
        
        return _InsideCondition(self, masks)

    def is_outside(self, other, *others):
        if isinstance(other, Mask):
            masks = (other, *others)
        else:
            try:
                masks = (*other, *others)
            except:
                raise TypeError("Outside mask not of type 'Mask'")
        for l in masks:
            if not isinstance(l, Mask):
                raise TypeError("Outside mask not of type 'Mask'")
        
        return _OutsideCondition(self, masks)

class Masks:
    def __init__(self):
        self._masks = {}

    def __getitem__(self, key):
        return self._masks[key]

    def __getattr__(self, name):
        try:
            return self._masks[name]
        except KeyError:
            raise AttributeError("Mask '{}' not present".format(name))

    def __iadd__(self, other):
        masks = tuple(other) if _util.is_iterable(other) else (other,)
        for mask in masks:
            if not isinstance(mask, Mask):
                raise TypeError("Can only add 'Mask' object or an iterable of 'Mask' objects to 'Masks'")
            if mask.name in self._masks:
                raise ValueError("Mask '{}' already exists".format(mask.name))

        self._masks.update({mask.name: mask for mask in masks})
        
        return self

    def __iter__(self):
        return iter(self._masks.values())
