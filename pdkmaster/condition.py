import abc

from . import _util

__all__ = ["Condition", "Conditions"]

class Condition(abc.ABC):
    @abc.abstractmethod
    def __init__(self, elements):
        self._elements = elements

    def __eq__(self, other):
        return (self.__class__ == other.__class__) and (hash(self) == hash(other))

    def __ne__(self, other):
        return not self.__ne__(other)

    def __bool__(self):
        raise ValueError("Condition can't be converted to 'bool'")

    def __hash__(self):
        return hash(self._elements)

    @abc.abstractmethod
    def __str__(self):
        raise RuntimeError("Condition subclass needs to implement __str__() method")

class Conditions:
    def __init__(self):
        self._conds = set()
        self._frozen = False

    def freeze(self):
        self._frozen = True

    def __iadd__(self, other):
        if self._frozen:
            raise ValueError("Can't add condition when frozen")

        conds = set(other) if _util.is_iterable(other) else {other}
        for cond in conds:
            if not isinstance(cond, Condition):
                raise TypeError("other has to be of type 'Condition' or an iterable of type 'Condition'")

        self._conds.update(conds)

        return self

    def __iter__(self):
        return iter(self._conds)
