from . import condition as cond, property_ as prop

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

class _MaskMultiCondition(cond.Condition):
    def __init__(self, mask, others):
        assert (isinstance(mask, Mask) and len(others) != 0), "Internal error"
        super().__init__((mask, others))

        self.mask = mask
        self.others = others

    def __hash__(self):
        return hash((self.mask, self.others))

class _InsideCondition(_MaskMultiCondition):
    pass
class _OutsideCondition(_MaskMultiCondition):
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
        return self._masks[name]

    def __iadd__(self, other):
        e = TypeError("Can only add 'Mask' object or an iterable of 'Mask' objects to 'Masks'")
        try:
            for mask in other:
                if not isinstance(mask, Mask):
                    raise e
        except TypeError:
            if not isinstance(other, Mask):
                raise e
            other = (other,)
        for mask in other:
            if mask.name in self._masks:
                raise ValueError("Mask '{}' already exists".format(mask.name))
        self._masks.update({mask.name: mask for mask in other})
        
        return self