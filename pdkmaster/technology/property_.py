# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
import abc

from .. import _util
from . import rule as rle

__all__ = ["Operators", "Property"]

class _Condition(rle._Rule):
    @abc.abstractmethod
    def __init__(self, elements):
        self._elements = elements

    def __hash__(self):
        return hash(self._elements)

    @abc.abstractmethod
    def __repr__(self):
        raise RuntimeError("_Condition subclass needs to implement __repr__() method")

class _BinaryPropertyCondition(_Condition, abc.ABC):
    symbol = abc.abstractproperty()

    def __init__(self, *, left, right):
        if not isinstance(self.symbol, str):
            raise AttributeError("symbol _BinaryPropertyCondition abstract property has to be a string")
        if not isinstance(left, Property):
            raise TypeError("left value has to be of type 'Property'")

        super().__init__((left, right))
        self.left = left
        self.right = left.cast(right)

    def __repr__(self):
        return "{} {} {}".format(repr(self.left), self.symbol, repr(self.right))

class Operators:
    class Greater(_BinaryPropertyCondition):
        symbol = ">"
    class GreaterEqual(_BinaryPropertyCondition):
        symbol = ">="
    class Smaller(_BinaryPropertyCondition):
        symbol = "<"
    class SmallerEqual(_BinaryPropertyCondition):
        symbol = "<="
    class Equal(_BinaryPropertyCondition):
        symbol = "=="
    # Convenience assigns
    GT = Greater
    GE = GreaterEqual
    ST = Smaller
    SE = SmallerEqual
    EQ = Equal
# Convenience assigns
Ops = Operators

class Property:
    value_conv = _util.i2f
    value_type = float
    value_type_str = "float"

    def __init__(self, name, *, allow_none=False):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        self.name = name

        if not isinstance(allow_none, bool):
            raise TypeError("allow_none has to be a bool")
        self.allow_none = allow_none

        self.dependencies = set()

    def __gt__(self, other):
        return Ops.Greater(left=self, right=other)
    def __ge__(self, other):
        return Ops.GreaterEqual(left=self, right=other)
    def __lt__(self, other):
        return Ops.Smaller(left=self, right=other)
    def __le__(self, other):
        return Ops.SmallerEqual(left=self, right=other)
    def __eq__(self, other):
        return Ops.Equal(left=self, right=other)

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def cast(self, value):
        if value is None:
            if self.allow_none:
                return None
            else:
                raise TypeError("property value {!r} is not of type '{}'".format(
                    value, self.value_type_str,
                ))

        value_conv = self.__class__.value_conv
        if value_conv is not None:
            try:
                value = value_conv(value)
            except:
                raise TypeError("could not convert property value {!r} to type '{}'".format(
                    value, self.value_type_str,
                ))
        if not isinstance(value, self.value_type):
            raise TypeError("value {!r} for property '{}' is not of type '{}'".format(
                value, self.name, self.value_type_str,
            ))
        return value

class Enclosure:
    def __init__(self, spec):
        if isinstance(spec, Enclosure):
            spec = spec.spec
        spec = _util.i2f_recursive(spec)
        if not (
            isinstance(spec, float)
            or (
                _util.is_iterable(spec)
                and len(spec) == 2
                and all(isinstance(v, float) for v in spec)
            )
        ):
            raise TypeError("spec has to be a float or a pair of floats")
        self.spec = spec

    @property
    def first(self):
        return self.spec if isinstance(self.spec, float) else self.spec[0]

    @property
    def second(self):
        return self.spec if isinstance(self.spec, float) else self.spec[1]

    def min(self):
        return self.spec if isinstance(self.spec, float) else min(self.spec)

    def max(self):
        return self.spec if isinstance(self.spec, float) else max(self.spec)

    def wide(self):
        # Put bigger enclosure value first
        spec = self.spec
        if (
            isinstance(spec, float)
            or (spec[0] >= spec[1])
        ):
            return self
        else:
            return Enclosure((spec[1], spec[0]))

    def tall(self):
        # Put smaller enclosure value first
        spec = self.spec
        if (
            isinstance(spec, float)
            or (spec[0] <= spec[1])
        ):
            return self
        else:
            return Enclosure((spec[1], spec[0]))

    def _get_specs(self, other):
        try:
            other = Enclosure(other)
        except:
            raise TypeError(
                "right side of operation has to be of type 'Enclosure',\n"
                "a float or a pair of floats"
            )
        else:
            return self.spec, other.spec

    def __eq__(self, other):
        spec1, spec2 = self._get_specs(other)
        if type(spec1) != type(spec2):
            return False
        elif isinstance(spec1, float):
            return spec1 == spec2
        else: # Both pairs
            return set(spec1) == set(spec2)

    def __gt__(self, other):
        spec1, spec2 = self._get_specs(other)

        if isinstance(spec1, float):
            if isinstance(spec2, float):
                return spec1 > spec2
            else:
                return spec1 > max(spec2)
        else:
            if isinstance(spec2, float):
                raise NotImplementedError()
            else:
                return (
                    ((spec1[0] > spec2[0]) and (spec1[1] > spec2[1]))
                    or ((spec1[0] > spec2[1]) and (spec1[1] > spec2[0]))
                )

    def __ge__(self, other):
        spec1, spec2 = self._get_specs(other)

        if isinstance(spec1, float):
            if isinstance(spec2, float):
                return spec1 >= spec2
            else:
                return spec1 >= max(spec2)
        else:
            if isinstance(spec2, float):
                raise NotImplementedError()
            else:
                return (
                    ((spec1[0] >= spec2[0]) and (spec1[1] >= spec2[1]))
                    or ((spec1[0] >= spec2[1]) and (spec1[1] >= spec2[0]))
                )

    def __lt__(self, other):
        spec1, spec2 = self._get_specs(other)

        if isinstance(spec1, float):
            if isinstance(spec2, float):
                return spec1 < spec2
            else:
                raise NotImplementedError()
        else:
            if isinstance(spec2, float):
                raise NotImplementedError()
            else:
                return (
                    ((spec1[0] < spec2[0]) and (spec1[1] < spec2[1]))
                    or ((spec1[0] < spec2[1]) and (spec1[1] < spec2[0]))
                )

    def __le__(self, other):
        spec1, spec2 = self._get_specs(other)

        if isinstance(spec1, float):
            if isinstance(spec2, float):
                return spec1 <= spec2
            else:
                raise NotImplementedError()
        else:
            if isinstance(spec2, float):
                raise NotImplementedError()
            else:
                return (
                    ((spec1[0] <= spec2[0]) and (spec1[1] <= spec2[1]))
                    or ((spec1[0] <= spec2[1]) and (spec1[1] <= spec2[0]))
                )

    def __repr__(self):
        return f"Enclosure({self.spec})"

class EnclosureProperty(Property):
    value_conv = Enclosure
    value_type = Enclosure
    value_type_str = "'Enclosure'"
