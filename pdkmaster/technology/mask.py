# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
import abc
from typing import Iterable, Tuple, cast

from ..typing import OptSingleOrMulti, SingleOrMulti
from .. import _util
from . import rule as rle, property_ as prp


__all__ = ["DesignMask"]


class _MaskProperty(prp.Property):
    def __init__(self, mask, name):
        assert (isinstance(mask, _Mask) and isinstance(name, str)), "Internal error"

        super().__init__(mask.name + "." + name)
        self.mask = mask
        self.prop_name = name


class _DualMaskProperty(prp.Property):
    def __init__(self, mask1, mask2, name, *, commutative):
        assert (
            isinstance(mask1, _Mask) and isinstance(mask2, _Mask)
            and isinstance(name, str) and isinstance(commutative, bool)
        ), "Internal error"

        if commutative:
            supername = "{}({},{})".format(name, mask1.name, mask2.name)
        else:
            supername = "{}.{}({})".format(mask1.name, name, mask2.name)
        super().__init__(supername)

        self.mask1 = mask1
        self.mask2 = mask2
        self.prop_name = name


class _DualMaskEnclosureProperty(prp.EnclosureProperty):
    def __init__(self, mask1, mask2, name):
        assert (
            isinstance(mask1, _Mask) and isinstance(mask2, _Mask)
            and isinstance(name, str)
        ), "Internal error"

        super().__init__("{}.{}({})".format(mask1.name, name, mask2.name))

        self.mask1 = mask1
        self.mask2 = mask2
        self.prop_name = name


class _AsymmetricDualMaskProperty(_DualMaskProperty):
    @classmethod
    def cast(cls, value):
        if not (_util.is_iterable(value)):
            raise TypeError("property value has to be iterable of float of length 2")
        value = tuple(_util.i2f(v) for v in value)
        if not ((len(value) == 2) and all(isinstance(v, float) for v in value)):
            raise TypeError("property value has to be iterable of float of length 2")

        return value


class _MultiMaskCondition(prp._Condition, abc.ABC):
    operation = abc.abstractproperty()

    def __init__(self, mask, others):
        if not isinstance(self.operation, str):
            raise AttributeError("operation _MultMaskCondition abstract attribute has to be a string")
        assert (isinstance(mask, _Mask)
                and (len(others) > 0)
                and all(isinstance(mask, _Mask) for mask in others)
               ), "Internal error"
        super().__init__((mask, others))

        self.mask = mask
        self.others = others

    def __hash__(self):
        return hash((self.mask, *self.others))

    def __repr__(self):
        return "{}.{}({})".format(
            str(self.mask), self.operation,
            ",".join(str(mask) for mask in self.others),
        )


class _InsideCondition(_MultiMaskCondition):
    operation = "is_inside"
class _OutsideCondition(_MultiMaskCondition):
    operation = "is_outside"


class _Mask(abc.ABC):
    @abc.abstractmethod
    def __init__(self, name: str):
        self.name = name
        self.width = _MaskProperty(self, "width")
        self.length = _MaskProperty(self, "length")
        self.space = _MaskProperty(self, "space")
        self.area = _MaskProperty(self, "area")
        self.density = _MaskProperty(self, "density")

    def __repr__(self):
        return self.name

    def extend_over(self, other: "_Mask"):
        return _DualMaskProperty(self, other, "extend_over", commutative=False)

    def enclosed_by(self, other: "_Mask"):
        return _DualMaskEnclosureProperty(self, other, "enclosed_by")

    def is_inside(self, other: SingleOrMulti["_Mask"].T, *others: "_Mask"):
        masks = (*_util.v2t(other), *others)
        
        return _InsideCondition(self, masks)

    def is_outside(self, other: SingleOrMulti["_Mask"].T, *others: "_Mask"):
        masks = (*_util.v2t(other), *others)
        
        return _OutsideCondition(self, masks)

    def parts_with(self, condition: SingleOrMulti[prp._BinaryPropertyCondition].T):
        return _PartsWith(mask=self, condition=condition)

    def remove(self, what: "_Mask"):
        return _MaskRemove(from_=self, what=what)

    def alias(self, name: str):
        return _MaskAlias(name=name, mask=self)

    @abc.abstractproperty
    def designmasks(self) -> Iterable["DesignMask"]:
        return tuple()


