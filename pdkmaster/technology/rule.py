import abc

from .. import _util

__all__ = ["Rules"]

class _Rule(abc.ABC):
    @abc.abstractmethod
    def __init__(self):
        pass

    def __eq__(self, other):
        return (self.__class__ == other.__class__) and (hash(self) == hash(other))

    def __ne__(self, other):
        return not self.__ne__(other)

    def __bool__(self):
        raise ValueError("Condition can't be converted to 'bool'")

    @abc.abstractmethod
    def __hash__(self):
        raise TypeError("subclasses of _Rule need to implement __hash__()")

class Rules(_util.TypedTuple):
    tt_element_type = _Rule
    tt_index_attribute = None
