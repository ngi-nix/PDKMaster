import abc
from . import _util, condition as cnd

__all__ = ["Operators", "Property"]

class _BinaryPropertyCondition(cnd.Condition, abc.ABC):
    symbol = abc.abstractproperty()

    def __init__(self, *, left, right):
        if not isinstance(self.symbol, str):
            raise AttributeError("symbol _BinaryPropertyCondition abstract property has to be a string")
        if not isinstance(left, Property):
            raise TypeError("left value has to be of type 'Property'")

        super().__init__((left, right))
        self.left = left
        self.right = left._conv_value(right)

    def __str__(self):
        return "{} {} {}".format(str(self.left), self.symbol, str(self.right))

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

    def __init__(self, name):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")

        self.name = name
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

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    @classmethod
    def _conv_value(cls, value):
        if cls.value_conv is not None:
            try:
                value = cls.value_conv(value)
            except:
                raise TypeError("could not convert property value {!r} to type '{}'".format(
                    value, cls.value_type_str,
                ))
        if not isinstance(value, cls.value_type):
            raise TypeError("property value {!r} is not of type '{}'".format(
                value, cls.value_type_str,
            ))
        return value