class DesignMask(_Mask, rle._Rule):
    def __init__(self, name: str, *,
        gds_layer: OptSingleOrMulti[int].T=None, fill_space: str,
    ):
        if gds_layer is not None:
            gds_layer = _util.v2t(gds_layer)
            if len(gds_layer) == 1:
                gds_layer += (0,)
            if len(gds_layer) != 2:
                raise TypeError("gds_layer has to be an int or an iterable of two ints")
            self.gds_layer = cast(Tuple[int, int], gds_layer)
        else:
            self.gds_layer = None

        super().__init__(name)

        if not fill_space in ("no", "same_net", "yes"):
            raise ValueError("fill_space has to be one of ('no', 'same_net', 'yes')")
        self.fill_space = fill_space

        self.grid = _MaskProperty(self, "grid")

    def __repr__(self):
        sgds = (
            "" if self.gds_layer is None
            else f", gds_layer={self.gds_layer[0]}.{self.gds_layer[1]}"
        )
        return f"design({self.name}{sgds})"

    def __hash__(self):
        return hash(self.name)

    @property
    def designmasks(self):
        return (self,)


class _PartsWith(_Mask):
    def __init__(self, *,
        mask: _Mask, condition: SingleOrMulti[prp._BinaryPropertyCondition].T,
    ):
        self.mask = mask

        condition = _util.v2t(condition)
        if not all(
            (
                isinstance(cond.left, _MaskProperty)
                and cond.left.mask == mask
            ) for cond in condition
        ):
            raise TypeError(
                "condition has to a single or an iterable of condition on properties of mask '{}'".format(
                    mask.name,
                ))
        self.condition = condition

        super().__init__("{}.parts_with({})".format(
            mask.name, ",".join(str(cond) for cond in condition),
        ))

    @property
    def designmasks(self):
        return self.mask.designmasks


class Join(_Mask):
    def __init__(self, masks: SingleOrMulti[_Mask].T):
        self.masks = masks = _util.v2t(masks)

        super().__init__("join({})".format(",".join(mask.name for mask in masks)))

    @property
    def designmasks(self):
        for mask in self.masks:
            yield from mask.designmasks


class Intersect(_Mask):
    def __init__(self, masks: SingleOrMulti[_Mask].T):
        self.masks = masks = _util.v2t(masks)

        super().__init__("intersect({})".format(",".join(mask.name for mask in masks)))

    @property
    def designmasks(self):
        for mask in self.masks:
            yield from mask.designmasks


class _MaskRemove(_Mask):
    def __init__(self, *, from_: _Mask, what: _Mask):
        super().__init__("{}.remove({})".format(from_.name, what.name))
        self.from_ = from_
        self.what = what

    @property
    def designmasks(self):
        for mask in (self.from_, self.what):
            yield from mask.designmasks


class _MaskAlias(_Mask, rle._Rule):
    def __init__(self, *, name, mask):
        if not isinstance(mask, _Mask):
            raise TypeError("mask has to be of type 'Mask'")
        self.mask = mask

        super().__init__(name)

    def __hash__(self):
        return hash((self.name, self.mask))

    def __repr__(self):
        return f"{self.mask.name}.alias({self.name})"

    @property
    def designmasks(self):
        return self.mask.designmasks


class Spacing(_DualMaskProperty):
    def __init__(self, mask1, mask2):
        if not all(isinstance(mask, _Mask) for mask in (mask1, mask2)):
            raise TypeError("mask1 and mask2 have to be of type 'Mask'")

        super().__init__(mask1, mask2, "space", commutative=True)


class OverlapWidth(_DualMaskProperty):
    def __init__(self, mask1, mask2):
        if not all(isinstance(mask, _Mask) for mask in (mask1, mask2)):
            raise TypeError("mask1 and mask2 have to be of type 'Mask'")

        super().__init__(mask1, mask2, "overlapwidth", commutative=True)


class Connect(rle._Rule):
    def __init__(self,
        mask1: SingleOrMulti[_Mask].T, mask2: SingleOrMulti[_Mask].T,
    ):
        self.mask1 = mask1 = _util.v2t(mask1)
        self.mask2 = mask2 = _util.v2t(mask2)

    def __hash__(self):
        return hash((self.mask1, self.mask2))

    def __repr__(self):
        s1 = self.mask1[0].name if len(self.mask1) == 1 else "({})".format(
            ",".join(m.name for m in self.mask1)
        )
        s2 = self.mask2[0].name if len(self.mask2) == 1 else "({})".format(
            ",".join(m.name for m in self.mask2)
        )
        return f"connect({s1},{s2})"


class SameNet(_Mask):
    def __init__(self, mask):
        if not isinstance(mask, _Mask):
            raise TypeError("mask has to be of type _Mask")
        self.mask = mask

        super().__init__(f"same_net({mask.name})")

    @property
    def designmasks(self):
        return self.mask.designmasks
