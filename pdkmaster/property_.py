from . import condition as cond

__all__ = ["Operators", "Property"]

class _BinaryPropertyCondition(cond.Condition):
    def __init__(self, *, left, right):
        if not isinstance(left, Property):
            raise TypeError("left value has to be of type 'Property'")
        try:
            right = left.type(right)
        except:
            raise TypeError("right value {!r} can't be converted to type '{!r}'".format(right, left.type))

        super().__init__((left, right))
        self.left = left
        self.right = right

class Operators:
    class Greater(_BinaryPropertyCondition):
        pass
    class GreaterEqual(_BinaryPropertyCondition):
        pass
    class Smaller(_BinaryPropertyCondition):
        pass
    class SmallerEqual(_BinaryPropertyCondition):
        pass
    class Equal(_BinaryPropertyCondition):
        pass
    # Convenience assigns
    GT = Greater
    GE = GreaterEqual
    ST = Smaller
    SE = SmallerEqual
    EQ = Equal
# Convenience assigns
Ops = Operators

class Property:
    def __init__(self, name, type_=float):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        if not isinstance(type_, type):
            raise TypeError("type_ has to be of type 'type'")

        self.name = name
        self.type = type_
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

    def __hash__(self):
        return hash((self.name, self.type))
