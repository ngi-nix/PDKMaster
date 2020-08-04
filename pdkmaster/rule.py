import abc

from . import _util

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

class Rules:
    def __init__(self):
        self._rules = set()
        self._frozen = False

    def freeze(self):
        self._frozen = True

    def __iadd__(self, other):
        if self._frozen:
            raise ValueError("Can't add rule when frozen")

        rules = set(other) if _util.is_iterable(other) else {other}
        for rule in rules:
            if not isinstance(rule, _Rule):
                raise TypeError("other has to be of type '_Rule' or an iterable of type '_Rule'")

        self._rules.update(rules)

        return self

    def __iter__(self):
        return iter(self._rules)
