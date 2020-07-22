import abc

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

class _ConditionsAdd:
    def __init__(self, conds, new):
        self.conds = conds
        self.new = new

class Conditions:
    def __init__(self):
        self._conds = set()

    def __iadd__(self, other):
        e = TypeError("other has to be of type 'Condition' or an iterable of type 'Condition'")
        try:
            iter(other)
        except TypeError:
            if not isinstance(other, Condition):
                raise e
            conds = {other}
        else:
            conds = set(other)
            for cond in conds:
                if not isinstance(cond, Condition):
                    raise e

        self._conds.update(conds)

        return self

    def __iter__(self):
        return iter(self._conds)
